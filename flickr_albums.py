import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor

import flickr_api as f

from rich import box
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import BarColumn, Progress, TimeRemainingColumn
from rich.table import Table


MAX_WORKERS = 4

log = logging.getLogger("rich")

progress = Progress(
    "[progress.description]{task.description}",
    BarColumn(bar_width=None),
    "[progress.percentage]{task.percentage:>3.0f}%",
    TimeRemainingColumn(),
)


def _get_flickr_user():
    try:
        with open(".flickr.json") as flick_info:
            flickr_data = json.load(flick_info)
        f.set_keys(api_key=flickr_data["API_KEY"], api_secret=flickr_data["API_SECRET"])
        u = f.Person.findByUserName(flickr_data["USERNAME"])
    except Exception:
        log.error("Boom!")
    return u


def _get_album_list(user):
    ps = user.getPhotosets()
    ps.reverse()
    return ps


def list_albums(args):
    u = _get_flickr_user()
    ps = _get_album_list(u)

    console = Console()
    table = Table(show_footer=False)
    table.border_style = "bright_yellow"
    table.box = box.SIMPLE_HEAD
    table.add_column("ID", justify="right")
    table.add_column("Album Title")

    for i, p in enumerate(ps):
        table.add_row(str(i), p.title)

    console.print(table)


def _download_photo(photo, task_id):
    try:
        log.info(f"Downloading {photo.title}")
        photo.save(f"{photo.title}.jpg")
    except Exception:
        log.error(f"problem downloading {photo.title}")

    progress.update(task_id, advance=1)


def download_album(args):
    u = _get_flickr_user()
    ps = _get_album_list(u)
    album = ps[args.album]

    if not os.path.exists(album.title):
        log.info(f"Creating directory {album.title}")
        os.mkdir(album.title)
    os.chdir(album.title)

    task_id = progress.add_task(f"Downloading {album.title}", total=len(album.getPhotos()))

    with progress:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            for photo in album.getPhotos():
                pool.submit(_download_photo, photo, task_id)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(prog="flickr albums")
    parser.add_argument("-v", "--verbose", action="store_true", help="Turn on debug log messages")
    subparsers = parser.add_subparsers(help="operation")

    list_parser = subparsers.add_parser("list", help="list albums")
    list_parser.set_defaults(func=list_albums)

    download_parser = subparsers.add_parser("download", help="download album")
    download_parser.add_argument("album", type=int, help="album to download")
    download_parser.set_defaults(func=download_album)

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler()],
    )
    args.func(args)
