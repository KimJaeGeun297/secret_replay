# Eternal Return `.er` Replay Format — Reference

Status: **2026-08-26**. Reverse-engineered statically from files we hold (no runtime/anticheat bypass).
Game client v12.1.0. Reference decoder: `er_decode.py` (session scratchpad `66230dd4…`).

This document marks each section **[VALIDATED]** (cross-checked against dakgg + API ground truth) or
**[PARTIAL]** / **[UNRESOLVED]** (structure known but not fully decoded/validated), honestly.

---

## 0. TL;DR

- `.er` = the official replay the client downloads from `cdn.eternalreturn.io`. File = 1056-byte header + a flat sequence of length-prefixed **records**.
- **Every record payload is Brotli-compressed; decompressed = MemoryPack** (Cysharp serializer). Brotli has no magic bytes — that is why earlier analysis mistook it for a "custom bit-packed" stream and declared it uncrackable. It is not: it is two open, documented formats stacked.
- Top object = `ReplaySnapshot` → `GameSnapshot` → per-entity snapshots + global state.
- **[VALIDATED]** per-entity **position, hp, SP, level, shields, moveSpeed** are extractable and match dakgg/API (position: 1608 samples across 67 snapshots, median error 0.43 grid units; hp: 24/24 exact).
- **[PARTIAL]** deep nested player fields (characterCode/teamNumber/skills/traits/buffs/cooldowns) and the delta-packet field layout are located structurally but not fully decoded — see §8.

---

## 1. File layout  [VALIDATED]

```
[0x000..0x420)  Fixed 1056-byte header
    0x000  char[16]  magic   = "EternalReturnV1\0"
    0x010  char[16]  version = "12.1.0"
    0x020  char[]    gamedata CDN url ("http://cdn.eternalreturn.io/gameDb/gamedata-…"), zero-padded to 0x420

[0x410 .. EOF)  Flat sequence of records. NOTE: first record header starts at 0x410 (= HEADER_LEN 0x420 − 16), not 0x420.
```

### Record header (16 bytes, little-endian) — `struct <HHIII>`
| off | type   | field  | meaning |
|-----|--------|--------|---------|
| 0   | uint16 | kind   | record class (see below) |
| 2   | uint16 | ver    | 0=zero-length marker, 1=live record, 2=gzip/side block? (actually Brotli side block) |
| 4   | uint32 | tick   | game tick (60/s) for ver==1; 0 for side blocks |
| 8   | uint32 | length | payload byte length following the header |
| 12  | uint32 | aux    | ver==1: 0; keyframe marker: dup tick |

Payload = `data[off+16 : off+16+length]`.

### Record kinds actually seen (game 63953953, 15.4 MB)  [VALIDATED]
| (kind,ver) | count | meaning |
|-----------|-------|---------|
| (3,2) | 1     | definitions block (Brotli+MemoryPack) — name→packetType table |
| (7,0) | 1     | keyframe marker, length 0, aux = tick, precedes first snapshot |
| (2,1) | 67    | **full-state SNAPSHOT** (keyframe) — Brotli+MemoryPack `ReplaySnapshot` |
| (1,1) | 68359 | **per-entity DELTA packet** — Brotli+MemoryPack (fields not yet decoded) |
| (4,2) | 1     | trailer (Brotli+MemoryPack) — profiling telemetry |
| (0,0) | 1     | EOF marker, length 0 |

Snapshots occur on a regular cadence (first tick 2878, ~every 1200 ticks). `seq` inside the snapshot == the record tick.

### Per-record compression  [VALIDATED]
Each snapshot/delta payload is a standalone **Brotli** stream (`brotli.decompress(payload)`), no framing/magic.
Example: snapshot 51024 B → 334754 B; delta packet 5311 B → 36394 B. All 67/67 snapshots + sampled deltas decompress.

---

## 2. MemoryPack wire format (as observed)  [VALIDATED unless noted]

MemoryPack = Cysharp zero-encoding serializer. Little-endian throughout.

