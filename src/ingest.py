"""Copy footage from SD cards to SSD (editing) and HDD (backup)."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from .project_paths import project_root, video_dir, video_folder_name
from .sd_compare import CompareResult, compare_sd_cards_from_config
from .utils import format_bytes, normalize_path, sha256_file

console = Console()


def _dest_paths(cfg: dict, shoot_date: str | None = None) -> tuple[Path, Path]:
    """SSD/HDD ingest targets: project folder / Video / (camera paths)."""
    date_fmt = cfg["ingest"].get("date_folder_format", "%Y-%m-%d")
    folder = shoot_date or datetime.now().strftime(date_fmt)
    return video_dir(cfg, folder, destination="ssd"), video_dir(cfg, folder, destination="hdd")


def _copy_file(
    src: Path,
    dest: Path,
    verify: bool,
    dry_run: bool,
) -> tuple[bool, str]:
    """Copy one file. Returns (copied, message). Skips if dest exists and matches."""
    if dest.exists():
        if dest.stat().st_size == src.stat().st_size:
            if not verify:
                return False, "skipped (exists)"
            if sha256_file(src) == sha256_file(dest):
                return False, "skipped (verified)"
        elif dest.stat().st_size > src.stat().st_size:
            return False, "skipped (dest larger)"

    if dry_run:
        return True, "would copy"

    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)

    if verify:
        if sha256_file(src) != sha256_file(dest):
            dest.unlink(missing_ok=True)
            return False, "FAILED checksum"
    return True, "copied"


def ingest_footage(
    cfg: dict,
    compare: CompareResult | None = None,
    shoot_date: str | None = None,
    dry_run: bool = False,
) -> dict:
    """
    Copy all footage from SD card(s) into project/Video/ on SSD and HDD.
    Uses compare result to gather files from both cards when they differ.
    """
    extensions = cfg.get("footage_extensions", [".mp4", ".mov"])
    verify = cfg.get("ingest", {}).get("verify_checksum", True)

    if compare is None:
        compare = compare_sd_cards_from_config(cfg, extensions)

    files = compare.all_unique_files
    ssd_root, hdd_root = _dest_paths(cfg, shoot_date)
    video_name = video_folder_name(cfg)

    stats = {"copied_ssd": 0, "copied_hdd": 0, "skipped": 0, "failed": 0, "bytes": 0}

    console.print(f"\n[bold]Ingesting {len(files)} files into {video_name}/[/bold]")
    console.print(f"  SSD: {ssd_root}")
    console.print(f"  HDD: {hdd_root}\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Copying...", total=len(files))

        for rel, src in sorted(files.items()):
            progress.update(task, description=rel[:60])

            for label, root, key in [
                ("SSD", ssd_root, "copied_ssd"),
                ("HDD", hdd_root, "copied_hdd"),
            ]:
                dest = root / rel.replace("/", "\\")
                ok, msg = _copy_file(src, dest, verify, dry_run)
                if ok:
                    stats[key] += 1
                    if label == "SSD":
                        stats["bytes"] += src.stat().st_size
                elif msg.startswith("skipped"):
                    stats["skipped"] += 1
                elif msg.startswith("FAILED"):
                    stats["failed"] += 1
                    console.print(f"[red]{label} {rel}: {msg}[/red]")

            progress.advance(task)

    console.print(f"\n[green]Ingest complete.[/green]")
    console.print(f"  SSD copies: {stats['copied_ssd']}")
    console.print(f"  HDD copies: {stats['copied_hdd']}")
    console.print(f"  Skipped:    {stats['skipped']}")
    if stats["failed"]:
        console.print(f"  [red]Failed:     {stats['failed']}[/red]")
    console.print(f"  Data moved: {format_bytes(stats['bytes'])}")

    stats["ssd_path"] = str(ssd_root.parent)
    stats["video_path"] = str(ssd_root)
    stats["hdd_path"] = str(hdd_root.parent)
    return stats
