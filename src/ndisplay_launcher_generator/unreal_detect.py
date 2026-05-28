from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True)
class UnrealInstall:
    version_label: str
    editor_path: Path


def _version_from_folder(folder_name: str) -> str:
    match = re.match(r"UE_(.+)", folder_name, flags=re.IGNORECASE)
    return match.group(1) if match else folder_name


def detect_unreal_installs() -> list[UnrealInstall]:
    roots = [
        Path(r"C:\Program Files\Epic Games"),
        Path(r"C:\Program Files (x86)\Epic Games"),
    ]
    installs: list[UnrealInstall] = []

    for root in roots:
        if not root.exists():
            continue
        for candidate in root.glob("UE_*"):
            editor_path = candidate / "Engine" / "Binaries" / "Win64" / "UnrealEditor.exe"
            if editor_path.exists():
                version = _version_from_folder(candidate.name)
                installs.append(UnrealInstall(version_label=f"UE {version}", editor_path=editor_path))

    installs.sort(key=lambda x: x.version_label, reverse=True)
    return installs

