from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
VENDOR_SITE = ROOT / ".vendor" / "py312"

if VENDOR_SITE.exists():
    vendor_path = str(VENDOR_SITE)
    if vendor_path not in sys.path:
        sys.path.insert(0, vendor_path)
