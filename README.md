# secret_replay — Eternal Return `.er` 리플레이 포맷 리버싱

이터널 리턴(Eternal Return) 공식 리플레이 파일 `.er`의 바이너리 포맷을 리버스 엔지니어링하고 디코더를 구현한 작업물.

> **정적 분석만** 사용. 게임 프로세스 메모리 덤프·안티치트 우회 없음. 리플레이 데이터 읽기 용도

## 핵심 결론

`.er` 레코드 payload = **Brotli 압축 → MemoryPack 직렬화**

- 이전엔 "커스텀 비트팩·해독 불가"로 오판됐음 — 실제로는 **Brotli(magic 바이트 없어 압축 감지 우회됨) + MemoryPack(Cysharp 오픈소스)** 조합.
- IL2CppDumper 출력(`CharacterStatusSnapshot : IMemoryPackable`, `[MemoryPackOrder]`)으로 정체 판명.
- 압축 해제하면 `gameId`·좌표·HP가 그대로 읽힘.

## 파일 구조

| 폴더 | 내용 |
|---|---|
| `docs/er-replay-format.md` | **완전 포맷 레퍼런스** — 파일 레이아웃, 레코드 프레이밍, Brotli, MemoryPack 와이어 포맷, 컨테이너 계층, 엔티티 레이아웃, 좌표 변환, 바이트 예제 |
| `decoder/er_decode.py` | 메인 디코더 (프레이밍 → Brotli → MemoryPack → 엔티티 위치/HP/스탯) |
| `decoder/` | MemoryPack 파서·스키마 추출·좌표 추출 스크립트 |
| `schema/schema.json` | dump.cs에서 추출한 976개 MemoryPackable 클래스 스키마 |
| `schema/mempack_meta.json` | union 태그맵 + 필드 오프셋 (경험적 확정분) |
| `data/er_dense_traj.json` | 24명 궤적 (그리드좌표, HP) |
| `viewers/*.html` | 자립형 시각화 (미니맵 재생 / 원본-해석 대조 / 독립검증 나란히보기) |
| `research/` | 리버싱 과정 스크립트 + 발견 노트 |

## 검증 상태

| 항목 | 상태 |
|---|---|
| 포맷 (Brotli+MemoryPack) | ✅ 확정 |
| 컨테이너 (ReplaySnapshot→GameSnapshot→userList) | ✅ gameId/seq/24명 일치 |
| **위치** | ✅ 1608 샘플, 오차 중앙 **0.43 그리드** (dakgg 대조) |
| **HP** | ✅ 24/24 정확 |
| SP·레벨·실드·이동속도 | ✅ 추출됨 |
| string 인코딩 | ✅ `[~utf8len][utf16len][utf8]` |
| union (SnapshotWrapper) | ✅ 경험적 (0x07=Full/0x04=Basic, objectType 판별) |
| 델타 패킷 구조 | ◑ 프레이밍 해독(`[0x05][tick][count][records]`, fieldTag 0x02=위치), 클린 워크 미완 |
| 깊은 플레이어 필드 (characterCode·스킬·버프) | ⛔ 권위 `[MemoryPackOrder]` 추출 블로커 (아래) |
| 투사체 조준좌표 / 글로벌 상태 | ⛔ 동일 블로커 |

## 남은 블로커

깊은 중첩 필드·클린 델타 워크·투사체·글로벌 상태는 **권위있는 `[MemoryPackOrder]`/union `typeof` 맵**이 필요.
- pure-python `dnfile`로 24MB 어셈블리의 484,704개 CustomAttribute를 예산 내 다 해석 못 함.
- **해결경로**: 더 빠른 .NET 메타데이터 리더(ILSpy/monodis/ildasm) 또는 `#~`/`#Blob` 테이블 raw 파싱(대상 ~50 타입만, ctor 토큰 정수필터) → 필드순서 확보 → `er_decode.py`에 주입.

## 좌표계

월드좌표(Vector2Int/float) → dakgg 미니맵 그리드 (아이소메트릭 아핀):
```
gridX = -1.645*(x + z) + 290.1
gridY = -1.653*x + 1.652*z + 555.0
```

## 리플레이 취득

- **dakgg** (무인증): `er.dakgg.io/api/v1/rpc/replay?gameId=X` → `.bin` (AES-128-CBC 키=IV=0) — 닥지지 재가공 포맷
- **공식 `.er`** (세션 인증): `ReplayApi.FindReplayGame` → `bser-rest-release.bser.io/api/external/findReplayGame/{gameId}/{userNum}` — 게임사 비공개 API (ToS 주의)
