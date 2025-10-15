# Swine-paper-tracker
Automatically tracks new swine-related papers using Crossref API

## GitHub Actions: Weekly fetch

This repository includes a GitHub Actions workflow that runs weekly to fetch recent swine/pig-related papers and save them as weekly archive files.

- Schedule: Every Wednesday at 09:00 US Eastern (the workflow is scheduled at 13:00 UTC, which corresponds to 09:00 EDT during daylight saving time). Note: GitHub Actions uses UTC for cron schedules; DST shifts may change the local offset. See note below.
- What it does: checks out the repo, sets up Python, installs dependencies from `requirements.txt`, runs `fetch_papers.py` with the default query `"pig OR swine"` for the last 30 days, creates a new markdown file in the `weekly/` directory named `YYYY_MM_DD.md` (for example `2025_10_15.md`) for that run, and commits any new files back to the repository.

Note about DST: The workflow cron is set to 13:00 UTC so it will match 09:00 US Eastern during daylight saving time (EDT). If you require strict, unchanging local time behavior year-round, consider using a PAT and scheduling two crons or adjusting manually when DST starts/ends.

### If the workflow cannot push changes

By default the workflow uses the built-in `GITHUB_TOKEN` to push commits. If your repository has branch protection rules or other restrictions that prevent the workflow from pushing, create a Personal Access Token (PAT) with the `repo` scope and add it as a secret in the repository settings (for example `GH_PUSH_TOKEN`). Then modify the workflow to use that secret when pushing.

Steps:

1. Go to Settings → Secrets and variables → Actions → New repository secret and add `GH_PUSH_TOKEN` with your PAT.
2. Update the `Commit results` step in `.github/workflows/weekly_fetch.yml` to authenticate with the PAT before pushing, for example:

```yaml
			- name: Commit results
				env:
					GH_PUSH_TOKEN: ${{ secrets.GH_PUSH_TOKEN }}
				run: |
					git config user.name "github-actions[bot]"
					git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
					git remote set-url origin https://x-access-token:${GH_PUSH_TOKEN}@github.com/${{ github.repository }}.git
					git add weekly/*.md journals_issn.txt || true
					git commit -m "Weekly: fetch latest swine papers" || echo "No changes to commit"
					git push origin HEAD:${{ github.ref_name }}
```

Keep your PAT secret and limit its scope only to what's necessary. After adding the secret and updating the workflow, the action should be able to push changes even when branch protection requires status checks or other constraints.

If you want any changes to the schedule, query, or commit message format, tell me and I will update the workflow.

