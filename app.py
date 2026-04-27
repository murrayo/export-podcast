#!/usr/bin/env python3
"""Flask web UI for exporting Apple Podcasts cached episodes."""

import re
import shutil
import sqlite3
import subprocess
import urllib.parse
from pathlib import Path

from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

PODCASTS_DB = (
    Path.home()
    / "Library/Group Containers/243LU875E5.groups.com.apple.podcasts/Documents/MTLibrary.sqlite"
)


def sanitize_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name[:200]


def get_cached_episodes() -> list[dict]:
    if not PODCASTS_DB.exists():
        return []
    conn = sqlite3.connect(f"file:{PODCASTS_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute("""
            SELECT
                p.ZTITLE                AS podcast,
                p.ZARTWORKTEMPLATEURL   AS podcast_art_template,
                e.ZEPISODENUMBER        AS episode_num,
                e.ZSEASONNUMBER         AS season_num,
                e.ZTITLE                AS title,
                e.ZUUID                 AS uuid,
                e.ZASSETURL             AS asset_url,
                e.ZPUBDATE              AS pub_date
            FROM ZMTEPISODE e
            JOIN ZMTPODCAST p ON e.ZPODCAST = p.Z_PK
            WHERE e.ZASSETURL IS NOT NULL
            ORDER BY p.ZTITLE, e.ZPUBDATE DESC
        """)
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def artwork_url(template: str | None, size: int = 60) -> str | None:
    if not template:
        return None
    return template.replace("{w}", str(size)).replace("{h}", str(size)).replace("{f}", "jpg")


def asset_url_to_path(asset_url: str) -> Path:
    return Path(urllib.parse.unquote(urllib.parse.urlparse(asset_url).path))


def build_filename(ep: dict) -> str:
    podcast = sanitize_filename(ep["podcast"] or "Unknown Podcast")
    title = sanitize_filename(ep["title"] or "Unknown Title")
    ep_num = f"E{int(ep['episode_num']):04d}" if ep["episode_num"] else None
    if ep_num:
        return f"{podcast} - {ep_num} - {title}.mp3"
    return f"{podcast} - {title}.mp3"


def group_by_podcast(episodes: list[dict]) -> dict[str, dict]:
    """Return {podcast_name: {"art": url, "episodes": [...]}}."""
    groups: dict[str, dict] = {}
    for ep in episodes:
        name = ep["podcast"] or "Unknown"
        if name not in groups:
            groups[name] = {
                "art": artwork_url(ep.get("podcast_art_template"), size=60),
                "episodes": [],
            }
        groups[name]["episodes"].append(ep)
    return groups


@app.route("/")
def index():
    episodes = get_cached_episodes()
    db_missing = not PODCASTS_DB.exists()
    groups = group_by_podcast(episodes)
    return render_template("index.html", groups=groups, total=len(episodes), db_missing=db_missing)


@app.route("/export", methods=["POST"])
def export():
    uuids = set(request.form.getlist("uuids"))
    dest_str = request.form.get("destination", "").strip()

    if not uuids:
        return render_template("result.html", error="No episodes selected.", results=[], dest=None)
    if not dest_str:
        return render_template("result.html", error="No destination specified.", results=[], dest=None)

    dest = Path(dest_str).expanduser().resolve()
    try:
        dest.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return render_template("result.html", error=f"Cannot create destination: {e}", results=[], dest=dest)

    episodes = get_cached_episodes()
    selected = [ep for ep in episodes if ep["uuid"] in uuids]

    results = []
    for ep in selected:
        filename = build_filename(ep)
        src = asset_url_to_path(ep["asset_url"])
        dst = dest / filename

        if not src.exists():
            results.append({"filename": filename, "status": "missing", "detail": "Source file not found on disk"})
            continue
        if dst.exists():
            results.append({"filename": filename, "status": "exists", "detail": "Already exists at destination"})
            continue
        try:
            shutil.copy2(src, dst)
            results.append({"filename": filename, "status": "ok", "detail": ""})
        except OSError as e:
            results.append({"filename": filename, "status": "error", "detail": str(e)})

    return render_template("result.html", error=None, results=results, dest=dest)


@app.route("/reveal", methods=["POST"])
def reveal():
    data = request.get_json(silent=True) or {}
    path = data.get("path", "")
    if path:
        subprocess.Popen(["open", path])
    return jsonify(ok=True)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
