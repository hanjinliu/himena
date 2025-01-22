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


def _assert_profile_not_none(profile: str | None) -> None:
    if profile is None:
        raise ValueError("Profile name is required with the --new option.")


def _assert_args_not_given(profile: str | None, path: str | None) -> None:
    if profile is not None or path is not None:
        raise ValueError("Profile name and file path cannot be given with this option.")


def _main(
    profile: str | None = None,
    path: str | None = None,
    log_level: str = "WARNING",
    with_plugins: list[str] | None = None,
    new: str | None = None,
    remove: str | None = None,
    install: list[str] = [],
    uninstall: list[str] = [],
    list_plugins: bool = False,
    clear_plugin_configs: bool = False,
):
    if remove:
        _assert_profile_not_none(remove)
        _assert_args_not_given(profile, path)
        from himena.profile import remove_app_profile

        remove_app_profile(remove)
        print(f"Profile {remove!r} is removed.")
        return
    if new:
        _assert_profile_not_none(new)
        _assert_args_not_given(profile, path)
        from himena.profile import new_app_profile

        new_app_profile(new)
        print(
            f"Profile {new!r} is created. You can start the application with:\n"
            f"$ himena {new}"
        )
        return

    if profile is not None and not _is_profile_name(profile):
        path = profile
        profile = None

    from himena.profile import load_app_profile

    if clear_plugin_configs:
        prof = load_app_profile(profile or "default")
        if prof.plugin_configs:
            prof.plugin_configs.clear()
            prof.save()
            print(f"Plugin configurations are cleared for the profile {profile!r}.")

    if list_plugins:
        from himena.utils.entries import iter_plugin_info

        app_profile = load_app_profile(profile or "default")
        print("Profile:", profile or "default")
        print("Plugins:")
        for info in iter_plugin_info():
            if info.place in app_profile.plugins:
                print(f"- {info.name} ({info.place}, v{info.version})")
        return

    if install or uninstall:
        from himena.utils.entries import (
            iter_plugin_info,
            is_submodule,
            HimenaPluginInfo,
        )

        app_profile = load_app_profile(profile or "default")
        plugins_to_write = app_profile.plugins.copy()
        infos_installed: list[HimenaPluginInfo] = []
        infos_uninstalled: list[HimenaPluginInfo] = []
        for info in iter_plugin_info():
            for plugin_name in install:
                if plugin_name in app_profile.plugins:
                    print(f"Plugin {plugin_name!r} is already installed.")
                elif is_submodule(info.place, plugin_name):
                    plugins_to_write.append(info.place)
                    infos_installed.append(info)
                elif info.distribution == plugin_name:
                    plugins_to_write.append(info.place)
                    infos_installed.append(info)

            for plugin_name in uninstall:
                if (
                    is_submodule(info.place, plugin_name)
                    and info.place in plugins_to_write
                ):
                    plugins_to_write.remove(info.place)
                    infos_uninstalled.append(info)
                elif info.distribution == plugin_name:
                    if info.place in plugins_to_write:
                        plugins_to_write.remove(info.place)
                        infos_uninstalled.append(info)
                    else:
                        print(f"Plugin {plugin_name!r} is not installed.")
        if infos_installed:
            print("Plugins installed:")
            for info in infos_installed:
                print(f"- {info.name} ({info.place}, v{info.version})")
        if infos_uninstalled:
            print("Plugins uninstalled:")
            for info in infos_uninstalled:
                print(f"- {info.name} ({info.place}, v{info.version})")
        elif len(infos_uninstalled) == 0 and len(infos_installed) == 0:
            print("No plugins are installed or uninstalled.")
        new_prof = app_profile.with_plugins(plugins_to_write)
        new_prof.save()
        return

    logging.basicConfig(level=log_level)
    ui = new_window(profile, plugins=with_plugins)
    if path is not None:
        ui.read_file(path)
    ui.show(run=not _is_testing())


def main():
    parser = argparse.ArgumentParser(
        prog="himena", description="Start the himena GUI application."
    )

    ### Configure the parser ###
    # fmt: off
    parser.add_argument(
        "profile", nargs="?", default=None,
        help=(
            "Profile name. If not given, the default profile is used. If a file path "
            "is given, it will be interpreted as the next 'path' argument and this "
            "argument will be set to None."
        )
    )
    parser.add_argument(
        "path", nargs="?", default=None,
        help="File path to open with the GUI."
    )
    parser.add_argument(
        "--log-level", nargs="?", default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the default log level.",
    )
    parser.add_argument(
        "--with-plugins", nargs="+", default=None,
        help=(
            "Additional plugins to be loaded. Can be submodule names (xyz.abc) or file "
            "paths."
        )
    )
    parser.add_argument(
        "--new", default=None,
        help="Create a new profile with the given name."
    )
    parser.add_argument(
        "--remove", default=None,
        help="Remove the profile of the given name."
    )
    parser.add_argument(
        "--install", nargs="+", default=[], help="Install the given plugins."
    )
    parser.add_argument(
        "--uninstall", nargs="+", default=[], help="Uninstall the given plugins."
    )
    parser.add_argument(
        "--list-plugins", action="store_true", help="List all the available plugins."
    )
    parser.add_argument(
        "--clear-plugin-configs", action="store_true",
        help="Clear all the plugin configurations in the given profile."
    )
    # fmt: on

    # Run the main function with the parsed arguments
    args = parser.parse_args()
    _main(
        args.profile,
        args.path,
        log_level=args.log_level,
        with_plugins=args.with_plugins,
        new=args.new,
        remove=args.remove,
        install=args.install,
        uninstall=args.uninstall,
        list_plugins=args.list_plugins,
        clear_plugin_configs=args.clear_plugin_configs,
    )
    from himena.widgets._initialize import cleanup

    cleanup()
    return None
