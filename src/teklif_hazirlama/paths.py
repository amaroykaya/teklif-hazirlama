from __future__ import annotations

import sys
from pathlib import Path


def _project_root() -> Path:
    """Geliştirmede repo kökü; PyInstaller exe'te _MEIPASS."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent.parent


ROOT = _project_root()

ASSETS = ROOT / "assets"

TEMPLATES = ASSETS / "templates"

CONFIG = ROOT / "config"

CUSTOMERS = CONFIG / "customers"

HITAP = CONFIG / "hitap"

TEMPLATE_FILE = TEMPLATES / "teklif_sablonu.xlsx"

REVIZE_TEMPLATE_FILE = TEMPLATES / "revize_teklif_sablonu.xlsx"
