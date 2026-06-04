"""Mirror primary hard drive backup to secondary hard drive."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from rich.console import Console

from .utils import normalize_path

console = Console()


def mirror_backup(cfg: dict, dry_run: bool = False) -> dict:
    """
    Mirror the entire HDD backup folder to the second hard drive.
    Uses robocopy on Windows for efficient mirroring; falls back to shutil.
    """
    source = normalize_path(cfg["destinations"]["hdd_backup"])
    dest = normalize_path(cfg["destinations"]["hdd_backup_mirror"])

    if not source.exists():
        raise FileNotFoundError(f"Primary HDD backup not found: {source}")

    console.print("\n[bold]Mirroring HDD backup[/bold]")
    console.print(f"  Source: {source}")
    console.print(f"  Dest:   {dest}\n")

    if dry_run:
        console.print("[yellow]Dry run — would mirror all files.[/yellow]")
        return {"dry_run": True}

    dest.mkdir(parents=True, exist_ok=True)

    # robocopy: /MIR mirror, /MT multithreaded, /R:1 /W:1 quick retries
    robocopy = shutil.which("robocopy")
    if robocopy:
        cmd = [
            robocopy,
            str(source),
            str(dest),
            "/MIR",
            "/MT:8",
            "/R:2",
            "/W:3",
            "/NP",
            "/NDL",
            "/NFL",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        # robocopy exit codes 0-7 are success/partial success
        if result.returncode >= 8:
            console.print(f"[red]Robocopy failed (code {result.returncode})[/red]")
            if result.stdout:
                console.print(result.stdout[-2000:])
            return {"success": False, "exit_code": result.returncode}

        console.print("[green]Mirror complete (robocopy).[/green]")
        return {"success": True, "method": "robocopy"}
    else:
        console.print("[yellow]robocopy not found, using Python copy (slower).[/yellow]")
        _mirror_python(source, dest)
        console.print("[green]Mirror complete.[/green]")
        return {"success": True, "method": "python"}


def _mirror_python(source: Path, dest: Path) -> None:
    """Simple recursive mirror without deleting extra files on dest."""
    for src_path in source.rglob("*"):
        if src_path.is_file():
            rel = src_path.relative_to(source)
            dst_path = dest / rel
            if not dst_path.exists() or dst_path.stat().st_size != src_path.stat().st_size:
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dst_path)
