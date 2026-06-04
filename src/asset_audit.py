"""Audit project assets against hard drive backup."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.table import Table

from .utils import format_bytes, iter_files, normalize_path, scan_directory

console = Console()


def audit_assets(
    project_folder: str | Path,
    hdd_folder: str | Path,
    cfg: dict,
    copy_missing: bool = False,
    dry_run: bool = False,
) -> dict:
    """
    Compare all files in the project folder (assets, exports, extras)
    against the HDD backup. Reports and optionally copies missing files.
    """
    project_root = normalize_path(project_folder)
    hdd_root = normalize_path(hdd_folder)

    if not project_root.exists():
        raise FileNotFoundError(f"Project folder not found: {project_root}")

    # Scan everything in project folder (not just footage extensions)
    project_files = scan_directory(project_root, extensions=None)
    hdd_files = scan_directory(hdd_root, extensions=None) if hdd_root.exists() else {}

    missing_on_hdd: list[str] = []
    size_mismatch: list[tuple[str, int, int]] = []

    for rel, info in sorted(project_files.items()):
        hdd_info = hdd_files.get(rel)
        if not hdd_info:
            missing_on_hdd.append(rel)
        elif hdd_info.size != info.size:
            size_mismatch.append((rel, info.size, hdd_info.size))

    # Also flag common asset locations
    asset_dirs = ["Assets", "assets", "SFX", "Music", "Exports", "exports"]
    found_asset_dirs = [d for d in asset_dirs if (project_root / d).exists()]

    console.print("\n[bold]Asset Audit Report[/bold]\n")
    console.print(f"  Project: {project_root}")
    console.print(f"  HDD:     {hdd_root}\n")

    table = Table(show_header=True, header_style="bold")
    table.add_column("Metric")
    table.add_column("Count", justify="right")
    table.add_row("Files in project", str(len(project_files)))
    table.add_row("Missing on HDD", str(len(missing_on_hdd)), style="red" if missing_on_hdd else "")
    table.add_row("Size mismatches", str(len(size_mismatch)), style="yellow" if size_mismatch else "")
    console.print(table)

    if found_asset_dirs:
        console.print(f"\nAsset folders detected: {', '.join(found_asset_dirs)}")

    if missing_on_hdd:
        console.print("\n[red]Files on project SSD but NOT on HDD:[/red]")
        total_missing = 0
        for rel in missing_on_hdd[:30]:
            size = project_files[rel].size
            total_missing += size
            console.print(f"  - {rel} ({format_bytes(size)})")
        if len(missing_on_hdd) > 30:
            console.print(f"  ... and {len(missing_on_hdd) - 30} more")
        console.print(f"  Total missing: {format_bytes(total_missing)}")

    if size_mismatch:
        console.print("\n[yellow]Size mismatches:[/yellow]")
        for rel, ps, hs in size_mismatch[:10]:
            console.print(f"  ! {rel}  project={format_bytes(ps)}  hdd={format_bytes(hs)}")

    copied = 0
    if copy_missing and missing_on_hdd:
        import shutil

        console.print("\n[bold]Copying missing files to HDD...[/bold]")
        for rel in missing_on_hdd:
            src = project_root / rel.replace("/", "\\")
            dest = hdd_root / rel.replace("/", "\\")
            if dry_run:
                console.print(f"  would copy: {rel}")
                copied += 1
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            copied += 1
        console.print(f"[green]Copied {copied} files to HDD.[/green]")

    if not missing_on_hdd and not size_mismatch:
        console.print("\n[green]All project files are backed up on the HDD.[/green]")

    return {
        "missing": missing_on_hdd,
        "size_mismatch": size_mismatch,
        "copied": copied,
        "in_sync": not missing_on_hdd and not size_mismatch,
    }
