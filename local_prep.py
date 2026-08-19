"""회차 준비 (토큰 0): RSS 수집 → 키워드 랭킹 → 중복 제거 → work/candidates.json.

중복 검증(구 main.py의 부분문자열 방식 결함 수정):
  - seen.json에 (키워드, 날짜) 기록, 최근 7일 안에 다룬 키워드만 차단
  - 정확 일치 또는 상호 포함(코스피/코스피지수)일 때만 중복으로 판정
"""
import json
import time
from datetime import date, timedelta
from pathlib import Path

import collector

SEEN_PATH = Path("seen.json")
OUT_PATH = Path("work/candidates.json")
DEDUP_DAYS = 7


def _load_seen() -> list:
    if not SEEN_PATH.exists():
        return []
    try:
        seen = json.loads(SEEN_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    cutoff = (date.today() - timedelta(days=DEDUP_DAYS)).isoformat()
    return [s for s in seen if s.get("date", "") >= cutoff]


def _recent_seen() -> list:
    return [s["keyword"] for s in _load_seen()]


def _recent_links() -> set:
    """이미 다룬 회차가 근거로 쓴 기사 링크 — 같은 사건을 다른 키워드로 재탕하는 것을 막는다."""
    links = set()
    for s in _load_seen():
        links.update(s.get("links") or [])
    return links


def _is_dup(kw: str, recent: list) -> bool:
    return any(kw == r or kw in r or r in kw for r in recent)


def main():
    print("[prep] RSS 수집 중...")
    articles = collector.collect()
    print(f"[prep] 기사 {len(articles)}건 수집")
    issues = collector.rank_issues(articles, top_n=8)

    recent = _recent_seen()
    used_links = _recent_links()
    fresh, skipped, same_story = [], [], []
    for i in issues:
        if _is_dup(i.keyword, recent):
            skipped.append(i)
            continue
        # 같은 사건 재탕 차단: 근거 기사의 절반 이상이 이미 쓴 기사면 제외
        links = [a.link for a in i.articles if a.link]
        overlap = sum(1 for l in links if l in used_links)
        if links and overlap / len(links) >= 0.5:
            same_story.append(i)
            continue
        fresh.append(i)
    if skipped:
        print(f"[prep] 키워드 중복 스킵({DEDUP_DAYS}일): " + ", ".join(i.keyword for i in skipped))
    if same_story:
        print("[prep] 같은 사건 재탕 스킵: " + ", ".join(i.keyword for i in same_story))

    now = time.time()

    def _age_h(ts):
        return round((now - ts) / 3600, 1) if ts else None

    payload = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M"),
        "candidates": [
            {
                "keyword": i.keyword, "score": i.score, "category": i.category,
                "article_count": len(i.articles),
                # 가장 최근 기사가 몇 시간 전인지 — 신선도 판정의 1차 지표
                "newest_age_h": min((_age_h(a.ts) for a in i.articles if a.ts), default=None),
                "articles": [
                    {"title": a.title, "link": a.link, "source": a.source,
                     "published": a.published, "age_h": _age_h(a.ts)}
                    for a in i.articles
                ],
            }
            for i in fresh
        ],
    }
    OUT_PATH.parent.mkdir(exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[prep] 후보 {len(fresh)}건 → {OUT_PATH}")
    for c in payload["candidates"]:
        age = c["newest_age_h"]
        flag = "" if age is None or age <= 6 else "   ⚠ 지난 이슈"
        age_txt = f"{age}h 전" if age is not None else "시각불명"
        print(f"  - {c['keyword']} ({c['category']}, 기사 {c['article_count']}건, "
              f"최신 {age_txt}, 화제도 {c['score']}){flag}")
    if not fresh:
        print("[prep] 새 이슈 없음 — 이번 회차는 건너뛰어도 됨")


if __name__ == "__main__":
    main()
