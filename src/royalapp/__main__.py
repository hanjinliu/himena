import argparse
from royalapp import new_window
import logging


def _main(
    profile: str | None = None,
    log_level: str = "WARNING",
):
    logging.basicConfig(level=log_level)
    ui = new_window(profile)
    ui.show(run=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("profile", nargs="?", default=None)
    parser.add_argument("--log-level", nargs="?", default="WARNING")
    args = parser.parse_args()
    _main(args.profile, log_level=args.log_level)
