"""Launch Adobe Premiere Pro and run automate_premiere.jsx without manual steps."""

from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from rich.console import Console

console = Console()

EXTENDSCRIPT_FLAG = "extendscriptprqe.txt"
HELPER_SCRIPT_NAME = "Run Automated Workflow.jsx"
HELPER_SOURCE = Path(__file__).resolve().parent.parent / "templates" / "premiere_run_queued.jsx"


def automated_script_state_dir() -> Path:
    """LocalAppData — matches ExtendScript Folder.appData on Windows."""
    state = Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir())) / "Automated-script"
    state.mkdir(parents=True, exist_ok=True)
    return state


def find_premiere_exe(cfg: dict) -> Path | None:
    premiere_cfg = cfg.get("premiere", {})
    if premiere_cfg.get("exe_path"):
        path = Path(premiere_cfg["exe_path"])
        if path.exists():
            return path

    patterns = [
        r"C:\Program Files\Adobe\Adobe Premiere Pro *\Adobe Premiere Pro.exe",
    ]
    matches: list[str] = []
    for pattern in patterns:
        matches.extend(glob.glob(pattern))
    if not matches:
        return None
    return Path(sorted(matches)[-1])


def find_premiere_scripts_folder() -> Path | None:
    """Documents/Adobe/Premiere Pro/<version>/Scripts (newest version first)."""
    root = Path.home() / "Documents" / "Adobe" / "Premiere Pro"
    if not root.is_dir():
        return None
    version_dirs = sorted(
        (p for p in root.iterdir() if p.is_dir()),
        key=lambda p: p.name,
        reverse=True,
    )
    for version_dir in version_dirs:
        scripts = version_dir / "Scripts"
        scripts.mkdir(parents=True, exist_ok=True)
        return scripts
    return None


def is_media_encoder_running() -> bool:
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq Adobe Media Encoder.exe"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return "Adobe Media Encoder.exe" in (result.stdout or "")
    except (OSError, subprocess.SubprocessError):
        return False


def is_premiere_running() -> bool:
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq Adobe Premiere Pro.exe"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return "Adobe Premiere Pro.exe" in (result.stdout or "")
    except (OSError, subprocess.SubprocessError):
        return False


def _try_elevated_create_flag(flag: Path) -> bool:
    """Prompt Windows UAC to create extendscriptprqe.txt in Program Files."""
    if flag.exists():
        return True

    script_body = f'New-Item -LiteralPath "{flag}" -ItemType File -Force'
    script_path = Path(tempfile.gettempdir()) / "create_extendscriptprqe.ps1"
    try:
        script_path.write_text(script_body, encoding="utf-8")
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                (
                    "Start-Process -FilePath powershell.exe -Verb RunAs -Wait "
                    f"-ArgumentList '-ExecutionPolicy','Bypass','-File','{script_path}'"
                ),
            ],
            check=False,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    finally:
        script_path.unlink(missing_ok=True)

    return flag.exists()


def ensure_extendscript_flag(premiere_exe: Path) -> tuple[bool, Path]:
    """
    Adobe requires an empty extendscriptprqe.txt beside Premiere.exe
    for: Premiere.exe /C es.processFile script.jsx
    """
    flag = premiere_exe.parent / EXTENDSCRIPT_FLAG
    if flag.exists():
        return True, flag
    try:
        flag.touch()
        console.print(f"[green]Created[/green] {flag}")
        return True, flag
    except OSError:
        return False, flag


def ensure_premiere_scripts_helper() -> Path | None:
    """
    Copy queue runner into Premiere's Scripts folder (File → Scripts menu).
    Used when Premiere is already open — CLI /C cannot target a live session.
    """
    if not HELPER_SOURCE.is_file():
        console.print(f"[yellow]Missing helper template:[/yellow] {HELPER_SOURCE}")
        return None

    scripts_dir = find_premiere_scripts_folder()
    if not scripts_dir:
        console.print(
            "[yellow]Premiere Scripts folder not found.[/yellow] "
            "Open Premiere once so Documents/Adobe/Premiere Pro/... is created."
        )
        return None

    dest = scripts_dir / HELPER_SCRIPT_NAME
    try:
        shutil.copy2(HELPER_SOURCE, dest)
    except OSError as exc:
        console.print(f"[yellow]Could not install Scripts helper:[/yellow] {exc}")
        return None
    return dest


