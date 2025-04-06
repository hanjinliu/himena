"""`himena` uses profile name as if it is a subcommand.

Examples
--------
$ himena  # launch GUI with the default profile
$ himena myprof  # launch GUI with the profile named "myprof"
$ himena path/to/file.txt  # open the file with the default profile
$ himena myprof path/to/file.txt  # open the file with the profile named "myprof"

"""

import logging
import sys
from himena._cli import HimenaArgumentParser, HimenaCliNamespace


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

    if args.clear_plugin_configs:
        prof = load_app_profile(args.profile or "default")
        if prof.plugin_configs:
            prof.plugin_configs.clear()
            prof.save()
            print(
                f"Plugin configurations are cleared for the profile {args.profile!r}."
            )

    if args.uninstall_outdated:
        from himena._cli.install import uninstall_outdated

        return uninstall_outdated(args.profile)

    if args.list_plugins:
        from himena.utils.entries import iter_plugin_info

        app_profile = load_app_profile(args.profile or "default")
        print("Profile:", args.profile or "default")
        print("Plugins:")
        for info in iter_plugin_info():
            if info.place in app_profile.plugins:
                print(f"- {info.name} ({info.place}, v{info.version})")
        return

    if args.install or args.uninstall:
        from himena._cli.install import install_and_uninstall

        return install_and_uninstall(args.install, args.uninstall, args.profile)

    logging.basicConfig(level=args.log_level)

    # now it's ready to start the GUI
    from himena import new_window

    ui = new_window(args.profile)
    if args.path is not None:
        ui.read_file(args.path)
    ui.show(run=not _is_testing())


def main():
    parser = HimenaArgumentParser()

    # Run the main function with the parsed arguments
    args = parser.parse_args()
    _main(args)

    from himena.widgets._initialize import cleanup

    cleanup()
    return None