| construct | encoding |
|-----------|----------|
| int/uint/enum(int) | 4 bytes LE |
| long/ulong | 8 bytes LE |
| short/ushort | 2 bytes LE; byte/sbyte/bool | 1 byte |
| float | 4 bytes IEEE-754; double | 8 bytes |
| **object** | 1 byte **member-count header** (0..249 = number of serialized members; **0xFF = null**), then members in `[MemoryPackOrder]` order. Inheritance: base members (lower orders) precede derived. |
| **collection** (`T[]`, `List<T>`) | int32 length prefix (**−1 = null**), then N elements |
| **byte[]** | int32 length prefix (−1=null), then raw bytes. Nested snapshots are stored as `byte[]` = a *separate* MemoryPack blob (recurse). |
| **string** | `[int32 a][int32 utf16Len][utf8 bytes]` where **utf8Len = ~a** (a is negative). `a==0`→"", `a==−1`→null. |
| **Vector2Int** | 2× int32 (x,y). **Vector2** | 2× float. **Vector3** | 3× float. **Quaternion** | 4× float. |
| **BlisFixedPoint** | object{ int internalValue }; world value = internalValue/100. |
| enum | underlying int width (ObjectType/InWorldType/MoveStrategyType = 4 bytes) |
| Nullable<T> / Dictionary<K,V> / HashSet<T> | **[PARTIAL]** implemented as (1-byte flag + value) / (int32 count + pairs) / (int32 count + elems) per MemoryPack spec, but not yet empirically confirmed on real bytes |
| **union** (`[MemoryPackUnion]`, e.g. SnapshotWrapper) | **[PARTIAL]** — see §6 |

### String, worked example  [VALIDATED on 24 nicknames]
Nickname "고순조" (UTF-8 = 9 bytes, 3 chars) is preceded by:
`f6 ff ff ff  03 00 00 00` = int32 −10 (~−10 = 9 = utf8Len), int32 3 (utf16Len), then the 9 UTF-8 bytes.

---

## 3. Container hierarchy  [VALIDATED to GameSnapshot; deeper members PARTIAL]

Top object = **`ReplaySnapshot`** (schema: 976 MemoryPackable classes in `schema.json`).

```
ReplaySnapshot (8 members)
 0 int              targetFrameRate      = 60            [VALIDATED]
 1 long             gameId               = 63953953      [VALIDATED]
 2 List<long>       userIds              (25; [0]=Int64.MinValue sentinel) [VALIDATED]
 3 int              seq                  = 2878 (== snapshot tick)         [VALIDATED]
 4 GameSnapshot     gameSnapshot         (39 members)    [VALIDATED header]
 5 List<UserInfo>   userList
 6 List<CharacterSightInfo> characterSightList
 7 Dictionary<int,List<Item>> itemBoxes
```

Decoded top-level bytes of snap0 (decompressed): `08 | 3c000000 | 21dccf03 00000000 | 19000000 …`
= header 8 members, targetFrameRate 60, gameId 63953953 (long), userIds count 25 …

```
GameSnapshot (39 members)   [VALIDATED header=39; member types from schema]
 0  List<UserSnapshot>                       userList            (=24 players)
 1  List<SnapshotWrapper>                     worldSnapshot       (all ~803 entities, union)
 2  Dictionary<int,MoveAgentSnapshot>         moveAgentSnapshots  (objectId→movement)
 3  BlisFixedPoint areaRestrictionRemainTime
 4  Dictionary<int,AreaState> areaStateMap
 5  DayNight dayNight        6 int day       7 bool isStopAreaRestriction
 8  Dictionary<MonsterType,List<BossMonsterSpawnInfo>> bossMonsterSpawnTimes
 9  Dictionary<SubSightSnapshotType,List<byte[]>> subSights
 …  (20 phase; 25 gamePlayPhase; 26-29 phase times; 30 escapeItems; 31 teamVoteData;
     34 creditShopSnapshot; 36 ObjectTimelineSnapshot; 38 riftLaboratoryAreaStateMap; …)
```
(Full 39-member list: see `schema.json` → GameSnapshot.)

`UserSnapshot` (14 members): 0 long userId, 1 SnapshotWrapper characterSnapshot, 2 byte[] playerSnapshot,
3 List<EquipItem> equips, 4 int walkableNavMask, 5 int exp, 6 BlisFixedPoint survivalTime,
7 List<InvenItem> inventoryItems, 8 List<BulletItem> bulletItems, 9 List<TeammateRoute> teammateRouteList,
10 UserInGameRoute route, 11 string voiceChannelName, 12 JoinChannelType voiceChannelType, 13 byte[] deathRecapOverlayInfoSnapshot.

---

## 4. Entity records — position + status  [VALIDATED]

