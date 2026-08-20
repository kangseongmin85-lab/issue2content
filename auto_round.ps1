# auto_round.ps1 — /x-blog-round 1회차를 새 Claude 세션에서 무인 실행
#
# 왜 새 세션인가: /loop나 cron으로 같은 세션에 회차를 쌓으면 API 호출마다 그때까지의
# 대화 전체를 다시 읽는다(캐시 읽기). 실측상 이 비용이 전체의 97%였고, 회차가 쌓일수록
# 계속 커진다. 매 회차 새 프로세스를 띄우면 컨텍스트가 회차 분량으로 리셋돼 4~5배 싸다.
#
# 수동 실행: powershell -ExecutionPolicy Bypass -File auto_round.ps1

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repo

# 자동 업데이트 차단: 2026-08-20에 본체가 2.1.237로 오르면서 플랫폼 바이너리(2.1.236이 최신)를
# 못 찾아 CLI가 통째로 깨진 사례가 있다. 무인 실행 중 같은 일이 나면 회차가 조용히 죽는다.
$env:DISABLE_AUTOUPDATER = '1'

$stamp   = Get-Date -Format 'yyyy-MM-dd_HHmm'
$logDir  = Join-Path $repo 'out\logs'
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
$log = Join-Path $logDir "$stamp.log"

# 회차에 필요한 도구만 허용한다. 목록에 없는 도구는 무인 모드에서 자동 거부된다.
$allowed = @(
  'Bash', 'Read', 'Write', 'Edit', 'Glob', 'Grep',
  'WebFetch', 'WebSearch', 'Task',
  'mcp__claude_ai_Notion__notion-create-pages',
  'mcp__claude_ai_Notion__notion-fetch'
)

"=== $stamp 회차 시작 ===" | Tee-Object -FilePath $log

try {
    # stdin을 즉시 닫는다 ($null 파이프). 안 그러면 CLI가 파이프 입력을 3초 기다린다.
    $null | & claude -p '/x-blog-round' `
        --allowedTools $allowed `
        --permission-mode acceptEdits 2>&1 | Tee-Object -FilePath $log -Append
    $code = $LASTEXITCODE
} catch {
    "[error] $($_.Exception.Message)" | Tee-Object -FilePath $log -Append
    $code = 1
}

"=== 종료 코드 $code ===" | Tee-Object -FilePath $log -Append

# 실패했으면 텔레그램으로 알린다 (회차 자체가 죽으면 노션도 텔레그램도 안 오므로,
# 조용한 실패를 막는 유일한 통로다)
if ($code -ne 0) {
    $tail = (Get-Content $log -Tail 15) -join "`n"
    $py = @"
from local_env import load_env; load_env()
import telegram_notify
telegram_notify.notify('''[X 자동회차 실패] $stamp
종료 코드 $code
--- 로그 끝부분 ---
$tail''')
"@
    $py | & python - 2>&1 | Out-Null
}

exit $code
