from __future__ import annotations

import argparse
import csv
import json
import sys
import textwrap
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, date, datetime, timedelta
from html import escape
from io import StringIO
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = ROOT / "site"
GENERATED_DIR = SITE_DIR / "generated"
GRAPHICS_DIR = GENERATED_DIR / "graphics"
POSTS_DIR = GENERATED_DIR / "posts"
DRAFTS_DIR = ROOT / "outputs" / "drafts"
SAMPLE_HR_DATA = ROOT / "data" / "sample_leaders.json"
SAMPLE_EXIT_VELO_DATA = ROOT / "data" / "sample_exit_velo.json"

BRAND = {
    "name": "Cheung Analytics",
    "handle": "@CheungAnalytics",
    "green_950": "#041f1a",
    "green_900": "#062d25",
    "green_700": "#0f5144",
    "silver": "#cbd4d0",
    "white": "#ffffff",
}

STATCAST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/135.0.0.0 Safari/537.36"
    ),
    "Accept": "text/csv,*/*",
}


def fetch_json(url: str, timeout: int = 15) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "CheungAnalytics/0.2 (+https://x.com/CheungAnalytics)",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_csv_rows(url: str, timeout: int = 30) -> list[dict[str, str]]:
    request = urllib.request.Request(url, headers=STATCAST_HEADERS)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        csv_text = response.read().decode("utf-8-sig")
    return list(csv.DictReader(StringIO(csv_text)))


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


def mlb_schedule_url(target_date: date) -> str:
    params = {
        "sportId": "1",
        "date": target_date.isoformat(),
    }
    return "https://statsapi.mlb.com/api/v1/schedule?" + urllib.parse.urlencode(params)


def statcast_single_game_url(game_pk: int) -> str:
    params = {
        "all": "true",
        "type": "details",
        "game_pk": str(game_pk),
    }
    return "https://baseballsavant.mlb.com/statcast_search/csv?" + urllib.parse.urlencode(params)


def normalize_mlb_leaders(payload: dict, limit: int) -> list[dict]:
    splits = payload.get("stats", [{}])[0].get("splits", [])
    leaders: list[dict] = []

    for idx, split in enumerate(splits[:limit], start=1):
        player = split.get("player") or split.get("person") or {}
        team = split.get("team") or {}
        stat = split.get("stat") or {}
        home_runs = int(float(stat.get("homeRuns", 0) or 0))
        leaders.append(
            {
                "rank": idx,
                "name": player.get("fullName", "Unknown Player"),
                "team": team.get("name", "MLB"),
                "value": home_runs,
                "value_display": str(home_runs),
                "secondary": f"{stat.get('ops', '---')} OPS | {stat.get('rbi', '--')} RBI",
            }
        )

    return leaders


def fetch_game_pks_for_date(target_date: date) -> list[int]:
    payload = fetch_json(mlb_schedule_url(target_date))
    game_pks: list[int] = []
    for game_date in payload.get("dates", []):
        for game in game_date.get("games", []):
            game_pk = game.get("gamePk")
            if game_pk:
                game_pks.append(int(game_pk))
    return game_pks


def batting_team_from_statcast_row(row: dict[str, str]) -> tuple[str, str]:
    inning_half = (row.get("inning_topbot") or "").lower()
    home_team = (row.get("home_team") or "").strip() or "HOME"
    away_team = (row.get("away_team") or "").strip() or "AWAY"
    if inning_half == "top":
        return away_team, home_team
    if inning_half == "bot":
        return home_team, away_team
    return home_team, away_team


def clean_event_label(raw_event: str) -> str:
    return (raw_event or "batted ball").replace("_", " ").title()


def format_decimal(value: float, digits: int = 1) -> str:
    return f"{value:.{digits}f}"


def normalize_exit_velo_rows(rows: list[dict[str, str]], limit: int) -> list[dict]:
    leaders: list[dict] = []

    for row in rows:
        launch_speed_raw = row.get("launch_speed") or ""
        if not launch_speed_raw:
            continue
        if not (row.get("events") or "").strip():
            continue

        try:
            launch_speed = float(launch_speed_raw)
        except ValueError:
            continue

        batting_team, opponent_team = batting_team_from_statcast_row(row)
        distance = row.get("hit_distance_sc") or "--"
        angle = row.get("launch_angle") or "--"
        event = clean_event_label(row.get("events") or "")
        player_name = (row.get("player_name") or "Unknown").strip()
        if "," in player_name:
            parts = [part.strip() for part in player_name.split(",")]
            player_name = " ".join(reversed(parts))

        leaders.append(
            {
                "name": player_name,
                "team": batting_team,
                "opponent": opponent_team,
                "value": launch_speed,
                "value_display": format_decimal(launch_speed),
                "secondary": f"vs {opponent_team} | {event} | {distance} ft | {angle} deg",
                "event": event,
                "distance_ft": distance,
                "launch_angle": angle,
            }
        )

        if len(leaders) >= limit:
            break

    for idx, leader in enumerate(leaders, start=1):
        leader["rank"] = idx

    return leaders


