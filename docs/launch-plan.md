# Cheung Analytics Launch Plan

This plan keeps costs minimal, protects the brand, and builds toward automation without forcing paid API spend before the content is proven.

## Positioning

Cheung Analytics should feel like a sharp MLB data desk: quick stat graphics on X, slightly deeper explanations on the website, and a consistent dark green/silver Spartan visual identity.

Core promise:

```text
MLB data, explained fast.
```

Bio draft:

```text
MLB stats, trends, and original graphics. Data-first baseball analysis by Cheung Analytics. Not affiliated with MLB.
```

## Cost-Control Strategy

- Domain: buy only when the website is ready to share.
- Hosting: use Cloudflare Pages or Vercel free tier.
- Database: avoid at first; use generated JSON files in `site/generated/`.
- Automation: use GitHub Actions scheduled runs.
- X API: avoid until automation is worth the cost; post manually from generated drafts.
- Graphics: generate original SVG templates from code; export to PNG later if needed.

## Content System

Post 2 to 4 times per day during the season:

- Morning: yesterday's leader/trend recap.
- Afternoon: one evergreen player/team chart.
- Night: live or postgame leaderboard.
- Weekly: one deeper website post.

Best first formats:

- HR leaderboard.
- Exit velocity leaderboard.
- Barrel leaderboard.
- Pitcher whiff leaderboard.
- Team rolling 7-day OPS.
- Team rolling 7-day ERA/FIP-style trend.
- "One number to know" player spotlight.

## Automation Stages

Stage 1: Manual posting

- Generate draft graphics with `py scripts\generate_draft.py --season 2026`.
- Export a PNG with `powershell -ExecutionPolicy Bypass -File scripts\export_latest_png.ps1`.
- Review the generated JSON in `outputs/drafts/`.
- Manually post the caption and graphic to `@CheungAnalytics`.

Stage 2: Semi-automated review

- GitHub Actions generates draft artifacts on a schedule.
- You review and post the best drafts.
- Track which formats get likes, reposts, follows, and profile visits.

Stage 3: API automation

- Add official X API media upload and post creation.
- Keep an API spend cap.
- Use automated profile labeling and clear bio disclosure.
- Do not auto-reply, auto-DM, auto-like, or tag players/teams without a reason.

## Brand Rules

- Use the second logo as the primary logo.
- Use the first logo as a hero/banner asset.
- Every graphic should include `Cheung Analytics` or `@CheungAnalytics`.
- Avoid MLB/team logos and player photos unless licensed.
- Do not use screenshots from stat sites as graphics.
- Cite data in small footer text where practical.

## 30-Day Roadmap

Week 1:

- Publish website homepage.
- Generate 10 sample graphics.
- Post manually on X.
- Identify the top 2 formats.

Week 2:

- Add exit velocity and barrel leader cards.
- Start a simple content tracker spreadsheet.
- Add a website section for latest generated posts.

Week 3:

- Add team rolling-trend cards.
- Write the first weekly deep dive.
- Create a pinned X post explaining the account.

Week 4:

- Decide whether X API posting is worth it.
- Add PNG export if X SVG upload is inconvenient.
- Deploy the website to a custom domain.
