# ER 세션 토큰 캡처 실행기 (local 모드 — 전에 쓰던 방식)
# - mitmdump --mode local:EternalReturn.exe : EternalReturn.exe 프로세스 트래픽만
#   투명하게 가로챈다(WinDivert 기반). 시스템 프록시를 안 건드림 → 다른 트래픽 안전.
# - capture_addon.py 가 bser 트래픽에서 토큰을 뽑아 session_tokens.log 에 기록.
# - -w flows.mitm 으로 원본 flow 도 통째로 저장(나중에 mitmweb 으로 다시 열람 가능).
#
# 최초 1회: 프록시 켠 상태에서 브라우저로 http://mitm.it 접속 → Windows용 CA 인증서
#           설치("현재 사용자 → 신뢰할 수 있는 루트 인증 기관")해야 HTTPS 해독됨.
#           (local 모드도 HTTPS 해독엔 CA 신뢰가 필요함.)

$ErrorActionPreference = "Stop"
$here    = Split-Path -Parent $MyInvocation.MyCommand.Path
$process = "EternalReturn.exe"
$flows   = Join-Path $here "flows.mitm"

# mitmproxy 설치 확인
if (-not (Get-Command mitmdump -ErrorAction SilentlyContinue)) {
    Write-Host "[setup] mitmproxy 가 없어서 설치한다 (pip install mitmproxy)" -ForegroundColor Yellow
    pip install mitmproxy
    if ($LASTEXITCODE -ne 0) { throw "mitmproxy 설치 실패 — python/pip 확인 필요" }
}

# local 모드는 WinDivert 를 쓰므로 관리자 권한 필요
$isAdmin = ([Security.Principal.WindowsPrincipal] `
    [Security.Principal.WindowsIdentity]::GetCurrent()
).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[!] local 모드는 관리자 권한이 필요하다 — 관리자 PowerShell 에서 다시 실행해라." -ForegroundColor Red
    Write-Host "    (우클릭 → '관리자 권한으로 실행')" -ForegroundColor Red
    exit 1
}

Write-Host "[mode] --mode local:$process  (이 프로세스 트래픽만 가로챈다, 시스템 프록시 안 건드림)" -ForegroundColor Cyan
Write-Host "[hint] 최초 1회면 http://mitm.it 에서 CA 인증서 설치부터 해라." -ForegroundColor DarkYellow
Write-Host "[go  ] 게임을 실행/로그인하면 session_tokens.log 에 토큰이 쌓인다. 끄려면 Ctrl+C.`n" -ForegroundColor Green

# 게임을 먼저 실행해도 되고, mitmdump 를 먼저 켜도 됨. local 모드가 프로세스를 따라간다.
mitmdump --mode "local:$process" -s "$here\capture_addon.py" -w "$flows"
