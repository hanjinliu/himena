"""`himena` uses profile name as if it is a subcommand.

Examples
--------
$ himena  # launch GUI with the default profile
$ himena myprof  # launch GUI with the profile named "myprof"
$ himena path/to/file.txt  # open the file with the default profile
$ himena myprof path/to/file.txt  # open the file with the profile named "myprof"

"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING
import sys
from himena._cli import HimenaArgumentParser, HimenaCliNamespace
from himena._socket import (
    SocketInfo,
    get_unique_lock_file,
    lock_file_path,
)

if TYPE_CHECKING:
    from himena.profile import AppProfile
    from himena.widgets import MainWindow
    from io import TextIOWrapper


def _is_testing() -> bool:
    return "pytest" in sys.modules


def _main(args: HimenaCliNamespace):
    if args.remove:
        from himena._cli.profiles import remove_profile

        return remove_profile(args)
    if args.new:
        from himena._cli.profiles import new_profile

        return new_profile(args)

    args.norm_profile_and_path()

    from himena.profile import load_app_profile

    prof_name = args.profile or "default"

    if args.clear_plugin_configs:
        prof = load_app_profile(prof_name)
        if prof.plugin_configs:
            prof.plugin_configs.clear()
            prof.save()
            print(f"Plugin configurations are cleared for the profile {prof_name!r}.")

    if args.uninstall_outdated:
        from himena._cli.install import uninstall_outdated

        return uninstall_outdated(prof_name)

    if args.list_plugins:
        from himena.utils.entries import iter_plugin_info

        app_profile = load_app_profile(prof_name)
        print("Profile:", prof_name)
        print("Plugins:")
        for info in iter_plugin_info():
            if info.place in app_profile.plugins:
                print(f"- {info.name} ({info.place}, v{info.version})")
        return

    if args.list_profiles:
        from himena.profile import profile_dir

        for path in profile_dir().iterdir():
            print(path.stem)
        return

    if args.get:
        from himena._cli.install import get_and_install

        return get_and_install(args.get, prof_name)

    if args.install or args.uninstall:
        from himena._cli.install import install_and_uninstall

        return install_and_uninstall(args.install, args.uninstall, prof_name)

    logging.basicConfig(level=args.log_level)

    # now it's ready to start the GUI
    app_prof = load_app_profile(prof_name, create_default=args.profile is None)
    attrs = {
        "print_import_time": args.import_time,
        "host": args.host,
        "port": args.port,
    }

    ui, lock = _send_or_create_window(app_prof, args.abs_path(), attrs)
    if ui is not None:
        ui.show(run=not _is_testing())
        lock.close()
        Path(lock.name).unlink(missing_ok=True)


def _send_or_create_window(
    prof: "AppProfile",
    path: str | None = None,
    attrs: dict = {},
) -> "tuple[MainWindow, TextIOWrapper] | None":
    from himena.core import new_window

    if (lock := get_unique_lock_file(prof.name)) is None:
        socket_info = SocketInfo.from_lock(prof.name)
        if path:
            files = path.split(";")
        else:
            files = []
        succeeded = socket_info.send_to_window(prof.name, files)
        if succeeded:
            return None, None
        lock = lock_file_path(prof.name).open("w")

    ui = new_window(prof, app_attributes=attrs)
    ui.socket_info.dump(lock)
    if path is not None:
        ui.read_file(path)
    return ui, lock


def main():
    parser = HimenaArgumentParser()

    # Run the main function with the parsed arguments
    args = parser.parse_args()
    _main(args)

    from himena.widgets._initialize import cleanup

    cleanup()
