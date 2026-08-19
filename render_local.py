"""카드 렌더 CLI: python render_local.py work/draft.json out/2026-08-19/1030_키워드"""
import json
import sys
from pathlib import Path

from local_env import load_env

load_env()  # I2C_HANDLE 반영 — cards import보다 먼저

import cards  # noqa: E402


def main():
    if len(sys.argv) < 3:
        print("사용법: python render_local.py <draft.json> <출력폴더>"); sys.exit(1)
    draft = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    out_dir = sys.argv[2]
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    paths = cards.render_cards(draft, out_dir=out_dir)
    for p in paths:
        print(p)


if __name__ == "__main__":
    main()
