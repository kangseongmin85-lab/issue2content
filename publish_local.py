"""발행 CLI: 노션 저장 + 텔레그램 알림 + seen.json 기록.
사용법: python publish_local.py work/draft.json <이미지폴더>
토큰이 없으면 해당 단계는 건너뛴다 (로컬 저장은 render 단계에서 이미 완료)."""
import json
import os
import sys
from datetime import date
from pathlib import Path

from local_env import load_env

load_env()

import notion_save  # noqa: E402
import telegram_notify  # noqa: E402

SEEN_PATH = Path("seen.json")


def _record_seen(keyword: str, links: list = None):
    seen = []
    if SEEN_PATH.exists():
        try:
            seen = json.loads(SEEN_PATH.read_text(encoding="utf-8"))
        except Exception:
            seen = []
    seen.append({"keyword": keyword, "date": date.today().isoformat(),
                 "links": links or []})
    SEEN_PATH.write_text(json.dumps(seen, ensure_ascii=False, indent=1), encoding="utf-8")


def main():
    if len(sys.argv) < 3:
        print("사용법: python publish_local.py <draft.json> <이미지폴더>"); sys.exit(1)
    draft = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    image_paths = sorted(str(p) for p in Path(sys.argv[2]).glob("*.png"))

    url = ""
    if os.environ.get("NOTION_TOKEN") and os.environ.get("NOTION_PARENT_PAGE_ID"):
        try:
            url = notion_save.save(draft, image_paths)
            print(f"[notion] {url}")
        except Exception as e:
            print(f"[notion] 저장 실패: {e}")
    else:
        print("[notion] 토큰 미설정 — 건너뜀 (.env 확인)")

    kw = draft.get("keyword", "")
    telegram_notify.notify(
        f"📝 콘텐츠 초안 완성\n이슈: {kw}\n노션: {url or '(미저장)'}\n"
        f"할 일: X 복붙 게시 (본문 → 첫 답글에 블로그 링크)", image_paths)

    # draft에 source_links가 있으면 함께 기록 (같은 사건 재탕 차단용)
    _record_seen(kw, draft.get("source_links"))
    print(f"[seen] '{kw}' 기록 완료 (근거 기사 {len(draft.get('source_links') or [])}건)")


if __name__ == "__main__":
    main()
