"""텔레그램 알림 (무료): 완료 요약 + 카드 이미지 미리보기 전송."""
import os

import requests


def notify(text: str, image_paths: list = None):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("[telegram] token/chat_id 없음 — 알림 생략")
        return
    base = f"https://api.telegram.org/bot{token}"
    requests.post(f"{base}/sendMessage", json={"chat_id": chat_id, "text": text,
                                              "disable_web_page_preview": True})
    for p in (image_paths or []):
        with open(p, "rb") as f:
            requests.post(f"{base}/sendPhoto", data={"chat_id": chat_id}, files={"photo": f})
