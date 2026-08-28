# 리플레이 int 코드 → GameDB 테이블 매핑

`.er` 리플레이 디코드 결과의 정수 코드들을 사람이 읽을 값으로 푸는 참조표.
데이터는 `fetch_gamedb.py` 로 받는다(공개 CDN, 인증 불필요):

- **GameDB** `gamedb/tables/*.json` — 195개 수치 정의 테이블 (각 행에 `code` PK)
- **l10n** `gamedb/l10n-Korean.txt` — `키┃값` 형식의 코드→표시이름 (약 36,800줄)

## 코드 → 소스

| 리플레이 코드 | GameDB 테이블 (`code`로 조인) | l10n 이름 키 | 비고 |
|---|---|---|---|
| `characterCode` | `Character.json` (91행: maxHp·attackPower·defense·skillAmp…) | `Character/Name/{code}` | 캐릭터 스탯/정의 |
| 상태·버프 코드 | `CharacterState.json` (3,993행: duration·maxStack·statType…) | — | 버프/디버프/상태 (CharacterStateDB) |
| `skillCode` | `Skill.json` (3,398행: level·cost·cooldown…) + `SkillGroup.json` | — | 스킬 (레벨별 행) |
| `itemCode` | `ItemWeapon`(418) `ItemArmor`(252) `ItemConsumable`(54) `ItemMisc`(62) `ItemSpecial`(22) `ItemSkill`(202) | `Item/Name/{code}` | 아이템은 카테고리별 분할 |
| area 코드 (`placeOfStart`/`placeOfDeath`) | `Area.json` (33행: areaType·maskCode…) | `Area/Name/{code}` | 지역 |
| monster 코드 | `Monster.json` (74행: grade·mode·regenTime…) | `Monster/Name/{code}` | 야생동물 |
| trait 코드 | `Trait.json` (148행) | `Trait/Name/{code}` | 특성 |
| `characterLevel` / exp | `Level.json`(600) · `CharacterExp.json` · `CharacterLevelUpStat.json` | — | 레벨/성장 |
| CC(군중제어) | `CrowdControlData.json` · `StateTypeData.json` | — | |
| 투사체 | `Projectile*.json` | — | |

## 사용 예 (파이썬)

```python
import json, glob, os

GD = "gamedb"
def load(name): return json.load(open(f"{GD}/tables/{name}.json", encoding="utf-8-sig"))

# 코드→행 인덱스
chars = {r["code"]: r for r in load("Character")}
states = {r["code"]: r for r in load("CharacterState")}

# l10n: 키┃값
l10n = {}
for line in open(f"{GD}/l10n-Korean.txt", encoding="utf-8"):
    if "┃" in line:
        k, v = line.rstrip("\n").split("┃", 1); l10n[k] = v

# 예: characterCode 74 →
c = 74
print(l10n.get(f"Character/Name/{c}"), chars[c]["maxHp"], chars[c]["attackPower"])
```

## CDN 구조 메모

- 버전 포인터: `{CDN}/gameDb/gamedata-steam.txt` → `gamedata-<yyyymmddhhmmss>.zip`
- l10n 포인터: `{CDN}/l10n/l10n-{Lang}-steam.txt` → `l10n-{Lang}-<ver>.txt`
- 게임 클라이언트가 `GameDBLoader` 로 로드하는 것과 동일 소스(`cdn.eternalreturn.io`).
- 데이터 자체는 님블뉴런 소유물이므로 저장소엔 커밋하지 않는다(스크립트만).
