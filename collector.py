"""이슈 수집: Google News RSS(무료, 키 불필요)로 전반 이슈 + 주식 이슈를 모은다. 토큰 0."""
import re
import time
from dataclasses import dataclass, field

import feedparser

# 검색형 RSS: 원하는 키워드로 자유롭게 추가/수정 가능
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

STOPWORDS = set("있다 없다 대한 위해 오늘 지난 이번 관련 기자 뉴스 속보 종합 단독 영상 포토 것으로 한다 했다 밝혔 전망 시장".split())


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


def collect(max_age_hours: int = 36) -> list:
    articles = []
    cutoff = time.time() - max_age_hours * 3600
    for category, urls in FEEDS.items():
        for url in urls:
            try:
                feed = feedparser.parse(url)
            except Exception:
                continue
            for e in feed.entries[:30]:
                ts = time.mktime(e.published_parsed) if getattr(e, "published_parsed", None) else time.time()
                if ts < cutoff:
                    continue
                articles.append(Article(
                    title=e.get("title", ""),
                    link=e.get("link", ""),
                    published=e.get("published", ""),
                    source=(e.get("source") or {}).get("title", "") if isinstance(e.get("source"), dict) else "",
                    category=category,
                ))
    return articles


def rank_issues(articles: list, top_n: int = 3) -> list:
    """여러 매체가 동시에 다루는 키워드일수록 화제성이 높다고 본다."""
    counts, sample = {}, {}
    for a in articles:
        for w in set(_tokens(a.title)):
            counts[w] = counts.get(w, 0) + 1
            sample.setdefault(w, []).append(a)
    issues = []
    for w, c in sorted(counts.items(), key=lambda x: -x[1])[:top_n * 4]:
        if c < 3:  # 최소 3개 매체/기사 이상에서 언급
            continue
        arts = sample[w][:8]
        cat = "주식" if any(a.category == "주식" for a in arts) else "전반"
        issues.append(Issue(keyword=w, score=c, category=cat, articles=arts))
    # 키워드가 서로 포함관계면 상위만 남김
    dedup = []
    for i in issues:
        if not any(i.keyword in d.keyword or d.keyword in i.keyword for d in dedup):
            dedup.append(i)
    return dedup[:top_n]
