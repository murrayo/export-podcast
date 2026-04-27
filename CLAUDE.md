# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A macOS Flask web app that exports cached episodes from the Apple Podcasts app to a user-specified directory. The original CLI (`export_podcasts.py`) is retained for reference.

## Running

```bash
source .venv/bin/activate
python app.py          # opens at http://localhost:5000
```

No build step. No test suite. Python version is pinned to 3.12.13 via `.python-version` (pyenv). Install dependencies with `pip install -r requirements.txt`.

## Architecture

**`app.py`** — three Flask routes backed by shared helper functions:

- `GET /` — calls `get_cached_episodes()`, groups results by podcast via `group_by_podcast()`, renders `templates/index.html`.
- `POST /export` — receives a list of `uuids` (checkboxes) and a destination path. Re-queries the DB, filters to selected episodes, copies each file, renders `templates/result.html` with per-file status.
- `POST /reveal` — accepts `{"path": "..."}` JSON and calls `open <path>` via subprocess to open the folder in Finder.

**Database layer** — `get_cached_episodes()` connects read-only to the Apple Podcasts SQLite DB at `~/Library/Group Containers/243LU875E5.groups.com.apple.podcasts/Documents/MTLibrary.sqlite`, joining `ZMTEPISODE` and `ZMTPODCAST` on `ZPODCAST = Z_PK` where `ZASSETURL IS NOT NULL`.

**Filename handling** — `asset_url_to_path()` URL-decodes the SQLite asset URL to a `Path`; `build_filename()` / `sanitize_filename()` produce `Podcast - ENNN - Title.mp3` (max 200 chars, invalid characters stripped).

**Templates** — `templates/index.html` (episode browser with live search, per-podcast select/clear, sticky export footer) and `templates/result.html` (summary stats + per-file status badges + "Open in Finder" button). Both use plain CSS with no external dependencies.

Key constraints: macOS-only (hardcoded DB path), episodes must already be cached locally.
