import argparse
from royalapp import new_window


def _main(profile: str | None = None):
    ui = new_window(profile)
    ui.show(run=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("profile", nargs="?", default=None)
    args = parser.parse_args()
    _main(args.profile)
