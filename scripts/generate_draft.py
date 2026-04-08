from __future__ import annotations

import argparse
import json
import sys
import textwrap
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, date, datetime
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = ROOT / "site"
GENERATED_DIR = SITE_DIR / "generated"
GRAPHICS_DIR = GENERATED_DIR / "graphics"
POSTS_DIR = GENERATED_DIR / "posts"
DRAFTS_DIR = ROOT / "outputs" / "drafts"
SAMPLE_DATA = ROOT / "data" / "sample_leaders.json"

BRAND = {
    "name": "Cheung Analytics",
    "handle": "@CheungAnalytics",
    "green_950": "#041f1a",
    "green_900": "#062d25",
    "green_700": "#0f5144",
    "silver": "#cbd4d0",
    "white": "#ffffff",
}


def fetch_json(url: str, timeout: int = 15) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "CheungAnalytics/0.1 (+https://x.com/CheungAnalytics)",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def mlb_hr_leader_url(season: int, limit: int) -> str:
    params = {
        "stats": "season",
        "group": "hitting",
        "playerPool": "ALL",
        "sortStat": "homeRuns",
        "order": "desc",
        "season": str(season),
        "sportIds": "1",
        "limit": str(limit),
        "gameType": "R",
        "hydrate": "person,team",
    }
    return "https://statsapi.mlb.com/api/v1/stats?" + urllib.parse.urlencode(params)


def normalize_mlb_leaders(payload: dict, limit: int) -> list[dict]:
    splits = payload.get("stats", [{}])[0].get("splits", [])
    leaders: list[dict] = []

    for idx, split in enumerate(splits[:limit], start=1):
        player = split.get("player") or split.get("person") or {}
        team = split.get("team") or {}
        stat = split.get("stat") or {}
        leaders.append(
            {
                "rank": idx,
                "name": player.get("fullName", "Unknown Player"),
                "team": team.get("name", "MLB"),
                "value": int(float(stat.get("homeRuns", 0) or 0)),
                "secondary": f"{stat.get('ops', '---')} OPS | {stat.get('rbi', '--')} RBI",
            }
        )

    return leaders


def load_leaders(season: int, limit: int, offline: bool) -> tuple[list[dict], str]:
    if not offline:
        try:
            payload = fetch_json(mlb_hr_leader_url(season, limit))
            leaders = normalize_mlb_leaders(payload, limit)
            if leaders:
                return leaders, "MLB Stats API"
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            print(f"Live MLB fetch failed, using sample fallback: {exc}", file=sys.stderr)

    sample = json.loads(SAMPLE_DATA.read_text(encoding="utf-8"))
    return sample["leaders"][:limit], sample["generated_from"]


def wrap_svg_text(text: str, width: int = 26) -> list[str]:
    return textwrap.wrap(text, width=width, break_long_words=False) or [text]


