"""Copy finished proxies from SSD (Soju) to matching HDD backup folder."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from .ingest import _copy_file
from .premiere_proxy import proxy_subfolder_name
from .project_paths import project_root, proxies_dir, video_folder_name
from .utils import format_bytes

console = Console()


def _hdd_proxies_path(cfg: dict, hdd_project: Path) -> Path:
    """Mirror SSD layout: project/Video/Proxies/."""
    video = video_folder_name(cfg)
    proxy_name = proxy_subfolder_name(cfg)
    found = proxies_dir(cfg, hdd_project)
    return found if found else hdd_project / video / proxy_name


def backup_proxies_to_hdd(
    cfg: dict,
    folder_name: str,
    *,
    dry_run: bool = False,
) -> dict:
    """
    Copy all files under SSD Video/Proxies/ to the same path on hdd_backup.

    Skips files that already match on HDD (size + optional checksum from ingest).
    """
    verify = cfg.get("ingest", {}).get("verify_checksum", True)
    ssd_root, hdd_root = project_root(cfg, folder_name)
    ssd_proxy = proxies_dir(cfg, ssd_root)
    hdd_proxy = _hdd_proxies_path(cfg, hdd_root)

    stats = {
        "copied": 0,
        "skipped": 0,
        "failed": 0,
        "bytes": 0,
        "ssd_proxies": str(ssd_proxy) if ssd_proxy else "",
        "hdd_proxies": str(hdd_proxy),
    }

    if not ssd_proxy or not ssd_proxy.is_dir():
        console.print("[yellow]No proxies on SSD to back up.[/yellow]")
        stats["skipped_reason"] = "no_ssd_proxies"
        return stats

    sources = sorted(
        (p for p in ssd_proxy.rglob("*") if p.is_file()),
        key=lambda p: str(p).lower(),
    )
    if not sources:
        console.print("[yellow]Proxies folder exists but has no files yet.[/yellow]")
        stats["skipped_reason"] = "empty"
        return stats

    console.print("\n[bold]Backing up proxies SSD → HDD[/bold]")
    console.print(f"  From: {ssd_proxy}")
    console.print(f"  To:   {hdd_proxy}\n")

    if dry_run:
        console.print(f"[yellow]Dry run — would copy {len(sources)} file(s).[/yellow]")
        stats["would_copy"] = len(sources)
        return stats

    hdd_proxy.mkdir(parents=True, exist_ok=True)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Proxies → HDD...", total=len(sources))
        for src in sources:
            rel = src.relative_to(ssd_proxy)
            dest = hdd_proxy / rel
            progress.update(task, description=str(rel)[:50])
            ok, msg = _copy_file(src, dest, verify, dry_run=False)
            if ok:
                stats["copied"] += 1
                stats["bytes"] += src.stat().st_size
            elif msg.startswith("skipped"):
                stats["skipped"] += 1
            else:
                stats["failed"] += 1
                console.print(f"[red]{rel}: {msg}[/red]")
            progress.advance(task)

    console.print(f"\n[green]Proxy backup complete.[/green]")
    console.print(f"  Copied:  {stats['copied']}")
    console.print(f"  Skipped: {stats['skipped']} (already on HDD)")
    if stats["failed"]:
        console.print(f"  [red]Failed:  {stats['failed']}[/red]")
    console.print(f"  Data:    {format_bytes(stats['bytes'])}")

    return stats
