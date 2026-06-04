"""Standard project folder layout on SSD / HDD."""

from __future__ import annotations

from pathlib import Path

from .utils import normalize_path


def video_folder_name(cfg: dict) -> str:
    return cfg.get("project", {}).get("video_folder", "Video")


def proxies_folder_name(cfg: dict) -> str:
    return cfg.get("proxies", {}).get("subfolder", "Proxies")


def project_root(cfg: dict, folder_name: str) -> tuple[Path, Path]:
    """SSD and HDD roots for a project, e.g. F:\\[003] Title\\."""
    ssd = normalize_path(cfg["destinations"]["ssd_editing"]) / folder_name
    hdd = normalize_path(cfg["destinations"]["hdd_backup"]) / folder_name
    return ssd, hdd


def video_dir(cfg: dict, folder_name: str, *, destination: str = "ssd") -> Path:
    """Footage + Premiere proxies live under Video\\ on the SSD (and mirror on HDD)."""
    ssd, hdd = project_root(cfg, folder_name)
    root = ssd if destination == "ssd" else hdd
    return root / video_folder_name(cfg)


def proxies_dir(cfg: dict, project_folder: str | Path) -> Path | None:
    """
    Find Proxies folder for Google Drive upload.
    Premiere (next to original media) creates: Project/Video/Proxies/
    """
    root = normalize_path(project_folder)
    video = video_folder_name(cfg)
    proxy_name = proxies_folder_name(cfg)
    for candidate in (root / video / proxy_name, root / proxy_name):
        if candidate.is_dir():
            return candidate
    return None


def find_prproj(cfg: dict, project_folder: str | Path) -> Path | None:
    root = normalize_path(project_folder)
    exts = cfg.get("project_extensions", [".prproj"])
    candidates = sorted(root.glob(f"*{exts[0]}"))
    if candidates:
        return candidates[0]
    # Match folder name, e.g. [003] Title.prproj
    named = root / f"{root.name}.prproj"
    if named.exists():
        return named
    return None
