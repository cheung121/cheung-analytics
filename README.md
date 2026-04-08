# Cheung Analytics

Low-cost MLB analytics brand platform for `@CheungAnalytics`.

This starter build includes:

- A static website in `site/`.
- Brand assets in `site/assets/brand/`.
- A Python content pipeline that fetches MLB leader data, renders a branded SVG graphic, and writes a draft caption.
- A GitHub Actions workflow that can run the draft generator on a schedule.
- A GitHub Pages workflow that can publish the website from your repository.
- A safe default posture: generate drafts first, manually post to X until the account's formats and voice are proven.

## Quick Start

Run the generator:

```powershell
py scripts\generate_draft.py --season 2026
```

Generate a real Statcast sample for exit velocity:

```powershell
py scripts\generate_draft.py --metric exit-velo --date 2025-04-07 --relative-date yesterday
```

Export the latest generated SVG into a PNG for X:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\export_latest_png.ps1
```

Preview the website locally:

```powershell
py -m http.server 8000 -d site
```

Then open:

```text
http://localhost:8000
```

If the MLB request fails or you are offline, the script falls back to `data/sample_leaders.json` so the site and templates still work.

## Launch Workflow

1. Run `py scripts\generate_draft.py --season 2026`.
2. Review the generated draft in `outputs/drafts/`.
3. Export a PNG with `powershell -ExecutionPolicy Bypass -File scripts\export_latest_png.ps1`.
4. Review the graphic in `site/generated/graphics/`.
5. Post manually to `@CheungAnalytics` while the account is new.
6. After the formats are reliable, wire `scripts/post_to_x.py` to the paid official X API.

## GitHub Repo

Repository:

```text
https://github.com/cheung121/cheung-analytics
```

Git is not available in the current shell, so the project has been prepared for that repository but not pushed from this environment.

## X Posting

To post the latest draft with the official X API, create a local `.env` file with:

```text
X_USER_ACCESS_TOKEN=your_user_access_token_here
```

Then run:

```powershell
py scripts\post_to_x.py
```

## Brand Guardrails

- Use the Cheung Analytics logo and original chart templates.
- Avoid MLB/team logos, player headshots, AP/Getty photos, and screenshots unless you have licensing rights.
- Use data to create original analysis and graphics.
- Label automation clearly if the X account becomes fully automated.
- Avoid unsolicited mentions, auto-replies, auto-likes, or trend-jacking.

## Suggested Content Pillars

- Daily leaders: exit velocity, barrels, whiffs, HR, OPS, ERA, K-BB%.
- Player spotlights: "why this breakout looks real."
- Team trend cards: rolling 7-day offense/pitching.
- Rare events: unusual stat combinations from the day.
- Weekly deeper article: one chart with a short explanation.

## Files

- `site/index.html`: public website.
- `site/styles.css`: Cheung Analytics visual system.
- `site/app.js`: loads the latest generated stat card.
- `scripts/generate_draft.py`: data fetch, SVG render, draft caption generation.
- `scripts/export_latest_png.ps1`: converts the latest SVG graphic to PNG using local Edge/Chrome.
- `scripts/post_to_x.py`: placeholder for future official X API posting.
- `.github/workflows/generate-drafts.yml`: scheduled draft generation.
- `.github/workflows/deploy-site.yml`: GitHub Pages deployment workflow.
- `docs/repo-setup.md`: instructions for connecting this workspace to the GitHub repo.
