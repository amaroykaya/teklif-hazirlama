from pathlib import Path



ROOT = Path(__file__).resolve().parent.parent.parent

ASSETS = ROOT / "assets"

TEMPLATES = ASSETS / "templates"

CONFIG = ROOT / "config"

CUSTOMERS = CONFIG / "customers"

HITAP = CONFIG / "hitap"

TEMPLATE_FILE = TEMPLATES / "teklif_sablonu.xlsx"

REVIZE_TEMPLATE_FILE = TEMPLATES / "revize_teklif_sablonu.xlsx"

