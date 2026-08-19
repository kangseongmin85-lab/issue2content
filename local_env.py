"""로컬 실행용 .env 로더 (의존성 없음). KEY=VALUE 형식, # 주석 지원."""
import os
from pathlib import Path


def load_env(path: str = ".env"):
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())
