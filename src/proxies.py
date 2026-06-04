"""Generate low-resolution proxy files with FFmpeg."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from .project_paths import video_folder_name
from .utils import format_bytes, iter_files, normalize_path

console = Console()


def _find_ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise RuntimeError(
            "FFmpeg not found. Install from https://ffmpeg.org/download.html "
            "and add it to your PATH."
        )
    return path


def _proxy_path(source: Path, footage_root: Path, proxy_subfolder: str) -> Path:
    rel = source.relative_to(footage_root)
    return footage_root / proxy_subfolder / rel.with_suffix(".mp4")


def create_proxies(
    footage_folder: str | Path,
    cfg: dict,
    dry_run: bool = False,
) -> dict:
    """
    Create H.264 proxy MP4s in a Proxies subfolder mirroring the source tree.
    Skips files that already have a newer proxy.
    """
    proxy_cfg = cfg.get("proxies", {})
    if not proxy_cfg.get("enabled", True):
        console.print("[yellow]Proxies disabled in config.[/yellow]")
        return {"created": 0, "skipped": 0}

    footage_root = normalize_path(footage_folder)
    if not footage_root.exists():
        raise FileNotFoundError(f"Footage folder not found: {footage_root}")

    video_path = footage_root / video_folder_name(cfg)
    scan_root = video_path if video_path.is_dir() else footage_root

    extensions = cfg.get("footage_extensions", [".mp4", ".mov"])
    subfolder = proxy_cfg.get("subfolder", "Proxies")
    width = int(proxy_cfg.get("width", 1280))
    crf = int(proxy_cfg.get("crf", 23))
    preset = proxy_cfg.get("preset", "fast")

    sources = [
        p
        for p in iter_files(scan_root, extensions)
        if subfolder not in p.parts
    ]

    ffmpeg = _find_ffmpeg()
    stats = {"created": 0, "skipped": 0, "failed": 0, "bytes": 0}

    console.print(f"\n[bold]Creating proxies for {len(sources)} files[/bold]")
    console.print(f"  Source: {scan_root}")
    console.print(f"  Output: {scan_root / subfolder}\n")

    vf = f"scale='min({width},iw)':-2"

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Proxies...", total=len(sources))

        for src in sources:
            progress.update(task, description=src.name[:50])
            dest = _proxy_path(src, scan_root, subfolder)

            if dest.exists() and dest.stat().st_mtime >= src.stat().st_mtime:
                stats["skipped"] += 1
                progress.advance(task)
                continue

            if dry_run:
                stats["created"] += 1
                progress.advance(task)
                continue

            dest.parent.mkdir(parents=True, exist_ok=True)
            cmd = [
                ffmpeg,
                "-y",
                "-i",
                str(src),
                "-vf",
                vf,
                "-c:v",
                "libx264",
                "-preset",
                preset,
                "-crf",
                str(crf),
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-movflags",
                "+faststart",
                str(dest),
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                stats["failed"] += 1
                console.print(f"[red]Failed: {src.name}[/red]")
                dest.unlink(missing_ok=True)
            else:
                stats["created"] += 1
                stats["bytes"] += dest.stat().st_size

            progress.advance(task)

    console.print(f"\n[green]Proxy generation complete.[/green]")
    console.print(f"  Created: {stats['created']}")
    console.print(f"  Skipped: {stats['skipped']}")
    if stats["failed"]:
        console.print(f"  [red]Failed:  {stats['failed']}[/red]")
    console.print(f"  Proxy size: {format_bytes(stats['bytes'])}")

    console.print(
        "\n[dim]In Premiere: Import originals from the SSD folder, then "
        "Right-click clip > Proxy > Attach Proxies > attach from the Proxies subfolder. "
        "Or use Ingest settings to auto-attach on import.[/dim]"
    )

    stats["proxy_folder"] = str(scan_root / subfolder)
    return stats
