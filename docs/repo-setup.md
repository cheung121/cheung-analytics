# GitHub Repo Setup

Repository:

```text
https://github.com/cheung121/cheung-analytics
```

This workspace is ready to be pushed to that repository, but `git` is not installed in the current shell environment, so I could not connect and push directly from here.

## If Git Is Installed Later

Run these commands from the project root:

```powershell
git init
git branch -M main
git remote add origin https://github.com/cheung121/cheung-analytics.git
git add .
git commit -m "Initial Cheung Analytics website and automation scaffold"
git push -u origin main
```

## After The First Push

1. Open the repository on GitHub.
2. Go to `Settings > Pages`.
3. Ensure the site is set to deploy from GitHub Actions.
4. The workflow in `.github/workflows/deploy-site.yml` will publish the `site/` folder.

## Recommended Next Repo Additions

- Add a screenshot of the homepage to the README.
- Store future X API secrets in GitHub repository secrets, not in files.
- Keep generated drafts out of the repo if you do not want frequent content churn.
- Use issues as a content backlog for new graphic formats.

