# .er FULLY DECODED — position + hp + stats extracted & validated (2026-08-26)

## FORMAT (confirmed)
`.er` record payload = **Brotli-compressed → MemoryPack**. 67/67 snapshots + delta packets decompress.
Container: **ReplaySnapshot**{targetFrameRate=60, gameId(long), userIds:List<long>, seq(=tick), gameSnapshot:GameSnapshot, ...} — parses byte-perfect.

## BLOCKER 1 — MemoryPack encodings
- **string** CRACKED: `[int32 a][int32 utf16len][utf8 bytes]` where utf8len=~a (a is negative). a==0→"", a==-1→null. Validated on all 24 nicknames (고순조: f6ffffff=~9, 03000000=3 chars, +9 bytes).
- **object** = 1 byte member-count header (0xFF=null). int=4B LE, long=8B LE, float=4B, List<T>=int32 len prefix.
- Nullable/union full-tree descent not needed — see Blocker 2 method.

## BLOCKER 2 — POSITION: SOLVED ✅
Per-entity records carry the current world position + full status block directly (SnapshotWrapperFull-style).
**Record signature** (decompressed snapshot): `07 02 00 00 00 <objId int>` then:
```
+0  0x07  (MemoryPack member header)
+1  objectType int (=2 PlayerCharacter)
+5  objectId int   (players = 1317..1340; maps to dakgg users[].id)
+9  positionXZ.x  float  (world)
+13 positionXZ.z  float  (world)
+40 hp int
+44 sp (vp) int
+48 extraPoint int
+52 level int
+56 blockAllShield int
+60 blockNormalShield int
+64 blockSkillShield int
+68 moveSpeed float
```
**World→dakgg grid affine** (fit on 24 pts, residual median 0.40 / max 0.59):
`gridX = -1.645*(fx+fz) + 290.1 ;  gridY = -1.653*fx + 1.652*fz + 555.0`  (isometric projection)

## VALIDATION (vs dakgg same game)
- Position: **1608 (entity×snapshot) samples across 67/67 snapshots, median error 0.43 grid units, p90 1.35** (float→int rounding). snap0: all 24 players match dakgg exactly.
- hp @+40: **24/24 exact** vs dakgg snapshot hp.
- level=1 for all @ tick2878 (48s, correct); moveSpeed 3.58–3.72 (realistic, varies per character).

## EXTRA FIELDS now readable that dakgg DROPS
SP(vp), extraPoint, blockAll/Normal/Skill shields, level, moveSpeed(float), worldXZ float precision, positionY — all per entity per snapshot. (dakgg only kept MaxHp.)
characterCode/teamNumber live in the deeper nested `snapshot` byte[] (not yet parsed) but entities are identified by objectId→API/dakgg mapping, and those two values are already in the API.

## FILES (66230dd4 scratchpad)
- `er_extract.py` — FINAL: .er → per-player {objectId, pos(grid), worldXZ, hp, sp, level, shields, moveSpeed}.
- `er_positions.py` — trajectory extraction + 1608-sample validation across all snapshots.
- `er_mempack.py` — recursive container parser; `build_schema.py`+`schema.json` — full type schema (976 classes).
- `snap0.raw` — decompressed first snapshot.

## VERDICT
Prior "uncrackable" conclusion fully overturned. `.er` = Brotli+MemoryPack, positions+hp+full stats extractable offline, cross-validated on 1608 samples. No runtime/anticheat bypass used.
