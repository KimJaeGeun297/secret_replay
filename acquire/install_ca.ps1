# mitmproxy CA 인증서를 "현재 사용자 → 신뢰할 수 있는 루트 인증 기관" 에 설치.
# local 모드에선 http://mitm.it 이 안 뜨므로, 디스크에 생성된 CA 파일을 직접 설치한다.
#
# 실행:  powershell -ExecutionPolicy Bypass -File .\install_ca.ps1

$ErrorActionPreference = "Stop"
$cer = Join-Path $env:USERPROFILE ".mitmproxy\mitmproxy-ca-cert.cer"

# 1) CA 파일 존재 확인 (없으면 mitmdump 한 번 돌려 생성)
if (-not (Test-Path $cer)) {
    Write-Host "[!] CA 파일이 없다: $cer" -ForegroundColor Yellow
    Write-Host "    mitmdump 를 한 번 실행하면 생성된다. 5초만 켰다 끈다..." -ForegroundColor Yellow
    if (Get-Command mitmdump -ErrorAction SilentlyContinue) {
        $p = Start-Process mitmdump -PassThru -WindowStyle Hidden
        Start-Sleep -Seconds 5
        Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
    } else {
        Write-Host "    mitmdump 도 없다 → pip install mitmproxy 후 다시 실행." -ForegroundColor Red
        exit 1
    }
}
if (-not (Test-Path $cer)) { Write-Host "[실패] CA 파일 생성 안 됨" -ForegroundColor Red; exit 1 }

# 2) 이미 설치돼 있으면 스킵
$cert  = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2 $cer
$thumb = $cert.Thumbprint
if (Get-ChildItem Cert:\CurrentUser\Root | Where-Object { $_.Thumbprint -eq $thumb }) {
    Write-Host "[OK] 이미 설치돼 있다 (지문 $thumb)" -ForegroundColor Green
    exit 0
}

# 3) 설치 — 보안 경고 팝업이 뜨면 "예"
Write-Host "[설치] $cer" -ForegroundColor Cyan
Write-Host "       Windows 보안 경고 팝업이 뜨면 반드시 '예' 를 눌러라." -ForegroundColor Yellow
try {
    Import-Certificate -FilePath $cer -CertStoreLocation Cert:\CurrentUser\Root | Out-Null
} catch {
    # 비대화형/UI 차단 환경 폴백: X509Store API 로 직접 추가
    $store = New-Object System.Security.Cryptography.X509Certificates.X509Store("Root", "CurrentUser")
    $store.Open("ReadWrite"); $store.Add($cert); $store.Close()
}

# 4) 결과 확인
if (Get-ChildItem Cert:\CurrentUser\Root | Where-Object { $_.Thumbprint -eq $thumb }) {
    Write-Host "[완료] 설치됨 — 이제 run.ps1 로 세션키를 캡처할 수 있다." -ForegroundColor Green
} else {
    Write-Host "[실패] 설치 안 됨 — 탐색기에서 CA 파일을 더블클릭해 수동 설치해라:" -ForegroundColor Red
    Write-Host "       $cer" -ForegroundColor Red
}
