"""STR permit feasibility checker.

Looks up local STR regulations from a pre-built database to determine
whether short-term rentals are allowed in a given city/county.
"""

import json
import logging
from pathlib import Path

from src.models import PermitInfo, PermitStatus, Property

logger = logging.getLogger(__name__)

REGULATIONS_FILE = Path("data/str_regulations.json")


class PermitChecker:
    def __init__(self, regulations_path: Path = REGULATIONS_FILE):
        self.regulations: dict = {}
        if regulations_path.exists():
            with open(regulations_path) as f:
                self.regulations = json.load(f)
        else:
            logger.warning("STR regulations file not found: %s", regulations_path)

    def check(self, prop: Property) -> PermitInfo:
        """Check STR permit feasibility for a property's location."""
        # Try city+state lookup first, then city alone
        lookup_keys = [
            f"{prop.city}, {prop.state}",
            prop.city,
            prop.market,
        ]

        for key in lookup_keys:
            if key in self.regulations:
                entry = self.regulations[key]
                return PermitInfo(
                    status=PermitStatus(entry.get("status", "UNKNOWN")),
                    permit_required=entry.get("permit_required", True),
                    permit_type=entry.get("permit_type", ""),
                    restrictions=entry.get("restrictions", ""),
                    notes=entry.get("notes", ""),
                )

        logger.info("No STR regulation data for %s, %s", prop.city, prop.state)
        return PermitInfo(status=PermitStatus.UNKNOWN)