def load_hr_leaders(season: int, limit: int, offline: bool) -> tuple[list[dict], str]:
    if not offline:
        try:
            payload = fetch_json(mlb_hr_leader_url(season, limit))
            leaders = normalize_mlb_leaders(payload, limit)
            if leaders:
                return leaders, "MLB Stats API"
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            print(f"Live MLB fetch failed, using sample fallback: {exc}", file=sys.stderr)

    sample = json.loads(SAMPLE_HR_DATA.read_text(encoding="utf-8"))
    return sample["leaders"][:limit], sample["generated_from"]


def load_exit_velo_leaders(target_date: date, limit: int, offline: bool) -> tuple[list[dict], str]:
    if not offline:
        try:
            rows: list[dict[str, str]] = []
            for game_pk in fetch_game_pks_for_date(target_date):
                rows.extend(fetch_csv_rows(statcast_single_game_url(game_pk)))
            rows.sort(key=lambda row: float(row.get("launch_speed") or 0.0), reverse=True)
            leaders = normalize_exit_velo_rows(rows, limit)
            if leaders:
                return leaders, "Baseball Savant Statcast"
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            print(f"Live Statcast fetch failed, using sample fallback: {exc}", file=sys.stderr)

    sample = json.loads(SAMPLE_EXIT_VELO_DATA.read_text(encoding="utf-8"))
    return sample["leaders"][:limit], sample["generated_from"]


def wrap_svg_text(text: str, width: int = 26) -> list[str]:
    return textwrap.wrap(text, width=width, break_long_words=False) or [text]


