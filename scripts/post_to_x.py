from __future__ import annotations

import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LATEST_INDEX = ROOT / "site" / "generated" / "index.json"


def main() -> int:
    if not LATEST_INDEX.exists():
        print("No generated draft found. Run `python scripts\\generate_draft.py --season 2026` first.")
        return 1

    latest = json.loads(LATEST_INDEX.read_text(encoding="utf-8"))["latest"]
    post_json = ROOT / "site" / latest["post_json"]
    draft = json.loads(post_json.read_text(encoding="utf-8"))

    required = ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"]
    missing = [name for name in required if not os.environ.get(name)]

    print("Latest draft ready for @CheungAnalytics:")
    print(draft["caption"])
    print()
    svg_path = ROOT / "site" / draft["graphic"]
    png_path = svg_path.with_suffix(".png")
    graphic_path = png_path if png_path.exists() else svg_path
    print(f"Graphic: {graphic_path}")

    if missing:
        print()
        print("X API posting is intentionally disabled until credentials are present.")
        print("Missing environment variables: " + ", ".join(missing))
        print("Recommended: keep posting manually until the best-performing formats are proven.")
        return 0

    print()
    print("Credentials found, but live posting is not implemented in this starter.")
    print("Next step: add official X API media upload and post creation here after confirming API spend.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
