#!/usr/bin/env python3
"""Export Apple Podcasts cached episodes to a destination directory."""

import re
import shutil
import sqlite3
import sys
import urllib.parse
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich import print as rprint

PODCASTS_DB = Path.home() / "Library/Group Containers/243LU875E5.groups.com.apple.podcasts/Documents/MTLibrary.sqlite"

console = Console()


def sanitize_filename(name: str) -> str:
    """Remove characters not safe for filenames."""
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name[:200]


def get_cached_episodes() -> list[dict]:
    if not PODCASTS_DB.exists():
        console.print(f"[red]Database not found:[/red] {PODCASTS_DB}")
        sys.exit(1)

    conn = sqlite3.connect(f"file:{PODCASTS_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute("""
            SELECT
                p.ZTITLE        AS podcast,
                e.ZEPISODENUMBER AS episode_num,
                e.ZSEASONNUMBER  AS season_num,
                e.ZTITLE         AS title,
                e.ZUUID          AS uuid,
                e.ZASSETURL      AS asset_url,
                e.ZPUBDATE       AS pub_date
            FROM ZMTEPISODE e
            JOIN ZMTPODCAST p ON e.ZPODCAST = p.Z_PK
            WHERE e.ZASSETURL IS NOT NULL
            ORDER BY p.ZTITLE, e.ZPUBDATE DESC
        """)
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def asset_url_to_path(asset_url: str) -> Path:
    path_str = urllib.parse.unquote(urllib.parse.urlparse(asset_url).path)
    return Path(path_str)


def build_filename(ep: dict) -> str:
    podcast = sanitize_filename(ep["podcast"] or "Unknown Podcast")
    title = sanitize_filename(ep["title"] or "Unknown Title")

    if ep["episode_num"]:
        ep_num = f"E{int(ep['episode_num']):04d}"
    else:
        ep_num = None

    if ep_num:
        name = f"{podcast} - {ep_num} - {title}.mp3"
    else:
        name = f"{podcast} - {title}.mp3"
    return name


def parse_selection(selection_str: str, max_idx: int) -> list[int]:
    """Parse comma-separated numbers and ranges like '1,3,5-8' into a sorted list of indices."""
    indices = set()
    for part in selection_str.split(','):
        part = part.strip()
        if '-' in part:
            try:
                start, end = part.split('-', 1)
                indices.update(range(int(start), int(end) + 1))
            except ValueError:
                console.print(f"[yellow]Skipping invalid range:[/yellow] {part}")
        else:
            try:
                indices.add(int(part))
            except ValueError:
                console.print(f"[yellow]Skipping invalid value:[/yellow] {part}")
    return sorted(i for i in indices if 1 <= i <= max_idx)


def display_episodes(episodes: list[dict]) -> None:
    table = Table(title="Cached Apple Podcast Episodes", show_lines=False, header_style="bold cyan")
    table.add_column("#", style="dim", width=5, justify="right")
    table.add_column("Podcast", style="bold", min_width=20)
    table.add_column("Ep#", justify="right", width=6)
    table.add_column("Title", min_width=30)

    current_podcast = None
    for i, ep in enumerate(episodes, 1):
        podcast_display = ep["podcast"] or "Unknown"
        if podcast_display != current_podcast:
            current_podcast = podcast_display
            podcast_cell = f"[green]{podcast_display}[/green]"
        else:
            podcast_cell = ""

        ep_num = str(int(ep["episode_num"])) if ep["episode_num"] else "-"
        table.add_row(str(i), podcast_cell, ep_num, ep["title"] or "Unknown")

    console.print(table)


def main():
    console.print("[bold cyan]Apple Podcasts Exporter[/bold cyan]\n")

    episodes = get_cached_episodes()
    if not episodes:
        console.print("[yellow]No cached episodes found.[/yellow]")
        sys.exit(0)

    display_episodes(episodes)

    console.print(f"\n[dim]Total: {len(episodes)} cached episodes[/dim]")
    console.print("\nEnter episode numbers to export (e.g. [bold]1,3,5-8[/bold], or [bold]all[/bold]):")

    try:
        selection_str = input("> ").strip()
    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Cancelled.[/yellow]")
        sys.exit(0)

    if selection_str.lower() == 'all':
        selected_indices = list(range(1, len(episodes) + 1))
    else:
        selected_indices = parse_selection(selection_str, len(episodes))

    if not selected_indices:
        console.print("[yellow]No valid episodes selected.[/yellow]")
        sys.exit(0)

    selected_episodes = [episodes[i - 1] for i in selected_indices]
    console.print(f"\n[green]{len(selected_episodes)} episode(s) selected.[/green]")

    console.print("\nDestination directory:")
    try:
        dest_str = input("> ").strip()
    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Cancelled.[/yellow]")
        sys.exit(0)

    dest = Path(dest_str).expanduser().resolve()
    dest.mkdir(parents=True, exist_ok=True)

    console.print()
    errors = []
    for ep in selected_episodes:
        src = asset_url_to_path(ep["asset_url"])
        filename = build_filename(ep)
        dst = dest / filename

        if not src.exists():
            msg = f"Source not found: {src.name}"
            console.print(f"  [red]SKIP[/red]  {filename}  [dim]({msg})[/dim]")
            errors.append((filename, msg))
            continue

        if dst.exists():
            console.print(f"  [yellow]EXISTS[/yellow] {filename}")
            continue

        try:
            shutil.copy2(src, dst)
            console.print(f"  [green]OK[/green]    {filename}")
        except OSError as e:
            msg = str(e)
            console.print(f"  [red]ERROR[/red] {filename}  [dim]({msg})[/dim]")
            errors.append((filename, msg))

    console.print()
    success = len(selected_episodes) - len(errors)
    console.print(f"[bold]Done.[/bold] {success}/{len(selected_episodes)} exported to [cyan]{dest}[/cyan]")
    if errors:
        console.print(f"[red]{len(errors)} error(s)[/red] — check output above.")


if __name__ == "__main__":
    main()
