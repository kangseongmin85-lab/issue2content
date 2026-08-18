# issue2content — 토큰 최소 자동 콘텐츠 파이프라인 (24시간 모드)

24시간, 30분 간격으로 자동 실행: 실시간 이슈 수집(무료 RSS) → **중복 검증**(노션 기존 페이지와 대조, 새 이슈 없으면 API 호출 없이 종료) → 블로그+X 글 작성(Claude API 1회) → AI패턴/가독성 린트 2회(API 2회) → 카드 이미지 2장 렌더링(토큰 0) → 노션 저장 → 텔레그램 알림.

**⚠️ 30분 간격 운영 시 저장소는 Public 권장**: GitHub Actions 무료 시간은 Private 저장소 월 2,000분인데, 30분 간격(하루 48회)이면 이를 초과합니다. Public 저장소는 Actions 무제한 무료예요. 코드에는 비밀 정보가 전혀 없고 키는 모두 Secrets(비공개)에 있으므로 Public이어도 안전합니다. Private을 원하면 cron을 `"0 * * * *"`(1시간) 이상으로.

**비용 통제 장치 (내장)**
- 중복 검증: 최근 노션 페이지 제목에 이미 있는 키워드는 건너뜀 → 실제 API 호출은 "새 이슈가 뜬 회차"에만 발생
- 일일 상한: 하루 생성 `I2C_MAX_PER_DAY`(기본 8건) 도달 시 그날은 더 안 만듦
- 즉, 30분 간격이어도 API 비용은 "하루 최대 8건 × 3호출" = Haiku 기준 월 수천 원 이내

- Claude 구독 사용량(토큰): **0** — Cowork/claude.ai를 전혀 쓰지 않음
- 비용: Claude API 3회 호출(기본 Haiku)로 하루 1회 기준 월 수백 원~천 원대. 나머지 전부 무료
- API 키가 없으면 "템플릿 모드"로 동작 (완전 무료, 글 품질은 헤드라인 정리 수준)

## 1. 준비물 (전부 무료 발급)

**① Notion 토큰 + 부모 페이지 ID**
1. https://www.notion.so/my-integrations → New integration 생성 → "Internal Integration Secret" 복사 = `NOTION_TOKEN`
2. 노션에서 "콘텐츠 파이프라인" 페이지 열기 → 우상단 ⋯ → 연결(Connections) → 방금 만든 통합 추가
3. 페이지 URL 끝의 32자리가 `NOTION_PARENT_PAGE_ID` (예: notion.so/xxx-**3c0ffbf46173819d80d0f4081609ff5b**)

**② 텔레그램 봇 (선택이지만 추천)**
1. 텔레그램에서 @BotFather 검색 → `/newbot` → 봇 이름 지정 → 토큰 복사 = `TELEGRAM_BOT_TOKEN`
2. 만든 봇에게 아무 메시지 1개 전송
3. 브라우저에서 `https://api.telegram.org/bot<토큰>/getUpdates` 열기 → `"chat":{"id":숫자}` = `TELEGRAM_CHAT_ID`

**③ Claude API 키 (권장)**
- https://console.anthropic.com → API Keys → 발급 = `ANTHROPIC_API_KEY` (사용량만큼만 과금)

## 2. GitHub Actions 배포 (서버비 0원)

1. GitHub에서 새 저장소 생성 (**Private** 권장) → 이 폴더 전체 업로드
   - 웹에서도 가능: 저장소 → Add file → Upload files → 폴더 내용물 드래그
   - `.github/workflows/daily.yml`이 포함되어야 함 (숨김 폴더 주의)
2. 저장소 → Settings → Secrets and variables → Actions → **Secrets**에 등록:
   - `NOTION_TOKEN`, `NOTION_PARENT_PAGE_ID`, `ANTHROPIC_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
3. 같은 화면 **Variables** 탭에 `I2C_HANDLE` = 본인 X 핸들 (예: @myhandle)
4. Actions 탭 → "daily-content" → **Run workflow**로 첫 수동 실행 테스트
5. 이후 매일 07:30 KST 자동 실행 (시간 변경: daily.yml의 cron, UTC 기준 = KST−9시간)

## 3. 로컬 실행 (선택)

```bash
pip install -r requirements.txt
playwright install chromium
export NOTION_TOKEN=... NOTION_PARENT_PAGE_ID=... ANTHROPIC_API_KEY=...
python main.py
```

## 4. 설정값

| 환경변수 | 기본값 | 설명 |
|---|---|---|
| I2C_HANDLE | @내계정 | 카드 우하단 핸들 |
| I2C_MODEL | claude-haiku-4-5 | 글쓰기·린트 모델 (품질 올리려면 sonnet 계열로) |
| I2C_CATEGORY | all | `주식` / `전반` / `all` |
| I2C_BADGE | MARKET BRIEF | 헤드라인 카드 배지 문구 |

이슈 수집 키워드는 `collector.py`의 FEEDS에서 자유롭게 추가/수정.

## 5. 아침 루틴

텔레그램으로 "초안 도착" 알림 + 카드 미리보기가 옴 → 노션 페이지 열기 → [내 코멘트] 슬롯 채우기 → 수치 1개 재확인 → 블로그 발행 → URL을 X 초안의 [블로그 링크]에 넣고 카드 이미지 첨부해 X 발행.

## Cowork 파이프라인과의 차이 (솔직 고지)

- 근거 수집이 "기사 제목+링크" 수준 (Cowork 버전은 본문까지 읽고 교차 검증·수치 검산)
- 저작권 체크는 프롬프트 규칙으로만 적용 (별도 판정 리포트 없음)
- 린트가 3회 독립 에이전트 → 2회 API 호출로 축소
- 이미지·노션 저장·복붙 블록 구조는 동일

깊게 파야 하는 이슈(공시 검증, 수치 교차 확인이 필요한 날)는 Cowork에서 "오늘 이슈로 콘텐츠 만들어줘"로 기존 파이프라인을 쓰는 걸 권장.