In a decompressed snapshot, each character entity is emitted as a record with the byte **signature**:
```
07 02 00 00 00  <objectId:int32>
```
(`07` = MemoryPack object header/7 members; `02 00 00 00` = objectType enum = 2 = PlayerCharacter.)
Players have objectId 1317..1340 (map 1:1 to dakgg `users[].id`). The same signature with other objectIds
covers monsters/summons/etc.

### Field offsets from the record start  [VALIDATED: position 1608 samples, hp 24/24]
| offset | type  | field | notes |
|--------|-------|-------|-------|
| +0  | byte  | member header (0x07) | |
| +1  | int32 | objectType (2=PlayerCharacter) | |
| +5  | int32 | **objectId** | 1317..1340 = players |
| +9  | float | **positionXZ.x** (world) | |
| +13 | float | **positionXZ.z** (world) | |
| +17..+39 | — | positionY / rotation / inWorldType / nested-status header | [PARTIAL] not individually mapped |
| +40 | int32 | **hp** | matches dakgg 24/24 |
| +44 | int32 | **sp** (vp) | 0 early game |
| +48 | int32 | extraPoint | |
| +52 | int32 | **level** | |
| +56 | int32 | blockAllShield | |
| +60 | int32 | blockNormalShield | |
| +64 | int32 | blockSkillShield | |
| +68 | float | **moveSpeed** | 3.58–3.72 (varies per character) |

`+40..+68` is a `BaseCharacterStatusSnapshot` (hp, vp, extraPoint, level, 3 shields, moveSpeed) laid inline.

### Coordinate systems + transform  [VALIDATED]
- `.er` stores **world** coords as `positionXZ` (Vector2 float, X/Z plane).
- dakgg / API `placeOf*` use a **minimap grid** (integers, ~0..1000).
- world → dakgg grid is a fixed **isometric affine** (fit on 24 points, residual median 0.40 / max 0.59):
  ```
  gridX = -1.645 * (worldX + worldZ) + 290.1
  gridY = -1.653 *  worldX + 1.652 * worldZ + 555.0
  ```
  (≈ 45° rotation, scale ≈ 2.33, translate.) Inverse is straightforward to derive if world coords are needed.

### Worked example — entity 1340 (고순조), snap0 tick 2878, decompressed offset 106184
```
07 | 02 00 00 00 | 3c 05 00 00 | ec 91 1a c3 | 85 6b 8d c2 | 01 18 00 00 00 32 06 00 00 01 00 00 00 f8 03 00 00 31 52 00 00 00 14 | 42 04 00 00 | 00 00 00 00 | 00 00 00 00 | 01 00 00 00 | 00…(shields)… | 7b 14 6e 40
hdr=7  objType=2      objId=0x53c=1340  posX=-154.57f      posZ=-70.71f     (+17..+39 middle fields)                                   hp=0x442=1090  sp=0        extra=0     level=1        shields=0        moveSpeed=3.72f
→ to_grid(-154.57,-70.71) = (660.7, 693.7)  ;  dakgg says (661,694)  ✓
```

---

## 5. Extraction recipes

- **Positions (all entities, all snapshots)**: for each (2,1) record → `brotli.decompress` → scan for `07 02 00 00 00` → read objectId(+5), posXZ(+9,+13) → `to_grid`. → trajectories. (`er_decode.extract_entities`, `er_positions.py`.)
- **hp / SP / level / shields / moveSpeed**: same record, offsets +40..+68.
- **Player identity**: objectId 1317+ → dakgg `users[].id` → nickname/characterCode/teamNumber (from API, since these are not yet located in `.er` itself — see §8).
- **Deaths timeline**: derive from API per-player `duration` (survival) + `placeOfDeath`/killer, cross-checked to the replay's last tick. (See `replay_63953953_deaths.md`; and [[reference_dakgg_replay]] for the dakgg event stream `CmdDead`/`CmdKill`.)
- **Skill casts / damage / heals**: **[from dakgg, not yet from .er]** dakgg `.bin` chunks give `CmdPlaySkillAction`, `CmdDamage`, `CmdHeal`, `CmdStartActionCasting` in plaintext. Extracting these from `.er` requires decoding the delta packets / projectile snapshots (§8).
- **Dense trajectory (for the replay viewer)**: `er_dense_traj.json` = per-objectId `{nickname, characterCode, traj:[[tick,gridX,gridY,hp],…]}`, 24 entities / 62,213 points / ~2 Hz. Source: dakgg `moves` (grid coords, validated median <0.5 vs the affine) + hp sampled from `.er` snapshots. This replaces the 20 s snapshot cadence and renders hyperloop/dashes smoothly. (The raw `.er` ~4 Hz delta stream would be denser but is not yet cleanly walkable — §7.)