def render_svg_card(
    *,
    title: str,
    subtitle: str,
    leaders: list[dict],
    source: str,
    board_label: str,
    output: Path,
) -> None:
    width = 1600
    height = 900
    max_value = max(float(row["value"]) for row in leaders) if leaders else 1
    rows = []
    y = 288

    for row in leaders:
        value = float(row["value"])
        bar_width = int(760 * (value / max_value)) if max_value else 0
        rows.append(
            f"""
            <g transform="translate(96 {y})">
              <text x="0" y="32" class="rank">#{escape(str(row["rank"]))}</text>
              <text x="104" y="18" class="player">{escape(row["name"])}</text>
              <text x="104" y="58" class="meta">{escape(row["team"])} | {escape(row["secondary"])}</text>
              <rect x="640" y="0" width="800" height="58" rx="29" class="bar-bg" />
              <rect x="640" y="0" width="{bar_width}" height="58" rx="29" class="bar" />
              <text x="1400" y="40" class="value">{escape(row['value_display'])}</text>
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
  <text x="96" y="72" class="eyebrow">{BRAND["handle"]} | {escape(board_label)}</text>
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


def resolve_target_date(run_date: date, relative_date: str | None) -> date:
    if relative_date == "yesterday":
        return run_date - timedelta(days=1)
    if relative_date == "today":
        return run_date
    return run_date


def build_hr_draft(season: int, run_date: date, limit: int, offline: bool) -> dict:
    leaders, source = load_hr_leaders(season=season, limit=limit, offline=offline)
    slug = f"{run_date.isoformat()}-mlb-hr-leaders"
    title = f"MLB home run leaders through {run_date.strftime('%b %d, %Y')}"
    subtitle = "A quick Cheung Analytics leaderboard card built for X and the web."
    summary = f"Top {len(leaders)} MLB home run leaders for the {season} regular season."
    caption = (
        f"{title}\n\n"
        f"Top {len(leaders)} as of {run_date.strftime('%B %d, %Y')}.\n\n"
        "Data-first graphic from Cheung Analytics. #MLB #BaseballAnalytics"
    )
    return {
        "slug": slug,
        "title": title,
        "subtitle": subtitle,
        "summary": summary,
        "caption": caption,
        "source": source,
        "leaders": leaders,
        "board_label": "MLB LEADERBOARD",
        "metric": "hr-leaders",
        "season": season,
        "date": run_date.isoformat(),
        "alt": f"Cheung Analytics graphic showing {summary}",
    }


def build_exit_velo_draft(run_date: date, target_date: date, limit: int, offline: bool) -> dict:
    leaders, source = load_exit_velo_leaders(target_date=target_date, limit=limit, offline=offline)
    slug = f"{run_date.isoformat()}-{target_date.isoformat()}-top-exit-velos"
    title = f"Top 5 exit velos | {target_date.strftime('%b %d, %Y')}"
    subtitle = "Hardest-hit MLB balls in play from Baseball Savant Statcast."
    summary = f"Top {len(leaders)} exit velocities from MLB games on {target_date.strftime('%B %d, %Y')}."

    if leaders:
        leader = leaders[0]
        lead_line = (
            f"{leader['name']} led the day at {leader['value_display']} mph "
            f"for {leader['team']}."
        )
    else:
        lead_line = "No tracked exit velocity events were found for that date."

    caption = (
        f"{title}\n\n"
        f"{lead_line}\n"
        f"Statcast sample from MLB games on {target_date.strftime('%B %d, %Y')}.\n\n"
        "Source: Baseball Savant Statcast | Graphic: Cheung Analytics #MLB #BaseballAnalytics"
    )

    return {
        "slug": slug,
        "title": title,
        "subtitle": subtitle,
        "summary": summary,
        "caption": caption,
        "source": source,
        "leaders": leaders,
        "board_label": "EXIT VELO",
        "metric": "exit-velo",
        "season": target_date.year,
        "date": run_date.isoformat(),
        "target_date": target_date.isoformat(),
        "alt": f"Cheung Analytics graphic showing {summary}",
    }


def build_draft(
    *,
    season: int,
    run_date: date,
    limit: int,
    offline: bool,
    metric: str,
    relative_date: str | None,
) -> dict:
    GRAPHICS_DIR.mkdir(parents=True, exist_ok=True)
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)

    if metric == "exit-velo":
        target_date = resolve_target_date(run_date, relative_date)
        draft = build_exit_velo_draft(run_date=run_date, target_date=target_date, limit=limit, offline=offline)
    else:
        draft = build_hr_draft(season=season, run_date=run_date, limit=limit, offline=offline)

    svg_path = GRAPHICS_DIR / f"{draft['slug']}.svg"
    render_svg_card(
        title=draft["title"],
        subtitle=draft["subtitle"],
        leaders=draft["leaders"],
        source=draft["source"],
        board_label=draft["board_label"],
        output=svg_path,
    )
    png_path = try_export_png(svg_path)

    draft["graphic"] = f"generated/graphics/{svg_path.name}"
    draft["graphic_png"] = f"generated/graphics/{png_path.name}" if png_path else None
    draft["x_handle"] = BRAND["handle"]
    draft["compliance_note"] = (
        "Use original graphics and avoid unlicensed MLB/team logos, player photos, and scraped screenshots."
    )

    post_json = POSTS_DIR / f"{draft['slug']}.json"
    write_json(post_json, draft)
    write_json(DRAFTS_DIR / f"{draft['slug']}.json", draft)

    latest = {
        "latest": {
            "title": draft["title"],
            "summary": draft["summary"],
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
    parser.add_argument("--metric", choices=["hr-leaders", "exit-velo"], default="hr-leaders")
    parser.add_argument("--relative-date", choices=["today", "yesterday"], default=None)
    parser.add_argument("--offline", action="store_true", help="Use sample data instead of live data.")
    args = parser.parse_args()

    run_date = date.fromisoformat(args.run_date)
    draft = build_draft(
        season=args.season,
        run_date=run_date,
        limit=args.limit,
        offline=args.offline,
        metric=args.metric,
        relative_date=args.relative_date,
    )

    print("Generated Cheung Analytics draft:")
    print(f"- {draft['title']}")
    print(f"- Metric: {draft['metric']}")
    print(f"- Graphic: {draft['graphic']}")
    print(f"- Draft JSON: site/generated/posts/{draft['slug']}.json")
    if draft["graphic_png"]:
        print(f"- PNG export: {draft['graphic_png']}")
    else:
        print("- PNG export skipped: install optional dependency with `pip install -r requirements.txt`")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