def write_script_queue(jsx_path: Path) -> Path:
    """Queue automate_premiere.jsx for the Scripts-menu runner (Premiere already open)."""
    queue = automated_script_state_dir() / "queue.txt"
    queue.write_text(_jsx_path_for_extendscript(jsx_path) + "\n", encoding="utf-8")
    return queue


def install_premiere_cli_scripting(cfg: dict) -> bool:
    """One-time setup so Premiere runs JSX on launch (may need Administrator)."""
    premiere = find_premiere_exe(cfg)
    if not premiere:
        console.print(
            "[red]Premiere not found.[/red] Set premiere.exe_path in config.yaml "
            "to your Adobe Premiere Pro.exe path."
        )
        return False

    console.print(f"Premiere: {premiere}")
    ok, flag = ensure_extendscript_flag(premiere)
    if not ok:
        console.print(
            "[yellow]Need Administrator for Program Files.[/yellow] "
            "Approve the UAC prompt if one appears..."
        )
        ok = _try_elevated_create_flag(flag)
        if ok:
            console.print(f"[green]Created[/green] {flag}")

    helper = ensure_premiere_scripts_helper()
    if helper:
        console.print(f"[green]Scripts helper installed:[/green] {helper.name}")

    if ok:
        console.print(
            "\n[green]Premiere automation is ready.[/green]\n"
            "  Cold start: python main.py workflow --number 003\n"
            "  Premiere already open: workflow queues the script — then in Premiere:\n"
            f"    File → Scripts → {HELPER_SCRIPT_NAME}\n"
        )
        return True

    console.print(
        f"\n[red]Could not create[/red] {flag}\n\n"
        "  [bold]Option A — Administrator PowerShell[/bold] (window title must say Administrator):\n"
        f'  New-Item -LiteralPath "{flag}" -ItemType File -Force\n\n'
        "  [bold]Option B — Notepad as Administrator[/bold]\n"
        "  1. Start menu → Notepad → right-click → Run as administrator\n"
        "  2. File → Save As → paste this path in the filename box:\n"
        f"     {flag}\n"
        "  3. Save empty file (choose All Files if needed)\n\n"
        "  [bold]Option C — Scripts menu[/bold] (no admin): After workflow with Premiere open:\n"
        f"  File → Scripts → {HELPER_SCRIPT_NAME}\n"
    )
    return helper is not None


def _jsx_path_for_extendscript(path: Path) -> str:
    """ExtendScript File() paths work best with forward slashes."""
    return path.resolve().as_posix()


def _write_launch_wrapper(jsx_path: Path) -> Path:
    """Stable wrapper path (no [brackets]) for Premiere CLI es.processFile."""
    target_lit = json.dumps(_jsx_path_for_extendscript(jsx_path))
    content = f"""(function () {{
    var f = new File({target_lit});
    if (!f.exists) {{
        alert("Automation script not found:\\n" + f.fsName);
        return;
    }}
    $.evalFile(f);
}})();
"""
    wrapper = automated_script_state_dir() / "premiere_cli_wrapper.jsx"
    wrapper.write_text(content, encoding="utf-8")
    return wrapper


def _extendscript_cli_command(script_path: Path) -> str:
    """Single /C argument Adobe expects: es.processFile("C:/path/script.jsx")."""
    return f'es.processFile("{_jsx_path_for_extendscript(script_path)}")'


def write_launch_batch(
    project_folder: Path,
    premiere_exe: Path,
    jsx_path: Path,
) -> Path:
    """Batch file Ethan can double-click if Python launch does not run the script."""
    bat = project_folder / "OPEN_PREMIERE_AUTOMATION.bat"
    prem = str(premiere_exe.resolve())
    wrapper = _write_launch_wrapper(jsx_path)
    cli = _extendscript_cli_command(wrapper)
    bat.write_text(
        "@echo off\n"
        "echo Starting Premiere with automation...\n"
        f'start "" "{prem}" /C {cli}\n'
        "echo.\n"
        "echo If Premiere was already open, use instead:\n"
        f"echo   File - Scripts - {HELPER_SCRIPT_NAME}\n"
        "echo.\n"
        "echo If nothing happens, run once as Administrator:\n"
        "echo   python main.py install-premiere\n"
        "pause\n",
        encoding="utf-8",
    )
    return bat


