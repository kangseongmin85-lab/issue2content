"""issue2content — 이슈 서치 → 글쓰기(API 1회) + 린트 2회(API) → 카드 2장(토큰 0) → 노션 저장 → 텔레그램 알림.

필요 환경변수:
  NOTION_TOKEN, NOTION_PARENT_PAGE_ID   (필수)
  ANTHROPIC_API_KEY                     (권장 — 없으면 템플릿 모드)
  TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID  (선택)
  I2C_HANDLE(@핸들), I2C_MODEL(기본 claude-haiku-4-5), I2C_CATEGORY(주식|전반|all)
"""
import os
import sys
import traceback

import collector
import writer
import cards
import notion_save
import telegram_notify


def main():
    want = os.environ.get("I2C_CATEGORY", "all")
    print("[1/5] 이슈 수집 중...")
    articles = collector.collect()
    if not articles:
        print("수집된 기사가 없습니다. 네트워크/RSS 확인 필요."); sys.exit(1)
    issues = collector.rank_issues(articles, top_n=5)
    if want != "all":
        filtered = [i for i in issues if i.category == want]
        issues = filtered or issues

    # 24시간 모드: 이미 다룬 이슈 건너뛰기 + 일일 생성 상한
    from datetime import date as _d
    today = _d.today().isoformat()
    try:
        titles = notion_save.recent_child_titles()
    except Exception:
        titles = []
    today_count = sum(1 for t in titles if t.startswith(f"[{today}]"))
    max_per_day = int(os.environ.get("I2C_MAX_PER_DAY", "8"))
    if today_count >= max_per_day:
        print(f"오늘 생성 {today_count}건 — 일일 상한({max_per_day}) 도달, 종료."); return
    recent = " ".join(titles[:80])
    fresh = [i for i in issues if i.keyword not in recent]
    if not fresh:
        print("새로운 이슈 없음(전부 기존 페이지와 중복) — API 호출 없이 종료."); return
    issue = fresh[0]
    print(f"    선정 이슈: {issue.keyword} ({issue.category}, 기사 {issue.score}건, 오늘 {today_count}건째)")

    print("[2/5] 글 작성 + 2회 린트...")
    draft = writer.write_content(issue)
    draft["keyword"] = issue.keyword
    print(f"    모드: {draft.get('mode')}")

    print("[3/5] 카드 이미지 렌더링...")
    image_paths = cards.render_cards(draft)
    print(f"    생성: {image_paths}")

    # 결과물 로컬 저장 (Actions 아티팩트용 백업)
    import json, pathlib
    pathlib.Path("out").mkdir(exist_ok=True)
    pathlib.Path("out/draft.json").write_text(json.dumps(draft, ensure_ascii=False, indent=1), encoding="utf-8")

    print("[4/5] 노션 저장...")
    if os.environ.get("NOTION_TOKEN") and os.environ.get("NOTION_PARENT_PAGE_ID"):
        url = notion_save.save(draft, image_paths)
        print(f"    페이지: {url}")
    else:
        url = "(노션 미설정 — Secrets에 NOTION_TOKEN, NOTION_PARENT_PAGE_ID 등록 필요. 결과물은 Actions 아티팩트에 저장됨)"
        print(f"    {url}")

    print("[5/5] 텔레그램 알림...")
    telegram_notify.notify(
        f"📝 오늘의 콘텐츠 초안 도착\n이슈: {issue.keyword}\n노션: {url}\n"
        f"할 일: [내 코멘트] 채우기 → 블로그 발행 → X 발행", image_paths)
    print("완료.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        telegram_notify.notify("⚠️ issue2content 실행 실패 — GitHub Actions 로그를 확인하세요.")
        sys.exit(1)
