from __future__ import annotations
import argparse
from pathlib import Path
from himena.consts import ALLOWED_LETTERS


class HimenaCliNamespace(argparse.Namespace):
    """The namespace returned by the CLI parser."""

    profile: str | None
    path: str | None
    log_level: str
    new: str | None
    remove: str | None
    run: str | None
    install: list[str]
    uninstall: list[str]
    uninstall_outdated: bool
    get: list[str]
    list_plugins: bool
    list_profiles: bool
    clear_plugin_configs: bool
    import_time: bool
    host: str = "localhost"
    port: int = 49200
    quit: bool = False
    version: bool = False

    def assert_args_not_given(self) -> None:
        if self.profile is not None or self.path is not None:
            raise ValueError(
                "Profile name and file path cannot be given with this option."
            )

    def norm_profile_and_path(self) -> HimenaCliNamespace:
        if self.profile is not None and not _is_profile_name(self.profile):
            self.path = self.profile
            self.profile = None

        return self

    def abs_path(self) -> str | None:
        """Return the absolute path of the file to open."""
        if self.path is None:
            return None
        fp = Path(self.path).expanduser()
        if fp.exists():
            fp = fp.resolve()
        return str(fp)

    def action_version(self):
        from himena import __version__

        print(f"himena version: {__version__}")

    def action_remove(self):
        _assert_profile_not_none(self.remove)
        self.assert_args_not_given()

        from himena.profile import remove_app_profile

        remove_app_profile(self.remove)
        print(f"Profile {self.remove!r} is removed.")

    def action_new(self):
        _assert_profile_not_none(self.new)
        self.assert_args_not_given()
        from himena.profile import new_app_profile

        new_app_profile(self.new)
        print(
            f"Profile {self.new!r} is created. You can start the application with:\n"
            f"$ himena {self.new}"
        )


def _is_profile_name(arg: str) -> bool:
    return all(c in ALLOWED_LETTERS for c in arg)


def _assert_profile_not_none(profile: str | None) -> None:
    if profile is None:
        raise ValueError("Profile name is required with the --new option.")


class HimenaArgumentParser(argparse.ArgumentParser):
    def __init__(self):
        super().__init__(prog="himena", description="Start the himena GUI application.")
        ### Configure the parser ###
        # fmt: off
        self.add_argument(
            "profile", nargs="?", default=None,
            help=(
                "Profile name. If not given, the default profile is used. If a file path "
                "is given, it will be interpreted as the next 'path' argument and this "
                "argument will be set to None."
            )
        )
        self.add_argument(
            "path", nargs="?", default=None,
            help="File path to open with the GUI."
        )
        self.add_argument(
            "--log-level", nargs="?", default="WARNING",
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            help="Set the default log level.",
        )
        self.add_argument(
            "--new", default=None,
            help="Create a new profile with the given name."
        )
        self.add_argument(
            "--remove", default=None,
            help="Remove the profile of the given name."
        )
        self.add_argument(
            "--run", default=None,
            help="Run the main function of the given script file"
        )
        self.add_argument(
            "--install", nargs="+", default=[], help="Install the given plugins."
        )
        self.add_argument(
            "--uninstall", nargs="+", default=[], help="Uninstall the given plugins."
        )
        self.add_argument(
            "--uninstall-outdated", action="store_true",
            help=(
                "Uninstall all the outdated plugins (plugins that are listed in the) "
                "profile but cannot be found in the Python environment."
            )
        )
        self.add_argument(
            "--get", "-g", nargs="+", default=[],
            help="Install packages from PyPI and add them as plugins."
        )
        self.add_argument(
            "--list-plugins", action="store_true", help="List all the available plugins."
        )
        self.add_argument(
            "--list-profiles", action="store_true",
            help="List all the available profiles."
        )
        self.add_argument(
            "--clear-plugin-configs", action="store_true",
            help="Clear all the plugin configurations in the given profile."
        )
        self.add_argument(
            "--import-time", action="store_true",
            help="Print the import time of the plugins."
        )
        self.add_argument(
            "--host", type=str, default="localhost",
            help="Socket host name to use for the GUI.",
        )
        self.add_argument(
            "--port", type=int, default=49200,
            help="Socket port number to use for the GUI.",
        )
        self.add_argument(
            "--quit", action="store_true",
            help="Quit the running application."
        )
        self.add_argument(
            "--version", "-v", action="store_true",
            help="Show the version and exit."
        )
        # fmt: on

    def parse_args(self, args=None, namespace=None) -> HimenaCliNamespace:
        args = super().parse_args(args, namespace)
        return HimenaCliNamespace(**vars(args))
