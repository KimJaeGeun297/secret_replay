"""
ER 세션 토큰 캡처 mitmproxy 애드온 (핀포인트 버전).

게임 코드(IL2Cpp 덤프)로 확인한 세션 토큰 헤더 = X-BSER-SessionKey.
 - 로그인/인증 응답 Blis.Common.AuthResult.sessionKey 로 발급되고,
 - 이후 bser-rest 요청에 X-BSER-SessionKey 헤더로 실려 나감.

이 애드온은 그 세션키 하나만 뽑아 session_tokens.log 에 남긴다(값 바뀔 때만).
동반 헤더(X-BSER-Handle=유저번호 등)는 어느 계정 토큰인지 식별용 컨텍스트로만 같이 적음.

- 자기 계정 인증 토큰의 로컬 관찰 용도. 트래픽 변조·재전송 없음.

실행:  mitmdump --mode local:EternalReturn.exe -s capture_addon.py   (run.ps1 이 대신 띄움)
"""
import json
import os
import re
import time

from mitmproxy import http, ctx

LOG_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_LOG = os.path.join(LOG_DIR, "session_tokens.log")

# 세션 토큰 헤더 (게임 코드에서 확인)
SESSION_HEADER = "X-BSER-SessionKey"
# 어느 계정/버전인지 식별용 동반 헤더 (토큰 아님, 컨텍스트로만 기록)
CONTEXT_HEADERS = ("X-BSER-Handle", "X-BSER-AuthProvider", "X-BSER-Version")

# 로그인 응답 본문(AuthResult)에서 세션키 발급 잡기
BODY_KEY_RE = re.compile(r'"sessionKey"\s*:\s*"([^"]+)"')

_seen = set()  # 같은 세션키 반복 기록 방지


def _ts() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _write(text: str) -> None:
    with open(TOKEN_LOG, "a", encoding="utf-8") as f:
        f.write(text + "\n")


def _log(session_key: str, source: str, host: str, path: str, context: str = "") -> None:
    if session_key in _seen:
        return
    _seen.add(session_key)
    ctxline = f"\n    {context}" if context else ""
    _write(
        f"[{_ts()}] {SESSION_HEADER} ({source})\n"
        f"    {session_key}{ctxline}\n"
        f"    ↳ {host}{path}"
    )
    ctx.log.info(f"[SESSION KEY] 캡처됨 → session_tokens.log  (…{session_key[-8:]})")


def request(flow: http.HTTPFlow) -> None:
    # 요청 헤더에 실려 나가는 세션키
    key = flow.request.headers.get(SESSION_HEADER)
    if key:
        ctx_bits = [
            f"{h}={flow.request.headers.get(h)}"
            for h in CONTEXT_HEADERS
            if flow.request.headers.get(h)
        ]
        _log(key, "request-header", flow.request.pretty_host, flow.request.path,
             " ".join(ctx_bits))


def response(flow: http.HTTPFlow) -> None:
    # 로그인/인증 응답 본문에서 새로 발급된 세션키
    ctype = flow.response.headers.get("content-type", "").lower()
    if "json" not in ctype and "text" not in ctype:
        return
    try:
        body = flow.response.get_text()
    except Exception:
        return
    m = BODY_KEY_RE.search(body or "")
    if m:
        _log(m.group(1), "login-response", flow.request.pretty_host, flow.request.path)


def load(loader) -> None:
    _write(f"\n===== 캡처 세션 시작 {_ts()}  (target header: {SESSION_HEADER}) =====")
    ctx.log.info(f"ER 세션 토큰 캡처 시작 — {SESSION_HEADER} 만 노린다요.")
