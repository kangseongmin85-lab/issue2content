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


def _recent_seen() -> list:
    if not SEEN_PATH.exists():
        return []
    try:
        seen = json.loads(SEEN_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    cutoff = (date.today() - timedelta(days=DEDUP_DAYS)).isoformat()
    return [s["keyword"] for s in seen if s.get("date", "") >= cutoff]


def _is_dup(kw: str, recent: list) -> bool:
    return any(kw == r or kw in r or r in kw for r in recent)


def main():
    print("[prep] RSS 수집 중...")
    articles = collector.collect()
    print(f"[prep] 기사 {len(articles)}건 수집")
    issues = collector.rank_issues(articles, top_n=8)

    recent = _recent_seen()
    fresh, skipped = [], []
    for i in issues:
        (skipped if _is_dup(i.keyword, recent) else fresh).append(i)
    if skipped:
        print(f"[prep] 최근 {DEDUP_DAYS}일 중복 스킵: " + ", ".join(i.keyword for i in skipped))

    payload = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M"),
        "candidates": [
            {
                "keyword": i.keyword, "score": i.score, "category": i.category,
                "articles": [
                    {"title": a.title, "link": a.link, "source": a.source, "published": a.published}
                    for a in i.articles
                ],
            }
            for i in fresh
        ],
    }
    OUT_PATH.parent.mkdir(exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[prep] 후보 {len(fresh)}건 → {OUT_PATH}")
    for i in fresh:
        print(f"  - {i.keyword} ({i.category}, 기사 {i.score}건)")
    if not fresh:
        print("[prep] 새 이슈 없음 — 이번 회차는 건너뛰어도 됨")


if __name__ == "__main__":
    main()
