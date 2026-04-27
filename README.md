# Export Podcast

A small macOS web app that lets you browse and export cached episodes from the Apple Podcasts app.

![Screenshot of the episode browser](https://raw.githubusercontent.com/murrayo/export-podcast/main/docs/screenshot.png)

## Features

- Browse all locally cached episodes grouped by podcast, sorted by most recent
- Podcast cover art thumbnails loaded from Apple's CDN
- Published date and episode number columns
- Expandable episode descriptions
- Live search filter across podcast names and episode titles
- Select individual episodes, all in a podcast, or everything
- Native macOS folder picker for the export destination
- Color-coded export results (exported / already exists / failed)
- "Open in Finder" button after export

## Requirements

- macOS (Apple Podcasts database path is macOS-specific)
- Python 3.12+
- [pyenv](https://github.com/pyenv/pyenv) (optional, for version pinning)
- Episodes must already be downloaded in the Apple Podcasts app

## Setup

```bash
git clone https://github.com/murrayo/export-podcast.git
cd export-podcast
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Running

```bash
./start.sh
```

This activates the virtual environment, opens `http://localhost:5001` in your browser, and starts the server.

Or manually:

```bash
source .venv/bin/activate
python app.py
```

Then open [http://localhost:5001](http://localhost:5001).

> **Note:** Port 5000 is used by macOS AirPlay Receiver, so this app runs on port 5001.

## How it works

The app reads Apple Podcasts' SQLite database at:

```
~/Library/Group Containers/243LU875E5.groups.com.apple.podcasts/Documents/MTLibrary.sqlite
```

It queries the `ZMTEPISODE` and `ZMTPODCAST` tables for episodes that have a cached file on disk (`ZASSETURL IS NOT NULL`), then copies the selected files to your chosen destination with clean, sanitized filenames in the format:

```
Podcast Name - E0042 - Episode Title.mp3
```
