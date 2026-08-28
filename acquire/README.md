# ER 세션 토큰 모니터 + 리플레이 조회

이터널 리턴 클라이언트가 bser(님블뉴런) 서버로 로그인할 때 쓰는 **세션 토큰**을
로컬에서 관찰해 로그로 남기고, 그 토큰으로 공식 `findReplayGame` API 를 불러
게임의 **리플레이(`.er`) URL/UUID** 를 뽑는다.

> 자기 계정의 인증 토큰·리플레이를 **로컬에서 관찰/조회**하는 개인 도구. 트래픽 변조·재전송 없음.
> 캡처 로그(`session_tokens.log`)·원본 트래픽(`flows.mitm`)·받은 `.er` 은 `.gitignore` 로
> 제외된다. **절대 커밋 금지.**

세션 토큰 헤더 = **`X-BSER-SessionKey`** (게임 IL2Cpp 덤프의 `Blis.Common.AuthResult.sessionKey`
로 확인). 값 형식은 `Session:<40자 hex>`. 이 헤더 하나만 뽑아 기록한다.

## 구성

| 파일 | 역할 |
|---|---|
| `install_ca.ps1` | mitmproxy CA 를 신뢰 루트에 원클릭 설치 (최초 1회) |
| `run.ps1` | `--mode local:EternalReturn.exe` 로 게임 프로세스만 투명 가로채기 |
| `capture_addon.py` | `X-BSER-SessionKey` **딱 그것만** 추출 → `session_tokens.log` 기록 |
| `get_replay.py` | gameId → 리플레이 UUID/URL 조회 (최신 토큰 자동 사용) |
| `session_tokens.log` | 잡힌 세션키 (gitignore) |
| `flows.mitm` | 원본 flow (gitignore, `mitmweb -r flows.mitm` 로 재열람) |

## 세션 캡처

### 방식 — local 모드

`mitmdump --mode local:EternalReturn.exe` : EternalReturn.exe 프로세스의 트래픽만
WinDivert 로 투명하게 가로챈다. 시스템 프록시를 안 건드려서 다른 앱 트래픽은 그대로.
(local 모드는 **관리자 권한** 필요 — `run.ps1` 이 권한 체크함.)

### 1) CA 인증서 설치 (최초 1회)

HTTPS 를 해독하려면 mitmproxy 의 CA 를 신뢰 저장소에 넣어야 한다.
**주의: local 모드에선 `http://mitm.it` 페이지가 안 뜬다**(브라우저는 프록시를 안 타므로).
그래서 디스크에 이미 생성된 CA 파일을 직접 설치한다.

파일 위치: `%USERPROFILE%\.mitmproxy\mitmproxy-ca-cert.cer`
(없으면 `mitmdump` 를 한 번 실행하면 생성됨)

**설치 (택1):**

- **원클릭 스크립트 (가장 쉬움):**
  ```powershell
  powershell -ExecutionPolicy Bypass -File .\install_ca.ps1
  ```
  CA 파일이 없으면 자동 생성하고, 신뢰 루트에 설치한다. **보안 경고 팝업이 뜨면 "예".**

- **탐색기에서 파일 더블클릭** → "인증서 설치" → **현재 사용자** → "모든 인증서를 다음
  저장소에 저장" → 찾아보기 → **"신뢰할 수 있는 루트 인증 기관"** → 다음 → 마침 →
  **보안 경고 팝업이 뜨면 "예" 클릭** ← 이 확인 버튼을 꼭 눌러야 설치된다.

- 또는 PowerShell 에서 직접:
  ```powershell
  Import-Certificate -FilePath "$env:USERPROFILE\.mitmproxy\mitmproxy-ca-cert.cer" `
    -CertStoreLocation Cert:\CurrentUser\Root
  ```
  실행하면 같은 **보안 경고 팝업**이 뜨고 **"예"** 를 눌러야 신뢰 저장소에 들어간다.

> 설치 확인:
> ```powershell
> Get-ChildItem Cert:\CurrentUser\Root | Where-Object { $_.Subject -match 'mitmproxy' }
> ```

### 2) 실행 → 로그인

**관리자 PowerShell** 에서 (레포를 클론한 폴더에서):

```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

게임을 실행해서 로그인하면(mitmdump 먼저 켜도 되고 게임 먼저 켜도 됨) `X-BSER-SessionKey`
가 요청에 실려 나갈 때 `session_tokens.log` 에 쌓인다. `Ctrl+C` 로 종료.

실시간 확인:
```powershell
Get-Content .\session_tokens.log -Wait
```

## gameId → 리플레이 UUID (`get_replay.py`)

캡처된 **최신 세션키**(`session_tokens.log` 맨 끝)를 자동으로 읽어 공식 `findReplayGame`
API 를 호출한다.

```bash
python get_replay.py 64466684                 # UUID·URL 출력
python get_replay.py 64466684 --download      # .er 파일까지 내려받기
python get_replay.py 64466684 --user 1234567  # userNum 직접 지정
python get_replay.py 64466684 --json          # JSON 한 줄(파이프라인용)
```

- 엔드포인트: `GET /api/external/findReplayGame/{gameId}/{userNum}`
- userNum 자동 해결: `--user` > 환경변수 `ER_OWN_USERNUM`(본인 계정) > 그 게임 참가자 순회.
  (외부 리플레이 API 는 userNum 이 그 게임 참가자여야 200 이 나온다.)
- userNum 은 오픈 API `/v1/user/nickname` 로도 얻는 공개 번호. 매번 안 넣으려면:
  ```powershell
  $env:ER_OWN_USERNUM = "1234567"
  ```
- 세션 만료 시 `401` → 게임에서 재로그인하면 로그에 새 토큰이 찍히고 스크립트가 자동으로 최신 걸 씀.

## 안 잡히면

- **CA 미설치 / "예" 안 누름**: 대부분 이 경우. 위 설치 + 보안경고 확인을 다시.
- **프로세스명 불일치**: 작업관리자에서 실제 실행 파일명 확인. 런처에서 인증한다면
  `run.ps1` 의 `$process` 를 그쪽(`EternalReturnLauncher.exe` 등)으로 바꿔라.
- **인증서 피닝**: 클라가 자체 CA만 신뢰하면 프록시로 못 뚫음 →
  **메모리 덤프**(`strings -e l EternalReturn.DMP`, .NET 문자열은 UTF-16) / 함수 후킹으로 접근.
- 우선 `flows.mitm` 에 bser 요청이 찍히는지 `mitmweb -r flows.mitm` 로 확인. 요청은 찍히는데
  세션키가 없으면 헤더명 변경 → `capture_addon.py` 의 `SESSION_HEADER` 를 고치면 됨.

## 로그 예시 (토큰은 마스킹)

```
[YYYY-MM-DD HH:MM:SS] X-BSER-SessionKey (request-header)
    Session:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    X-BSER-AuthProvider=STEAM X-BSER-Version=12.2.0
    ↳ bser-rest-release.bser.io/api/users/findPresences
```
