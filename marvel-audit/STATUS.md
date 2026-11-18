# Marvel CBH/CBRO audit — execution status

This branch is deliberately isolated from DC Tracker main.

## Current state
- The Python scraper and workflow have been committed.
- A draft PR (#1) was opened to request CI execution.
- The GitHub connector reports **no workflow runs** for the latest commit, and no commit statuses.
- No fetched data, verified issue mappings, or import-ready JSON exist yet.

## Important limitations
- This is a *heuristic diagnostic*, not an exhaustive comparison.
- CBH includes trade paperbacks, which must be expanded from collected issue metadata.
- CBH reading scope stops at Irredeemable Ant-Man #12; extraction must stop there on the final page.
- CBRO progress IDs must be read from actual page markup or a verified exported JSON, not invented.
- An imported JSON should preserve original progress and only add independently verified IDs.
- If Actions remains unavailable, enable Actions in repository settings or execute the workflow from GitHub's Actions tab after the workflow exists on the default branch; **do not merge this draft PR into main** merely to run it.

## Reports
The current script only produces preliminary CSVs and an explicit warning. Do not use it to update CBRO progress.