def _try_launch(premiere: Path, script_path: Path, cwd: Path) -> bool:
    """Launch Premiere cold and run ExtendScript (Premiere must not already be open)."""
    command = _extendscript_cli_command(script_path)
    attempts = (
        [str(premiere), "/C", command],
        [str(premiere), f"/C {command}"],
    )
    for args in attempts:
        try:
            subprocess.Popen(args, shell=False, cwd=str(cwd))
            return True
        except OSError:
            continue
    return False


def _queue_for_open_premiere(jsx_path: Path) -> bool:
    """Premiere is live — queue script and use File → Scripts (CLI cannot attach)."""
    write_script_queue(jsx_path)
    helper = ensure_premiere_scripts_helper()
    console.print(
        "\n[bold yellow]Premiere is already open[/bold yellow] — one quick step in Premiere:\n"
        f"  [bold]File → Scripts → {HELPER_SCRIPT_NAME}[/bold]\n"
        "  (Adobe cannot run CLI scripts into an open session — this avoids the "
        "'file path does not exist' error.)\n"
    )
    if helper:
        console.print(f"  Helper: {helper}\n")
    else:
        console.print(
            f"  Or: File → Scripts → Run Script File → {jsx_path.name}\n"
        )
    return True


def launch_premiere_automation(
    cfg: dict,
    *,
    jsx_path: Path,
    prproj_path: Path,
    project_folder: Path,
) -> bool:
    """
    Run automate_premiere.jsx.

    - Premiere closed: launch with /C es.processFile (automatic).
    - Premiere open: queue script + run File → Scripts → Run Automated Workflow.
    """
    premiere_cfg = cfg.get("premiere", {})
    if premiere_cfg.get("auto_run_script") is False:
        return _launch_premiere_project_only(cfg, prproj_path, project_folder)

    premiere = find_premiere_exe(cfg)
    if not premiere:
        console.print(
            "[yellow]Adobe Premiere Pro not found.[/yellow] "
            "Set premiere.exe_path in config.yaml."
        )
        os.startfile(project_folder)  # noqa: S606
        return False

    if not jsx_path.is_file():
        console.print(f"[red]Automation script missing:[/red] {jsx_path}")
        return False

    premiere_open = is_premiere_running()
    ame_open = is_media_encoder_running()

    flag_ok, flag_path = ensure_extendscript_flag(premiere)
    if not flag_ok:
        console.print(
            f"\n[yellow]Missing {EXTENDSCRIPT_FLAG}[/yellow] next to Premiere.exe.\n"
            "  Run [bold]python main.py install-premiere[/bold] "
            "(PowerShell as Administrator if it fails).\n"
        )

    wrapper = _write_launch_wrapper(jsx_path)
    bat_path = write_launch_batch(project_folder, premiere, jsx_path)

    console.print(f"  Project folder: {project_folder}")
    console.print(f"  Script:         {jsx_path.name}")
    if flag_ok:
        console.print(f"  CLI scripting:  enabled ({flag_path.name})")
    console.print(f"  Manual fallback: {bat_path.name}\n")

    if ame_open:
        console.print("[dim]Media Encoder is open — proxy jobs will queue there.[/dim]")

    if premiere_open:
        return _queue_for_open_premiere(jsx_path)

    console.print("\n[bold]Launching Premiere with automation...[/bold]")
    launched = _try_launch(premiere, wrapper, project_folder)

    if not launched:
        console.print(
            "[yellow]Could not launch Premiere with automation.[/yellow]\n"
            f"  File → Scripts → Run Script File → {jsx_path.name}\n"
        )
        return False

    if not flag_ok:
        console.print(
            "[yellow]If Premiere opens but does not create the project:[/yellow]\n"
            "  1. python main.py install-premiere   (as Administrator)\n"
            f"  2. Double-click: {bat_path}\n"
            "  3. Or in Premiere: File → Scripts → Run Script File → automate_premiere.jsx\n"
        )

    return launched


def _launch_premiere_project_only(
    cfg: dict,
    prproj_path: Path,
    project_folder: Path,
) -> bool:
    """Open an existing .prproj (no automatic JSX)."""
    premiere = find_premiere_exe(cfg)
    if not premiere:
        os.startfile(project_folder)  # noqa: S606
        return False

    if prproj_path.is_file():
        console.print(f"Opening Premiere: {prproj_path.name}")
        subprocess.Popen([str(premiere), str(prproj_path.resolve())], shell=False)
    else:
        console.print("Opening Premiere — run automate_premiere.jsx from File > Scripts")
        subprocess.Popen([str(premiere)], shell=False)
        os.startfile(project_folder)  # noqa: S606
    return True
