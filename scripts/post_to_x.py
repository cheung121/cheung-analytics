from __future__ import annotations

import argparse
import json
import mimetypes
import os
import uuid
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LATEST_INDEX = ROOT / "site" / "generated" / "index.json"


def load_local_env() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def http_json(url: str, *, method: str = "GET", headers: dict[str, str] | None = None, body: bytes | None = None) -> dict:
    request = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def encode_multipart(fields: dict[str, str], files: list[tuple[str, str, bytes, str]]) -> tuple[bytes, str]:
    boundary = f"----CheungAnalytics{uuid.uuid4().hex}"
    body = bytearray()

    for name, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        body.extend(str(value).encode("utf-8"))
        body.extend(b"\r\n")

    for field_name, filename, content, content_type in files:
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(
            f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode("utf-8")
        )
        body.extend(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
        body.extend(content)
        body.extend(b"\r\n")

    body.extend(f"--{boundary}--\r\n".encode("utf-8"))
    return bytes(body), boundary


def get_access_token() -> str | None:
    return os.environ.get("X_USER_ACCESS_TOKEN") or os.environ.get("X_BEARER_TOKEN")


def upload_media(access_token: str, media_path: Path) -> str:
    mime_type = mimetypes.guess_type(media_path.name)[0] or "application/octet-stream"
    fields = {
        "media_category": "tweet_image",
        "media_type": mime_type,
        "shared": "false",
    }
    files = [("media", media_path.name, media_path.read_bytes(), mime_type)]
    body, boundary = encode_multipart(fields, files)
    response = http_json(
        "https://api.x.com/2/media/upload",
        method="POST",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
        },
        body=body,
    )
    return response["data"]["id"]


def create_post(access_token: str, text: str, media_id: str) -> dict:
    payload = json.dumps({"text": text, "media": {"media_ids": [media_id]}}).encode("utf-8")
    return http_json(
        "https://api.x.com/2/tweets",
        method="POST",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        body=payload,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Post the latest Cheung Analytics draft to X.")
    parser.add_argument("--dry-run", action="store_true", help="Print the pending post without calling the X API.")
    args = parser.parse_args()

    load_local_env()

    if not LATEST_INDEX.exists():
        print("No generated draft found. Run `py scripts\\generate_draft.py --metric exit-velo --relative-date yesterday` first.")
        return 1

    latest = json.loads(LATEST_INDEX.read_text(encoding="utf-8"))["latest"]
    post_json = ROOT / "site" / latest["post_json"]
    draft = json.loads(post_json.read_text(encoding="utf-8"))

    svg_path = ROOT / "site" / draft["graphic"]
    png_path = svg_path.with_suffix(".png")
    graphic_path = png_path if png_path.exists() else svg_path

    print("Latest draft ready for @CheungAnalytics:")
    print(draft["caption"])
    print()
    print(f"Graphic: {graphic_path}")

    if args.dry_run:
        print()
        print("Dry run enabled. No X API calls were made.")
        return 0

    access_token = get_access_token()
    if not access_token:
        print()
        print("X posting is blocked because no user access token was found.")
        print("Set X_USER_ACCESS_TOKEN in the environment or in a local .env file.")
        return 1

    try:
        media_id = upload_media(access_token, graphic_path)
        response = create_post(access_token, draft["caption"], media_id)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print()
        print(f"X API request failed with HTTP {exc.code}.")
        print(detail)
        return 1
    except Exception as exc:  # noqa: BLE001
        print()
        print(f"X posting failed: {exc}")
        return 1

    print()
    print("Post created successfully.")
    print(json.dumps(response, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