def render_svg_card(
    *,
    title: str,
    subtitle: str,
    leaders: list[dict],
    source: str,
    output: Path,
) -> None:
    width = 1600
    height = 900
    max_value = max(int(row["value"]) for row in leaders) if leaders else 1
    rows = []
    y = 288

    for row in leaders:
        value = int(row["value"])
        bar_width = int(760 * (value / max_value)) if max_value else 0
        rows.append(
            f"""
            <g transform="translate(96 {y})">
              <text x="0" y="32" class="rank">#{escape(str(row["rank"]))}</text>
              <text x="104" y="18" class="player">{escape(row["name"])}</text>
              <text x="104" y="58" class="meta">{escape(row["team"])} | {escape(row["secondary"])}</text>
              <rect x="640" y="0" width="800" height="58" rx="29" class="bar-bg" />
              <rect x="640" y="0" width="{bar_width}" height="58" rx="29" class="bar" />
              <text x="1400" y="40" class="value">{value}</text>
            </g>
            """
        )
        y += 100

    title_lines = wrap_svg_text(title, width=28)
    title_svg = []
    for idx, line in enumerate(title_lines[:2]):
        title_svg.append(f'<text x="96" y="{112 + idx * 68}" class="title">{escape(line)}</text>')

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{BRAND["green_950"]}" />
      <stop offset="48%" stop-color="{BRAND["green_900"]}" />
      <stop offset="100%" stop-color="#09120f" />
    </linearGradient>
    <linearGradient id="bar" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{BRAND["silver"]}" />
      <stop offset="100%" stop-color="{BRAND["green_700"]}" />
    </linearGradient>
    <filter id="softGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="22" result="blur" />
      <feColorMatrix in="blur" type="matrix" values="0 0 0 0 0.79 0 0 0 0 0.83 0 0 0 0 0.82 0 0 0 0.38 0" />
      <feBlend in="SourceGraphic" />
    </filter>
    <style>
      .eyebrow {{ fill: {BRAND["silver"]}; font: 800 30px Arial, sans-serif; letter-spacing: 8px; }}
      .title {{ fill: {BRAND["white"]}; font: 900 62px Arial, sans-serif; letter-spacing: -2px; }}
      .subtitle {{ fill: {BRAND["silver"]}; font: 500 29px Arial, sans-serif; }}
      .rank {{ fill: {BRAND["silver"]}; font: 900 42px Arial, sans-serif; }}
      .player {{ fill: {BRAND["white"]}; font: 900 34px Arial, sans-serif; }}
      .meta {{ fill: {BRAND["silver"]}; font: 500 23px Arial, sans-serif; }}
      .value {{ fill: {BRAND["green_950"]}; font: 900 34px Arial, sans-serif; text-anchor: middle; }}
      .bar-bg {{ fill: rgba(255,255,255,0.09); }}
      .bar {{ fill: url(#bar); }}
      .footer {{ fill: {BRAND["silver"]}; font: 700 22px Arial, sans-serif; }}
      .mark {{ fill: none; stroke: {BRAND["silver"]}; stroke-width: 2; opacity: 0.45; }}
    </style>
  </defs>
  <rect width="1600" height="900" fill="url(#bg)" />
  <circle cx="1320" cy="78" r="280" fill="#cbd4d0" opacity="0.08" filter="url(#softGlow)" />
  <circle cx="124" cy="820" r="320" fill="#146553" opacity="0.16" />
  <rect x="44" y="44" width="1512" height="812" rx="44" fill="none" stroke="#cbd4d0" stroke-opacity="0.22" />
  <text x="96" y="72" class="eyebrow">{BRAND["handle"]} | MLB LEADERBOARD</text>
  {"".join(title_svg)}
  <text x="96" y="232" class="subtitle">{escape(subtitle)}</text>
  {"".join(rows)}
  <path class="mark" d="M1344 116 l44 54 l44 -54 l62 120 l-106 126 l-106 -126 z" />
  <text x="96" y="824" class="footer">Cheung Analytics | Original data graphic | Not affiliated with MLB</text>
  <text x="1504" y="824" class="footer" text-anchor="end">Data: {escape(source)}</text>
</svg>
"""
    output.write_text(svg, encoding="utf-8")


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def try_export_png(svg_path: Path) -> Path | None:
    try:
        import cairosvg  # type: ignore
    except ImportError:
        return None

    png_path = svg_path.with_suffix(".png")
    cairosvg.svg2png(url=str(svg_path), write_to=str(png_path), output_width=1600, output_height=900)
    return png_path


def build_draft(season: int, run_date: date, limit: int, offline: bool) -> dict:
    GRAPHICS_DIR.mkdir(parents=True, exist_ok=True)
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)

    leaders, source = load_leaders(season=season, limit=limit, offline=offline)
    date_slug = run_date.isoformat()
    slug = f"{date_slug}-mlb-hr-leaders"
    title = f"MLB home run leaders through {run_date.strftime('%b %d, %Y')}"
    subtitle = "A quick Cheung Analytics leaderboard card built for X and the web."
    summary = f"Top {len(leaders)} MLB home run leaders for the {season} regular season."
    svg_path = GRAPHICS_DIR / f"{slug}.svg"

    render_svg_card(title=title, subtitle=subtitle, leaders=leaders, source=source, output=svg_path)
    png_path = try_export_png(svg_path)

    caption = (
        f"{title}\n\n"
        f"Top {len(leaders)} as of {run_date.strftime('%B %d, %Y')}.\n\n"
        "Data-first graphic from Cheung Analytics. #MLB #BaseballAnalytics"
    )

    draft = {
        "slug": slug,
        "title": title,
        "summary": summary,
        "caption": caption,
        "season": season,
        "date": run_date.isoformat(),
        "source": source,
        "graphic": f"generated/graphics/{svg_path.name}",
        "graphic_png": f"generated/graphics/{png_path.name}" if png_path else None,
        "alt": f"Cheung Analytics graphic showing {summary}",
        "leaders": leaders,
        "x_handle": BRAND["handle"],
        "compliance_note": "Use original graphics and avoid unlicensed MLB/team logos, player photos, and scraped screenshots.",
    }

    post_json = POSTS_DIR / f"{slug}.json"
    write_json(post_json, draft)
    write_json(DRAFTS_DIR / f"{slug}.json", draft)

    latest = {
        "latest": {
            "title": title,
            "summary": summary,
            "graphic": f"generated/graphics/{svg_path.name}",
            "post_json": f"generated/posts/{post_json.name}",
            "alt": draft["alt"],
        },
        "updated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    write_json(GENERATED_DIR / "index.json", latest)
    return draft


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a Cheung Analytics MLB stat draft.")
    parser.add_argument("--season", type=int, default=date.today().year)
    parser.add_argument("--date", dest="run_date", default=date.today().isoformat())
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--offline", action="store_true", help="Use sample data instead of live MLB data.")
    args = parser.parse_args()

    run_date = date.fromisoformat(args.run_date)
    draft = build_draft(season=args.season, run_date=run_date, limit=args.limit, offline=args.offline)

    print("Generated Cheung Analytics draft:")
    print(f"- {draft['title']}")
    print(f"- Graphic: {draft['graphic']}")
    print(f"- Draft JSON: site/generated/posts/{draft['slug']}.json")
    if draft["graphic_png"]:
        print(f"- PNG export: {draft['graphic_png']}")
    else:
        print("- PNG export skipped: install optional dependency with `pip install -r requirements.txt`")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
