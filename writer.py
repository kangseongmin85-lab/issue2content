"""글쓰기 + 2회 린트. Claude API 총 3회 호출 (Haiku 기본 — 회당 수백 원 미만).
ANTHROPIC_API_KEY가 없으면 템플릿 모드로 폴백(품질 낮음, 토큰 0)."""
import json
import os
import re
from datetime import date

import prompts

MODEL = os.environ.get("I2C_MODEL", "claude-haiku-4-5")


def _extract_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError("no JSON in model output")
    return json.loads(m.group(0))


def _call(client, system: str, user: str) -> dict:
    resp = client.messages.create(
        model=MODEL, max_tokens=4000, system=system,
        messages=[{"role": "user", "content": user}],
    )
    return _extract_json(resp.content[0].text)


def write_content(issue) -> dict:
    articles_txt = "\n".join(f"- {a.title} | {a.source} | {a.link}" for a in issue.articles)
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return _template_fallback(issue)

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    user = prompts.WRITE_USER.format(
        date=date.today().isoformat(), keyword=issue.keyword,
        category=issue.category, articles=articles_txt)
    draft = _call(client, prompts.WRITE_SYSTEM, user)          # 1회: 작성
    draft = _call(client, prompts.LINT1_SYSTEM, json.dumps(draft, ensure_ascii=False))  # 2회: AI패턴 린트
    draft = _call(client, prompts.LINT2_SYSTEM, json.dumps(draft, ensure_ascii=False))  # 3회: 가독성 린트
    draft["mode"] = "api+lint2"
    return draft


def _template_fallback(issue) -> dict:
    """API 키 없을 때: 수집 데이터만으로 뼈대 초안 생성 (토큰 0, 품질 제한적)."""
    heads = [a.title for a in issue.articles[:5]]
    src_lines = "\n".join(f"- {a.title} ({a.source}) {a.link}" for a in issue.articles[:6])
    body = (
        f"[내 코멘트: 이 이슈를 고른 이유 한 줄]\n\n"
        f"오늘 '{issue.keyword}' 관련 보도가 몰렸다. 주요 헤드라인은 다음과 같다.\n\n"
        + "\n".join(f"- {h}" for h in heads)
        + "\n\n[내 코멘트: 나의 해석과 관전 포인트]\n\n"
        f"### 출처\n{src_lines}\n\n"
        "※ 공개 자료를 정리한 정보성 콘텐츠이며 투자 권유가 아닙니다."
    )
    return {
        "mode": "template",
        "blog_title": f"오늘 화제: {issue.keyword} — 헤드라인 정리",
        "blog_titles_alt": [], "meta_description": f"{issue.keyword} 관련 주요 보도 정리",
        "target_keyword": issue.keyword, "blog_body": body,
        "x_single": f"오늘 '{issue.keyword}' 보도 급증({issue.score}건+). 정리는 블로그에. [내 코멘트: 한 줄] [블로그 링크]",
        "x_thread": [],
        "card_headline": {"kicker": "오늘의 이슈", "title": issue.keyword, "accent": issue.keyword,
                          "sub": f"관련 보도 {issue.score}건+ · {date.today().strftime('%m/%d')}",
                          "hook": heads[0][:40] if heads else ""},
        "card_stats": None,
    }
