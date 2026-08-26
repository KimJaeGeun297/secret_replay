# .er Snapshot Crack — Fork Findings (option A, offline solver)

## Structure established (NEW, beyond parent's framing)
- **dakgg snapshots == .er snapshots**: identical 67 ticks incl. irregular first gap (2878→3600 = 722, then 1200). dakgg IS the decoded .er keyframe → perfect ground truth (snap0: 803 entities, 24 PlayerCharacter with exact hp+position).
- **Snapshot size ∝ entity count** (~76.7 bytes/entity, range 63–83). But NO leading entity-count field (803 absent from first 300 bits). Payload leads with header bytes `ab ff ff 00 00 ...` then high-entropy bitstream.
- **No per-entity type tags**: ALL *Snapshot types have packetType=0 in the definitions block (packetType only tags network RPC messages). Cannot segment entities by type id.
- **Entity record is deeply NESTED** (il2cpp schema): CharacterSnapshot = statusSnapshot(**byte[]**, nested BaseCharacterStatusSnapshot: hp,vp,extraPoint,level,shields,moveSpeed), initialStat(**List**), initialStateEffect(**List**), skillController, moveAgentSnapshot(moveStrategyType **enum** → type-selected **byte[]** position payload), inCombatType(enum), bools; then PlayerCharacterSnapshot: characterCode, skinIndex, masteryLevels(**Dict**), teamNumber, isDyingCondition, mapMarks(**Nullable[]**), lockedSlots(**HashSet**)... → variable-length nesting = **no fixed offsets even in keyframes**.
- **Position type = Vector2Int** (plain integers; ×1 == dakgg's values), NOT BlisFixedPoint×100. Corrects parent's assumption. (MoveToDestinationSnapshot.startPositionVector2/destinationVector2 = Vector2Int.)

## Crack attempts (ALL failed, rigorously)
| method | result |
|---|---|
| exact-int ×1 adjacency (bit widths + byte int16 LE) | noise / zero (not byte-aligned; low-entropy bit noise) |
| 4-field co-occurrence cluster (hp,x,y,cc in 400-bit window) | saturated — control(mixed) also 24/24 |
| entity-count at snapshot start | absent (803 not in first 300 bits) |
| packetType entity segmentation | impossible (all snapshot types = 0) |
| tier-0 fixed-length-class, absolute-value corr vs dakgg (tick-aligned) | max 0.577 = noise |
| tier-0 signed-**delta cumsum** corr vs dakgg absolute | 0.949 BUT **spurious** — 5/6 objectIds → same entity 1325 = classic integrated-series false correlation |
| **stationary delta-vs-delta** corr (spurious-proof) | 0.19–0.53, inconsistent entities (1330/1324/1323) → **confirms no recoverable position field** |

## Conclusion
Custom bit-packed "Collection" delta serializer, deeply nested variable-length, signed/zigzag deltas behind per-entity dirty masks. **Positions are NOT recoverable by offline statistical/crib/correlation methods** — the one promising signal (cumsum 0.949) was rigorously disproven as a spurious integrated-series artifact. Full decode requires the serializer's exact primitive bit-read routines (int/varint/collection-count/byte[]-length/bool/enum/Nullable/float), specified only in the ENCRYPTED GameAssembly Serialize/Deserialize method bodies.

## Most promising next step
Offline attack is exhausted AND disproven. Only tractable paths to the primitives:
(a) existing community IL2CPP dump / open-source ER replay parser with deobfuscated Serialize methods, or
(b) runtime memory dump of decrypted GameAssembly image (OUT OF SCOPE — bypass).
Recommend: **stop .er position extraction; dakgg .bin already gives plaintext positions + rich state.**
