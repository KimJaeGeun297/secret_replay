#!/usr/bin/env python3
"""
ER GameDB(수치 테이블) + l10n(코드→이름) 다운로드기.

게임이 쓰는 공개 CDN 에서 받는다(인증 불필요):
  gameDb/gamedata-steam.txt   → 현재 zip 파일명 → gameDb/gamedata-<ver>.zip  (195개 테이블)
  l10n/l10n-Korean-steam.txt  → 현재 txt 파일명 → l10n/l10n-Korean-<ver>.txt

리플레이의 int 코드(characterCode/skillCode/state/area/monster/item 등)를 이 테이블로 푼다.
매핑은 REPLAY_CODE_MAP.md 참고.

사용:
  python fetch_gamedb.py                 # ./gamedb/ 로 받기 (tables/*.json + l10n-Korean.txt)
  python fetch_gamedb.py --lang English  # 다른 언어 l10n
  python fetch_gamedb.py --out C:\er-gamedb
"""
import argparse
import io
import os
import urllib.request
import zipfile

CDN = "http://cdn.eternalreturn.io"
UA = "BestHTTP/2 v2.4.0"


def get(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read() if binary else r.read().decode("utf-8").strip().strip('"')


def fetch_gamedb(out):
    fn = get(f"{CDN}/gameDb/gamedata-steam.txt")          # 예: gamedata-20260827050516.zip
    print(f"[gameDb] {fn}")
    blob = get(f"{CDN}/gameDb/{fn}", binary=True)
    tables_dir = os.path.join(out, "tables")
    os.makedirs(tables_dir, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        z.extractall(tables_dir)
        n = len(z.namelist())
    ver = fn.replace("gamedata-", "").replace(".zip", "")
    with open(os.path.join(out, "gamedb-version.txt"), "w", encoding="utf-8") as f:
        f.write(ver)
    print(f"[gameDb] {n}개 테이블 → {tables_dir}  (버전 {ver})")


def fetch_l10n(out, lang):
    fn = get(f"{CDN}/l10n/l10n-{lang}-steam.txt")         # 예: l10n-Korean-20260820020638.txt
    print(f"[l10n] {fn}")
    txt = get(f"{CDN}/l10n/{fn}", binary=True)
    path = os.path.join(out, f"l10n-{lang}.txt")
    with open(path, "wb") as f:
        f.write(txt)
    print(f"[l10n] {len(txt.splitlines()):,}줄 → {path}")


def main():
    ap = argparse.ArgumentParser(description="ER GameDB + l10n 다운로드")
    ap.add_argument("--out", default="gamedb", help="저장 폴더 (기본: ./gamedb)")
    ap.add_argument("--lang", default="Korean", help="l10n 언어 (기본: Korean)")
    ap.add_argument("--no-l10n", action="store_true")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    fetch_gamedb(args.out)
    if not args.no_l10n:
        fetch_l10n(args.out, args.lang)


if __name__ == "__main__":
    main()