---

## 6. Unions  [RESOLVED empirically]

`SnapshotWrapper` (abstract, `[MemoryPackUnion(0)]`,`[MemoryPackUnion(1)]`) base members (dump.cs):
`0 ObjectType objectType, 1 int objectId, 2 InWorldType inWorldType, 3 byte[] snapshot`.
Subtypes: **SnapshotWrapperBasic** (no extra members → 4) and **SnapshotWrapperFull** (+ Vector2 positionXZ,
int positionY, uint blisLiteRotation → 7).

**Resolution (validated on real bytes):** in `worldSnapshot`, each element is serialized as its concrete object
with a member-count header byte — **0x07 = SnapshotWrapperFull, 0x04 = SnapshotWrapperBasic** — and the
`objectType` field (member #1) is the entity-kind discriminator. No `0xFA` union sentinel and no separate tag byte
precede the record (0xFA occurs only 199× and the byte before each record is 0x00 153/158 times = not a tag).
snap0 has **158 SnapshotWrapperFull + 2 Basic** entity records; objectType distribution: `2`=PlayerCharacter (24),
`14` (74), `3` (49), `12` (4), `1` (3), `11` (3), `0` (1).

**Serialize-order caveat:** the observed field order (positionXZ right after objectId, at +9) does not match the
`[MemoryPackOrder]` values dumped by IL2CppDumper (which place inWorldType + snapshot byte[] before positionXZ),
and IL2CppDumper strips the union `typeof(...)` args. The authoritative order lives in `Assembly-CSharp.dll`
metadata; extracting it via **dnfile** (pure-python) is impractically slow here — see §8. The working extractor
(§4) therefore uses empirically-validated fixed offsets, which are correct and validated (§9). This is sufficient
for position/hp/stats but not yet for the deep nested `snapshot` byte[] (player skills etc.).
Empirical map saved to `mempack_meta.json`.

---

## 7. Delta packets (kind=1)  [STRUCTURE decoded; clean field-walk PARTIAL]

68,359 packets (the bulk). Each payload = **Brotli → MemoryPack** (e.g. 5311→36394 B). Decoded structure:
```
byte  header (0x05)
int32 tick
int32 a            (=0 observed)
int32 count        (number of per-entity records; e.g. tick2879 → 9, tick2878 → 1036)
record × count     each: [recordTag byte][objId int32][ nested (fieldTag, value) … ]
```
**field-tag `0x02` = position** = `posX float, posZ float` (→ `to_grid`). Crib-validated: tick 3616, the record
`02 3a 05 00 00 | c9 f0 95 c1 | 5e 26 79 42` = objId 1338, pos (−18.74, 62.29) → grid (218.5, 688.9) ✓.
Other field-tags (03/04/09/…) carry hp/stat/state deltas.

**Blocker (clean extraction):** records are variable-length nested dirty-field encodings; walking them exactly
needs the per-field schema (authoritative MemoryPack orders — §8, dnfile-gated). Naive byte-scanning for `02 <objId>`
is too noisy (median error ~242 grid units from coincidental `0x02` bytes). So per-tick `.er` positions at the raw
~4 Hz rate are **not yet cleanly extractable**. For the viewer's dense trajectory we ship the dakgg-derived
2.6 Hz stream instead (validated, §9) — see `er_dense_traj.json`.

---

## 8. What is NOT yet decoded (honest gaps + exact blocker)

1. **Deep player fields** — characterCode, teamNumber, skinIndex, skills, traits, buffs/debuffs, cooldowns,
   equipment timeline. These live in `PlayerCharacterSnapshot`, inside either the worldSnapshot record's nested
   `byte[] snapshot` (last member) or `UserSnapshot.playerSnapshot` (a separate structure in `userList`, distinct
   from the 158 worldSnapshot entities). A crib search for known characterCode/teamNumber/skinCode as raw int32
   across the full entity span found **no** consistent offset — consistent with them sitting inside the nested
   `snapshot` byte[] which requires the authoritative field order to reach.
   **Exact blocker:** the true `[MemoryPackOrder]` for SnapshotWrapperFull / PlayerCharacterSnapshot (dump.cs's
   order disagrees with observed bytes, §6). It is in `Assembly-CSharp.dll` (DummyDll) metadata, but the
   pure-python **dnfile** parse of its **484,704 CustomAttribute** rows is impractically slow in this environment
   (loads fine with `clr_lazy_load=True`, but per-attribute coded-index resolution does not complete in budget).
   **Fix path:** extract the union/order map with a faster .NET metadata reader (ILSpy/monodis/ildasm, or dnfile
   run offline with more time / raw-token filtering), then feed orders into `er_mempack.py`. Meanwhile
   characterCode/teamNumber are available from the API/dakgg by objectId.
2. **Delta packet fields** (§7) — Brotli+MemoryPack confirmed, field layout not decoded.
3. **Skill aim coordinates / projectile snapshots** — projectile union subtypes
   (targetDirectionEndPos / projectileDirection / aroundTargetPosition) not parsed (same blocker as #1).
4. **Global state** — areaStateMap, boss spawns, creditShop, rift, teamVote, objectTimeline: types are in
   `schema.json` but not decoded end-to-end.
5. **Nullable / Dictionary / HashSet** encodings implemented per-spec but not empirically confirmed.

The general recursive reader (`er_mempack.py`) parses the container correctly through `GameSnapshot`/`userList`;
the empirical extractor (`er_decode.py`) handles worldSnapshot entity position/hp/stats. Resolving the field-order
blocker (#1) unblocks the deep nested fields and a fully-general worldSnapshot walk.

---

## 9. Validation summary  [VALIDATED]

Cross-checked against dakgg `rosetta.json` (same game, decoded `.er`, tick-aligned) + API `game.json`:

| item | result |
|------|--------|
| Format (Brotli+MemoryPack) | 67/67 snapshots + sampled deltas decompress |
| Container fields | targetFrameRate=60, gameId=63953953, seq=tick, userList=24 — all exact |
| String encoding | 24/24 nicknames decode |
| **Position** | **1608 (entity×snapshot) samples, 67 snapshots, median err 0.43, p90 1.35 grid units** |
| **hp** | **24/24 exact** vs dakgg snapshot |
| level / moveSpeed | level=1 @48s (correct); moveSpeed 3.58–3.72 (per-character, realistic) |
| characterCode/teamNumber | not located in .er (gap §8-1); available via API |
| skill casts / deaths | via dakgg/API, not yet from .er |
| delta packet structure | header/tick/count + fieldTag 02=position decoded; crib-validated (id1338 tick3616); clean walk gated (§7) |
| **dense trajectory** (`er_dense_traj.json`) | **24 entities, 62,213 pts, ~2 Hz, grid-validated** (dakgg source + .er snapshot hp) |

---

## 10. Acquisition (reference only — no bypass)

- **dakgg** (rehost, no auth): `GET https://er.dakgg.io/api/v1/rpc/replay?gameId=<id>` (poll `{retryAfter}`)
  → `https://er-replay.dakgg.net/v4/<id>.bin` → AES-128-CBC (key=IV=all-zero) → plaintext JSON.
  This is dakgg's *decoded* form of the same `.er` and is the practical source. See [[reference_dakgg_replay]].
- **Official** (`cdn.eternalreturn.io/…/<id>.er`): the client-authenticated endpoint; the raw `.er` this
  document describes. Bulk automated download is game-company infrastructure and ToS-sensitive — reference only.

**Do not mass-scrape either source.** For features, fetch on-demand per user request + cache.

---

## 11. Code (session scratchpad `…/66230dd4…/scratchpad`)
- `er_decode.py` — consolidated decoder: framing, Brotli, string, per-entity position/hp/status extractor + world→grid affine.
- `er_positions.py` — trajectory extraction across all 67 snapshots + 1608-sample validation.
- `er_extract.py` — per-player status table.
- `er_mempack.py` — general recursive MemoryPack reader (container OK; nested drift at union, §6).
- `build_schema.py` + `schema.json` — full type schema (976 MemoryPackable classes) auto-extracted from IL2CppDumper `dump.cs`.
- `snap0.raw` — decompressed first snapshot (for iteration).
- `er_dense_traj.json` — per-objectId ~2 Hz trajectory + hp for the whole match (viewer input).
- `mempack_meta.json` — empirical union resolution + validated offsets.
