#!/usr/bin/env python3
"""
gameId → 리플레이 UUID / 다운로드 URL 자동 조회.

캡처된 최신 세션 토큰(session_tokens.log 의 X-BSER-SessionKey)을 읽어
공식 findReplayGame API 를 호출한다. userNum 은 자동 해결:
  1) --user 로 지정한 값
  2) 본인 계정(OWN_USERNUM)
  3) 그래도 안 되면 그 게임 참가자 userNum 을 순회하며 재시도
(외부 리플레이 엔드포인트는 userNum 이 그 게임 참가자여야 200 이 나옴)

사용:
  python get_replay.py 64466684
  python get_replay.py 64466684 --user 1234567
  python get_replay.py 64466684 --download           # .er 파일까지 내려받기
  python get_replay.py 64466684 --download --out C:\path\game.er

자기 계정 세션으로 리플레이 데이터 조회 용도. 트래픽 변조 없음.
"""
import argparse
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
TOKEN_LOG = os.path.join(HERE, "session_tokens.log")

HOST = "https://bser-rest-release.bser.io"
# 본인 계정 userNum. 환경변수 ER_OWN_USERNUM 로 설정(미설정이면 게임 참가자로 자동 폴백).
# userNum 은 오픈 API(/v1/user/nickname)로도 얻는 공개 번호라 비밀은 아니지만,
# 저장소엔 안 박고 로컬 환경변수로 둔다.
OWN_USERNUM = int(os.environ["ER_OWN_USERNUM"]) if os.environ.get("ER_OWN_USERNUM") else None
VERSION = "12.2.0"
PROVIDER = "STEAM"

# HTTPS: bser 정식 인증서라 원래 검증돼야 하지만, 로컬 CA(mitmproxy) 신뢰 등
# 환경차로 막히는 경우를 피하려고 검증 생략(관찰/조회 전용이라 무방).
_SSL = ssl.create_default_context()
_SSL.check_hostname = False
_SSL.verify_mode = ssl.CERT_NONE


def latest_token():
    if not os.path.exists(TOKEN_LOG):
        sys.exit(f"[에러] {TOKEN_LOG} 없음 — run.ps1 로 먼저 세션키를 캡처해라")
    txt = open(TOKEN_LOG, encoding="utf-8").read()
    hits = re.findall(r"Session:[0-9a-fA-F]{16,}", txt)
    if not hits:
        sys.exit("[에러] session_tokens.log 에 세션키 없음 — 게임 로그인 후 재시도")
    return hits[-1]  # 파일 맨 끝 = 가장 최신 발급분


def api_get(path, token):
    req = urllib.request.Request(HOST + path, method="GET")
    req.add_header("X-BSER-Version", VERSION)
    req.add_header("X-BSER-AuthProvider", PROVIDER)
    req.add_header("X-BSER-SessionKey", token)
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "BestHTTP/2 v2.4.0")
    try:
        with urllib.request.urlopen(req, timeout=25, context=_SSL) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, {}


def participants(game_id, token):
    st, data = api_get(f"/api/battle/game/{game_id}", token)
    if st != 200:
        return []
    games = (data.get("rst") or {}).get("battleUserGames") or []
    return [g.get("userNum") for g in games if g.get("userNum")]


def find_replay(game_id, user_num, token):
    return api_get(f"/api/external/findReplayGame/{game_id}/{user_num}", token)


def resolve(game_id, token, explicit_user):
    """(replayPath, used_userNum) 반환. 못 찾으면 (None, tried_set)."""
    tried = []
    if explicit_user:
        order = [explicit_user]
    else:
        order = [OWN_USERNUM] if OWN_USERNUM else []
    # 폴백용 참가자 목록(명시 userNum 이 없을 때만)
    fallback = [] if explicit_user else None

    idx = 0
    while True:
        if idx < len(order):
            un = order[idx]
            idx += 1
        else:
            if fallback is None:
                break
            if not fallback:  # 참가자 목록 아직 안 가져왔으면 채우기
                fallback = [u for u in participants(game_id, token) if u not in order]
                if not fallback:
                    break
            un = fallback.pop(0)
        if un in tried:
            continue
        tried.append(un)
        st, data = find_replay(game_id, un, token)
        if st == 401:
            sys.exit("[에러] 401 — 세션 만료. 게임에서 재로그인하면 로그에 새 토큰이 찍힌다")
        path = (data.get("rst") or {}).get("replayPath")
        if st == 200 and path:
            return path, un, tried
    return None, None, tried


def main():
    ap = argparse.ArgumentParser(description="gameId → 리플레이 UUID/URL")
    ap.add_argument("gameId", type=int)
    ap.add_argument("--user", type=int, default=None, help="userNum 명시 (기본: 본인→참가자 자동폴백)")
    ap.add_argument("--download", action="store_true", help=".er 파일까지 내려받기")
    ap.add_argument("--out", default=None, help="다운로드 경로")
    ap.add_argument("--json", action="store_true", help="결과를 JSON 한 줄로만 출력")
    args = ap.parse_args()

    token = latest_token()
    if not args.json:
        print(f"[토큰] …{token[-8:]}   게임 {args.gameId}")

    path, used, tried = resolve(args.gameId, token, args.user)
    if not path:
        sys.exit(f"[실패] 리플레이 못 찾음 (시도한 userNum: {tried})")

    m = re.search(r"/(\d+)-([0-9a-fA-F]+)\.er", path)
    uuid = m.group(2) if m else "?"
    result = {"gameId": args.gameId, "userNum": used, "uuid": uuid, "replayPath": path}

    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(f"[userNum] {used}")
        print(f"[UUID] {uuid}")
        print(f"[URL ] {path}")

    if args.download:
        out = args.out or os.path.join(HERE, os.path.basename(path))
        if not args.json:
            print(f"[다운로드] → {out}")
        with urllib.request.urlopen(path, timeout=60, context=_SSL) as r, open(out, "wb") as f:
            f.write(r.read())
        if not args.json:
            print(f"[완료] {os.path.getsize(out):,} bytes")


if __name__ == "__main__":
    main()
