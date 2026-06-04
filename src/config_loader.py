"""Load and validate configuration."""

from __future__ import annotations

from pathlib import Path

import yaml

from .utils import normalize_path

DEFAULT_CONFIG = Path("config.yaml")
EXAMPLE_CONFIG = Path("config.example.yaml")


def load_config(path: Path | None = None) -> dict:
    config_path = normalize_path(path or DEFAULT_CONFIG)
    if not config_path.exists():
        example = normalize_path(EXAMPLE_CONFIG)
        raise FileNotFoundError(
            f"Config not found: {config_path}\n"
            f"Copy {example.name} to {config_path.name} and edit your drive paths."
        )
    with config_path.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    _validate(cfg)
    return cfg


def _validate(cfg: dict) -> None:
    required = [
        ("sd_cards", "primary"),
        ("sd_cards", "backup"),
        ("destinations", "ssd_editing"),
        ("destinations", "hdd_backup"),
        ("destinations", "hdd_backup_mirror"),
    ]
    for *parents, key in required:
        node = cfg
        for p in parents:
            if p not in node:
                raise ValueError(f"Missing config section: {'.'.join(parents)}")
            node = node[p]
        if key not in node:
            raise ValueError(f"Missing config key: {'.'.join(parents + [key])}")
