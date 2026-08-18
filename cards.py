"""카드 이미지 렌더링 (토큰 0). Playwright + 고정 HTML 템플릿."""
import html
import os
from datetime import date
from pathlib import Path

TPL_HEADLINE = r"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8">
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  html,body { width:1200px; height:675px; }
  body { font-family:'Noto Sans CJK KR','Noto Sans KR',sans-serif; background:#0B1220; color:#E8ECF2;
    display:flex; flex-direction:column; padding:52px 64px 40px; position:relative; overflow:hidden; }
  .glow { position:absolute; right:-180px; top:-180px; width:520px; height:520px; border-radius:50%;
    background:radial-gradient(circle, rgba(76,141,245,0.22) 0%, rgba(76,141,245,0) 70%); }
  .topline { display:flex; align-items:center; gap:14px; }
  .badge { font-size:22px; font-weight:700; letter-spacing:2px; color:#0B1220; background:#F5A524; padding:8px 18px; border-radius:8px; }
  .date { font-size:22px; color:#9AA4B2; letter-spacing:1px; }
  .main { flex:1; display:flex; flex-direction:column; justify-content:center; position:relative; }
  .kicker { font-size:30px; font-weight:500; color:#7FB0FF; margin-bottom:14px; }
  h1 { font-size:88px; font-weight:900; line-height:1.1; letter-spacing:-2px; }
  h1 .accent { color:#F5A524; }
  .sub { margin-top:20px; font-size:32px; font-weight:500; color:#C4CDD9; line-height:1.4; }
  .foot { display:flex; justify-content:space-between; align-items:flex-end; border-top:2px solid #232C3D; padding-top:20px; }
  .hook { font-size:26px; font-weight:700; color:#E8ECF2; max-width:900px; }
  .handle { font-size:22px; color:#9AA4B2; }
</style></head>
<body>
  <div class="glow"></div>
  <div class="topline"><span class="badge">{{BADGE}}</span><span class="date">{{DATE}}</span></div>
  <div class="main">
    <div class="kicker">{{KICKER}}</div>
    <h1>{{TITLE}}</h1>
    <div class="sub">{{SUB}}</div>
  </div>
  <div class="foot"><div class="hook">{{HOOK}}</div><div class="handle">{{HANDLE}}</div></div>
</body></html>
"""

TPL_STATS = r"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8">
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  html,body { width:1200px; height:675px; }
  body { font-family:'Noto Sans CJK KR','Noto Sans KR',sans-serif; background:#0B1220; color:#E8ECF2;
    display:flex; flex-direction:column; padding:52px 64px 40px; }
  .head { display:flex; justify-content:space-between; align-items:center; margin-bottom:38px; }
  .title { font-size:42px; font-weight:900; letter-spacing:-1px; max-width:960px; }
  .date { font-size:22px; color:#9AA4B2; }
  .grid { display:grid; grid-template-columns:1fr 1fr; gap:22px; flex:1; }
  .tile { background:#121B2E; border:1px solid #232C3D; border-radius:16px; padding:28px 34px;
    display:flex; flex-direction:column; justify-content:center; }
  .label { font-size:23px; font-weight:500; color:#9AA4B2; margin-bottom:10px; }
  .value { font-size:52px; font-weight:900; letter-spacing:-1px; line-height:1.05; }
  .value.amber { color:#F5A524; }
  .note { font-size:20px; color:#7A8494; margin-top:10px; }
  .foot { display:flex; justify-content:space-between; margin-top:28px; border-top:2px solid #232C3D; padding-top:18px; }
  .src { font-size:19px; color:#7A8494; }
  .handle { font-size:21px; color:#9AA4B2; }
</style></head>
<body>
  <div class="head"><div class="title">{{TITLE}}</div><div class="date">{{DATE}}</div></div>
  <div class="grid">{{TILES}}</div>
  <div class="foot"><div class="src">{{SOURCE_LINE}}</div><div class="handle">{{HANDLE}}</div></div>
</body></html>
"""
HANDLE = os.environ.get("I2C_HANDLE", "@내계정")
BADGE = os.environ.get("I2C_BADGE", "MARKET BRIEF")


def _esc(s):
    return html.escape(str(s or ""))


def _fill(tpl: str, mapping: dict) -> str:
    for k, v in mapping.items():
        tpl = tpl.replace("{{%s}}" % k, v)
    return tpl


def build_headline_html(card: dict) -> str:
    title = _esc(card.get("title"))
    accent = _esc(card.get("accent") or "")
    if accent and accent in title:
        title = title.replace(accent, f'<span class="accent">{accent}</span>', 1)
    return _fill(TPL_HEADLINE, {
        "BADGE": _esc(BADGE), "DATE": date.today().strftime("%Y. %m. %d"),
        "KICKER": _esc(card.get("kicker")), "TITLE": title,
        "SUB": _esc(card.get("sub")), "HOOK": _esc(card.get("hook")), "HANDLE": _esc(HANDLE),
    })


def build_stats_html(card: dict) -> str:
    tiles = ""
    for s in (card.get("stats") or [])[:4]:
        amber = " amber" if s.get("amber") else ""
        tiles += (f'<div class="tile"><div class="label">{_esc(s.get("label"))}</div>'
                  f'<div class="value{amber}">{_esc(s.get("value"))}</div>'
                  f'<div class="note">{_esc(s.get("note"))}</div></div>')
    return _fill(TPL_STATS, {
        "TITLE": _esc(card.get("title")), "DATE": date.today().strftime("%Y. %m. %d"),
        "TILES": tiles, "SOURCE_LINE": _esc(card.get("source_line")), "HANDLE": _esc(HANDLE),
    })


def render_cards(draft: dict, out_dir: str = "out") -> list:
    """draft의 card_headline / card_stats로 PNG 생성. 반환: 파일 경로 리스트."""
    Path(out_dir).mkdir(exist_ok=True)
    jobs = []
    if draft.get("card_headline"):
        jobs.append(("card_headline", build_headline_html(draft["card_headline"])))
    cs = draft.get("card_stats")
    if cs and cs.get("stats"):
        jobs.append(("card_stats", build_stats_html(cs)))
    if not jobs:
        return []

    from playwright.sync_api import sync_playwright
    paths = []
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--no-sandbox"])
        pg = b.new_page(viewport={"width": 1200, "height": 675})
        for name, html_str in jobs:
            f = Path(out_dir) / f"{name}.html"
            f.write_text(html_str, encoding="utf-8")
            pg.goto(f.resolve().as_uri())
            pg.wait_for_timeout(300)
            png = Path(out_dir) / f"{name}.png"
            pg.screenshot(path=str(png))
            paths.append(str(png))
        b.close()
    return paths
