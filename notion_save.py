"""Notion API 저장 (무료). 이슈당 페이지 1개: 요약·X 복붙 블록·블로그 블록·카드 이미지 첨부."""
import json
import os
from datetime import date
from pathlib import Path

import requests

API = "https://api.notion.com/v1"
VER = {"Notion-Version": "2022-06-28"}


def _headers():
    return {"Authorization": f"Bearer {os.environ['NOTION_TOKEN']}",
            "Content-Type": "application/json", **VER}


def _upload_file(path: str) -> str:
    """Notion File Upload API로 PNG 업로드 → file_upload id 반환."""
    r = requests.post(f"{API}/file_uploads", headers=_headers(),
                      json={"filename": Path(path).name, "content_type": "image/png"})
    r.raise_for_status()
    up = r.json()
    with open(path, "rb") as f:
        r2 = requests.post(f"{API}/file_uploads/{up['id']}/send",
                           headers={"Authorization": _headers()["Authorization"], **VER},
                           files={"file": (Path(path).name, f, "image/png")})
    r2.raise_for_status()
    return up["id"]


def _rt(text: str):
    return [{"type": "text", "text": {"content": text[:2000]}}]


def _blocks(draft: dict, image_ids: list) -> list:
    b = []
    b.append({"object": "block", "type": "heading_1",
              "heading_1": {"rich_text": _rt("상태: 🟡 초안 (검토 대기)")}})
    b.append({"object": "block", "type": "paragraph",
              "paragraph": {"rich_text": _rt(f"작성 모드: {draft.get('mode')} · [내 코멘트] 슬롯을 채운 뒤 발행하세요.")}})
    if image_ids:
        b.append({"object": "block", "type": "heading_2",
                  "heading_2": {"rich_text": _rt("🖼 X 첨부 이미지 (다운로드 → 포스트에 첨부)")}})
        for fid in image_ids:
            b.append({"object": "block", "type": "image",
                      "image": {"type": "file_upload", "file_upload": {"id": fid}}})
    b.append({"object": "block", "type": "heading_2",
              "heading_2": {"rich_text": _rt("📋 X 발행용 (복붙 블록)")}})
    if draft.get("x_single"):
        b.append({"object": "block", "type": "code",
                  "code": {"language": "plain text", "rich_text": _rt(draft["x_single"])}})
    for i, post in enumerate(draft.get("x_thread") or [], 1):
        b.append({"object": "block", "type": "code",
                  "code": {"language": "plain text", "rich_text": _rt(post)}})
    b.append({"object": "block", "type": "heading_2",
              "heading_2": {"rich_text": _rt("📝 블로그 발행용")}})
    b.append({"object": "block", "type": "paragraph",
              "paragraph": {"rich_text": _rt("제목: " + (draft.get("blog_title") or ""))}})
    # 블로그 본문: 2000자 단위로 분할해 code 블록으로 (복붙용)
    body = draft.get("blog_body") or ""
    for i in range(0, len(body), 1900):
        b.append({"object": "block", "type": "code",
                  "code": {"language": "markdown", "rich_text": _rt(body[i:i + 1900])}})
    meta = f"메타 설명: {draft.get('meta_description','')} / 키워드: {draft.get('target_keyword','')}"
    b.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": _rt(meta)}})
    for item in ["[내 코멘트] 슬롯 채우기", "핵심 수치 1개 이상 직접 재확인",
                 "블로그 발행 → URL을 X [블로그 링크]에 반영 → X 발행", "발행 후 상태 🟢로 변경"]:
        b.append({"object": "block", "type": "to_do",
                  "to_do": {"rich_text": _rt(item), "checked": False}})
    return b


def recent_child_titles(hours_titles: int = 100) -> list:
    """부모 페이지 하위 페이지 제목 목록 (중복 이슈 방지·일일 상한 계산용)."""
    parent_id = os.environ["NOTION_PARENT_PAGE_ID"]
    titles = []
    cursor, url = None, f"{API}/blocks/{parent_id}/children?page_size=100"
    for _ in range(3):  # 최대 300개
        u = url + (f"&start_cursor={cursor}" if cursor else "")
        r = requests.get(u, headers=_headers())
        if r.status_code != 200:
            break
        data = r.json()
        for blk in data.get("results", []):
            if blk.get("type") == "child_page":
                titles.append(blk["child_page"].get("title", ""))
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    return titles


def save(draft: dict, image_paths: list) -> str:
    parent_id = os.environ["NOTION_PARENT_PAGE_ID"]
    image_ids = []
    for p in image_paths:
        try:
            image_ids.append(_upload_file(p))
        except Exception as e:
            print(f"[notion] image upload failed: {e}")
    kw = draft.get("keyword", "")
    title = f"[{date.today().isoformat()}] {kw} — {draft.get('blog_title','콘텐츠 초안')[:50]}"
    payload = {
        "parent": {"page_id": parent_id},
        "properties": {"title": {"title": _rt(title)}},
        "children": _blocks(draft, image_ids),
    }
    r = requests.post(f"{API}/pages", headers=_headers(), json=payload)
    r.raise_for_status()
    return r.json().get("url", "")
