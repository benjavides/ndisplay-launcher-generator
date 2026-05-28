from __future__ import annotations

from pathlib import Path


def discover_project_maps(uproject_path: Path) -> list[str]:
    project_root = uproject_path.parent
    content_root = project_root / "Content"
    if not content_root.exists():
        return []

    maps: list[str] = []
    for umap in content_root.rglob("*.umap"):
        rel = umap.relative_to(content_root).with_suffix("")
        unreal_map = "/Game/" + str(rel).replace("\\", "/")
        maps.append(unreal_map)

    maps.sort()
    return maps

