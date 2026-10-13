"""Build the bundled world map used by page 2 (run once; not part of the data pipeline).

Country outlines: Natural Earth 1:110m admin-0 countries (public domain), as
packaged by world-atlas 2.0.2 (ISC licence, Mike Bostock). world-atlas keys
countries by ISO 3166-1 numeric codes; the World Bank uses ISO alpha-3 codes,
so each outline's id is replaced by its alpha-3 code using the code table in
world-countries 5.1.0 (ODbL). Kosovo has no ISO code in Natural Earth; it is
given the World Bank code XKX. The result is written to
data/geo/countries-110m-iso3.json so the map works offline.

    python -m src.build_map
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "geo" / "countries-110m-iso3.json"
ATLAS_URL = "https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/countries-110m.json"
CODES_URL = "https://cdn.jsdelivr.net/npm/world-countries@5.1.0/countries.json"
SPECIAL = {"Kosovo": "XKX"}


def _get(url: str):
    try:
        with urlopen(url, timeout=60) as response:
            return json.load(response)
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        sys.exit(f"Could not fetch {url}: {error}")


def build(atlas: dict, codes: list[dict]) -> dict:
    numeric_to_iso3 = {c["ccn3"]: c["cca3"] for c in codes if c.get("ccn3")}
    countries = atlas["objects"]["countries"]
    kept = []
    for geometry in countries["geometries"]:
        name = geometry.get("properties", {}).get("name", "")
        iso3 = SPECIAL.get(name) or numeric_to_iso3.get(geometry.get("id", ""))
        if iso3:
            geometry["id"] = iso3
            kept.append(geometry)
    countries["geometries"] = kept
    atlas["objects"] = {"countries": countries}
    return atlas


def main() -> None:
    result = build(_get(ATLAS_URL), _get(CODES_URL))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {len(result['objects']['countries']['geometries'])} country outlines to {OUTPUT}")


if __name__ == "__main__":
    main()
