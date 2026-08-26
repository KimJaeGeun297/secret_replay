# ER 3D 맵 → GLB Export (three.js 리플레이 뷰어용)

`.er` 리플레이를 실제 3D 맵 위에서 재생하기 위해, Unity에서 맵 프리팹을 `.glb`로 뽑는 절차.

## 대상 프리팹 (AssetRipper export 안)
`Assets/Resources/prefabs/map/` :
- **`DetailedMap.prefab`** → 본섬(루미아) 3D 맵 — **필수**
- **`RiftMap_A.prefab`**, **`RiftMap_B.prefab`** → 균열 맵
- `CobaltMap.prefab` → 코발트 프로토콜 (선택)

> `DefaultMap`/`StrategyMap`은 미니맵 UI(2D)라 제외. 3D 지오메트리는 `DetailedMap`에.

## 절차 (Unity 6000.3.20f1)

1. **프로젝트 열기**: Unity Hub → Add → `webgame/AssetRipper_export_20260821_054547/ExportedProject` 선택 (버전 6000.3.20f1 권장). 셰이더/스크립트 에러가 많이 떠도 **무시** — 메시·텍스처는 로드됨.

2. **glTFast 설치**: `Window > Package Manager > + > Add package by name` → `com.unity.cloud.gltfast`

3. **익스포터 스크립트 배치**: `MapGlbExporter.cs`(이 폴더)를 프로젝트의 `Assets/Editor/`에 복사.

4. **맵 export**:
   - Project 창에서 `DetailedMap.prefab`을 **Hierarchy로 드래그** (씬에 인스턴스화)
   - Hierarchy에서 그 오브젝트 **선택**
   - 메뉴 **`Tools > Export Selected → GLB`**
   - `<프로젝트루트>/MapExport/DetailedMap.glb` 생성됨
   - `RiftMap_A`, `RiftMap_B`도 각각 반복

5. **결과 전달**: 생성된 `.glb` 파일들을 `secret_replay_upload/data/`로 복사.
   - `DetailedMap.glb` (본섬), `RiftMap_A.glb`, `RiftMap_B.glb`

## 좌표계 노트 (뷰어 정렬용)
- Unity 월드좌표 = `.er` 월드좌표. 플레이어 `positionXZ(x,z)` + `positionY(높이)`가 맵과 같은 공간.
- Unity(왼손 Y-up) → glTF(오른손 Y-up): glTFast가 X축 부호를 뒤집어 변환. three.js에서 플레이어 좌표도 **x → -x** 맞춰주면 정렬됨(뷰어에서 처리).
- 스케일 1:1. `.er`의 x,z를 그대로 three.js 위치로.

## 문제 대응
- **Export 실패/Draco 에러**: `MapGlbExporter.cs`의 `Compression.Draco` → `Compression.None`으로 바꿔 재시도 (파일 커지지만 확실).
- **glb가 너무 큼(>100MB)**: 건물 LOD만 남기거나, 지형(`BG_Escape_Terrain`)만 먼저 export해서 테스트.
- **텍스처 누락**: 프리팹의 머티리얼이 커스텀 셰이더면 glTF가 못 담을 수 있음 → 알려주면 뷰어에서 단색/베이스맵으로 대체.
