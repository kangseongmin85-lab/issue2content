# X 첨부용 카드 이미지 자동 생성 (무료)

원칙: 외부 이미지·AI 사진 생성 대신, 글의 핵심 문구·숫자로 카드형 이미지를 코드로 직접 렌더링한다. 비용 0원, 저작권 안전(자체 제작), 매회 동일한 디자인으로 계정 브랜딩 효과.

## 생성 대상 (이슈당 2장 기본)

1. **헤드라인 카드** — 단독 포스트·스레드 1/5에 첨부. 구성: 상단 배지(MARKET BRIEF)+날짜, 중앙 키커(한 줄 맥락)+대형 제목(핵심 키워드+숫자 강조)+서브(일정·부연), 하단 훅 한 줄+@핸들.
2. **핵심수치 카드** — 스레드 2/5 또는 4/5에 첨부. 구성: 제목+날짜, 2×2 스탯 타일(라벨/큰 숫자/부연), 하단 자료 출처+@핸들.

## 디자인 규격 (고정 템플릿)

- 크기 1200×675 (X 타임라인 16:9), PNG
- 배경 #0B1220, 타일 #121B2E, 테두리 #232C3D, 본문 잉크 #E8ECF2, 보조 #9AA4B2, 포인트 앰버 #F5A524(강조 숫자·배지), 포인트 블루 #7FB0FF(키커)
- 폰트: Noto Sans CJK KR (제목 Black 900, 본문 Medium/Regular)
- 강조 색은 카드당 2곳 이내. 수치는 근거 수집 단계에서 출처 확인된 것만 사용.
- @핸들 자리는 기본 "@내계정" — 사용자가 실제 핸들을 알려주면 그 값으로 교체해 기억한다.

## 렌더링 방법

1. 위 규격으로 HTML 파일 작성 (인라인 CSS, 카드당 1파일). 레이아웃은 `display:flex; flex-direction:column` + 중간 영역 `flex:1` 구조를 쓴다 (absolute 포지셔닝·justify-content:space-between 단독 사용은 헤드리스 렌더링에서 잘림 사고가 있었음 — 금지).
2. Playwright(Python)로 스크린샷:
```python
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"])
    pg = b.new_page(viewport={"width":1200,"height":675})
    pg.goto("file:///.../card.html"); pg.wait_for_timeout(300)
    pg.screenshot(path="card.png"); b.close()
```
3. 생성된 PNG를 Read 툴로 열어 눈으로 확인한다 (텍스트 잘림·겹침 검수). 잘리면 수정 후 재렌더.

## 노션 저장 방법

1. `notion-create-file-upload`(filename)로 업로드 URL 발급
2. 발급된 upload_url에 multipart POST로 PNG 업로드 (`file` 필드, 반환된 authorization 헤더 포함)
3. 응답의 `<image src="file-upload://...">` 마크다운을 `notion-update-page`(update_content)로 이슈 페이지의 "X 발행용" 섹션 상단에 삽입 — 어떤 카드를 어느 포스트에 첨부할지 안내 문구와 함께

## 사용자 발행 동작

노션에서 이미지 우클릭 저장(또는 다운로드) → X 포스트 작성 시 첨부 → 텍스트는 코드 블록 복붙. 카드 내용은 본문과 동일한 근거 기반 수치이므로 별도 검증 불필요, 단 [내 코멘트]와 무관하게 첨부 가능.
