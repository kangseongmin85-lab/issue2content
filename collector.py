"""이슈 수집: 무료 RSS(구글 뉴스 + 국내 매체)로 전반/주식 이슈를 모은다. 토큰 0.

GitHub Actions 등 데이터센터 IP에서 구글 뉴스가 막히는 경우가 있어
① 브라우저 User-Agent로 요청 ② 국내 매체 RSS 폴백 ③ 시간 필터 완화 재시도
3단계 방어를 둔다.
"""
import re
import time
from dataclasses import dataclass, field

import feedparser
import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

# 1순위: 구글 뉴스 검색형 RSS (키워드 자유 추가/수정 가능)
FEEDS = {
    "주식": [
        "https://news.google.com/rss/search?q=%EC%BD%94%EC%8A%A4%ED%94%BC&hl=ko&gl=KR&ceid=KR:ko",
        "https://news.google.com/rss/search?q=%EA%B8%89%EB%93%B1%EC%A3%BC%20OR%20%ED%8A%B9%EC%A7%95%EC%A3%BC&hl=ko&gl=KR&ceid=KR:ko",
        "https://news.google.com/rss/search?q=%EC%97%B0%EC%A4%80%20OR%20FOMC&hl=ko&gl=KR&ceid=KR:ko",
    ],
    "전반": [
        "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko",
        "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko",
    ],
}

# 2순위: 구글이 막혔을 때 쓰는 국내 매체 RSS
FALLBACK_FEEDS = {
    "주식": [
        "https://www.mk.co.kr/rss/50200011/",   # 매경 증권
        "https://www.mk.co.kr/rss/30100041/",   # 매경 경제
    ],
    "전반": [
        "https://www.yna.co.kr/rss/news.xml",   # 연합뉴스 주요
    ],
}

# 일반 불용어 + 매체명(키워드로 뽑히면 안 되므로 제외)
STOPWORDS = set((
    "있다 없다 대한 위해 오늘 지난 이번 관련 기자 뉴스 속보 종합 단독 영상 포토 "
    "것으로 한다 했다 밝혔 전망 시장 기사 사진 인터뷰 헤드라인 이슈 정리 "
    "뉴스핌 연합뉴스 머니투데이 이데일리 한국경제 매일경제 서울경제 파이낸셜뉴스 "
    "조선비즈 아시아경제 헤럴드경제 뉴시스 뉴스1 데일리안 인포스탁데일리 매경 한경 "
    "머니S 비즈워치 시사저널 노컷뉴스 오마이뉴스 프레시안 국민일보 세계일보 문화일보"
).split())


@dataclass
class Article:
    title: str
    link: str
    published: str
    source: str
    category: str


@dataclass
class Issue:
    keyword: str
    score: int
    category: str
    articles: list = field(default_factory=list)


def _tokens(title: str):
    words = re.findall(r"[가-힣A-Za-z0-9]{2,}", title)
    return [w for w in words if w not in STOPWORDS]


def _fetch(url: str):
    """UA를 붙여 RSS를 받아 파싱. 실패 시 feedparser 직접 호출로 재시도."""
    for attempt in range(2):
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
            if r.status_code == 200 and r.content:
                f = feedparser.parse(r.content)
                if f.entries:
                    return f.entries
        except Exception:
            pass
        time.sleep(1.5)
    try:
        return feedparser.parse(url).entries
    except Exception:
        return []


def _harvest(feed_map: dict, cutoff: float) -> list:
    articles = []
    for category, urls in feed_map.items():
        for url in urls:
            entries = _fetch(url)
            kept = 0
            for e in entries[:40]:
                ts = time.mktime(e.published_parsed) if getattr(e, "published_parsed", None) else time.time()
                if ts < cutoff:
                    continue
                src = e.get("source")
                src_title = src.get("title", "") if isinstance(src, dict) else ""
                articles.append(Article(
                    title=e.get("title", ""), link=e.get("link", ""),
                    published=e.get("published", ""), source=src_title, category=category))
                kept += 1
            print(f"    [feed] {url[:58]:58} received={len(entries):3} kept={kept}")
    return articles


def collect(max_age_hours: int = 36) -> list:
    cutoff = time.time() - max_age_hours * 3600
    articles = _harvest(FEEDS, cutoff)

    if not articles:  # 시간 필터 때문일 수도 있으니 한 번 완화해서 재시도
        print("    [collector] 0건 — 시간 필터 해제하고 재시도")
        articles = _harvest(FEEDS, 0)

    if not articles:  # 구글이 막힌 경우 국내 매체로 폴백
        print("    [collector] 구글 뉴스 실패 — 국내 매체 RSS로 폴백")
        articles = _harvest(FALLBACK_FEEDS, cutoff) or _harvest(FALLBACK_FEEDS, 0)

    return articles


def rank_issues(articles: list, top_n: int = 3) -> list:
    """여러 매체가 동시에 다루는 키워드일수록 화제성이 높다고 본다."""
    counts, sample = {}, {}
    for a in articles:
        for w in set(_tokens(a.title)):
            counts[w] = counts.get(w, 0) + 1
            sample.setdefault(w, []).append(a)

    min_hits = 3 if len(articles) >= 40 else 2  # 수집량이 적으면 기준 완화
    issues = []
    for w, c in sorted(counts.items(), key=lambda x: -x[1])[:top_n * 6]:
        if c < min_hits:
            continue
        arts = sample[w][:8]
        cat = "주식" if any(a.category == "주식" for a in arts) else "전반"
        issues.append(Issue(keyword=w, score=c, category=cat, articles=arts))

    dedup = []
    for i in issues:
        if not any(i.keyword in d.keyword or d.keyword in i.keyword for d in dedup):
            dedup.append(i)
    return dedup[:top_n]
