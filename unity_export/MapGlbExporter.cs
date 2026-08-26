// ER 맵 → GLB 익스포터 (Unity 6000.3.20f1 + glTFast)
// 설치: Window > Package Manager > + > Add package by name > com.unity.cloud.gltfast
// 사용: 이 파일을 AssetRipper 프로젝트의 Assets/Editor/ 에 넣고,
//       맵 프리팹을 Hierarchy에 드래그 → 선택 → 메뉴 Tools > Export Selected → GLB
// 결과: <프로젝트루트>/MapExport/<이름>.glb  (Draco 압축 켜짐 = 웹 로드 가벼움)

#if UNITY_EDITOR
using UnityEngine;
using UnityEditor;
using GLTFast.Export;
using System.IO;
using System.Threading.Tasks;

public static class MapGlbExporter
{
    [MenuItem("Tools/Export Selected → GLB")]
    static async void ExportSelected()
    {
        var go = Selection.activeGameObject;
        if (go == null) { EditorUtility.DisplayDialog("Export", "Hierarchy에서 맵 프리팹을 선택하세요", "OK"); return; }

        var dir = Path.Combine(Directory.GetCurrentDirectory(), "MapExport");
        Directory.CreateDirectory(dir);
        var path = Path.Combine(dir, go.name + ".glb");

        // Draco 압축 + 바이너리(glb). 텍스처 포함.
        var settings = new ExportSettings {
            Format = GltfFormat.Binary,
            FileConflictResolution = FileConflictResolution.Overwrite,
            Compression = Compression.Draco,   // 메시 압축(웹 경량화). 문제 시 Compression.None 으로.
        };
        var goSettings = new GameObjectExportSettings {
            OnlyActiveInHierarchy = false,     // 비활성 자식도 포함
            DisabledComponents = false,
        };

        var export = new GameObjectExport(settings, goSettings);
        export.AddScene(new[] { go }, go.name);
        bool ok = await export.SaveToFileAndDispose(path);

        if (ok) { Debug.Log($"✅ GLB Export 완료: {path}"); EditorUtility.RevealInFinder(path); }
        else    { Debug.LogError("❌ GLB Export 실패 — Console 확인. Compression.None 으로 재시도해보세요."); }
    }
}
#endif
