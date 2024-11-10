"""
`himena` uses profile name as if it is a subcommand.

Examples
--------
$ himena  # launch GUI with the default profile
$ himena myprof  # launch GUI with the profile named "myprof"
$ himena path/to/file.txt  # open the file with the default profile
$ himena myprof path/to/file.txt  # open the file with the profile named "myprof"



"""

import argparse
from himena import new_window
import logging
import sys
from himena.consts import ALLOWED_LETTERS


def _is_testing() -> bool:
    return "pytest" in sys.modules


def _is_profile_name(arg: str) -> bool:
    return all(c in ALLOWED_LETTERS for c in arg)


def _main(
    profile: str | None = None,
    path: str | None = None,
    log_level: str = "WARNING",
    plugin: str | None = None,
):
    if profile is not None and not _is_profile_name(profile):
        path = profile
        profile = None

    logging.basicConfig(level=log_level)
    ui = new_window(profile)
    if path is not None:
        ui.read_file(path, plugin=plugin)
    else:
        if plugin is not None:
            print("Plugin option is ignored without a file path.")
    ui.show(run=not _is_testing())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("profile", nargs="?", default=None)
    parser.add_argument("path", nargs="?", default=None)
    parser.add_argument("--log-level", nargs="?", default="WARNING")
    parser.add_argument("--plugin", nargs="?", default=None)
    args = parser.parse_args()
    _main(args.profile, args.path, log_level=args.log_level, plugin=args.plugin)
