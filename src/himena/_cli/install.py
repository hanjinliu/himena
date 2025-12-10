from pathlib import Path
from himena.profile import load_app_profile
from himena.utils.entries import iter_plugin_info, is_submodule, HimenaPluginInfo
from himena.utils.install_plugin import get_install_tool
from configparser import ConfigParser, NoOptionError
import re


def install_and_uninstall(
    install: list[str], uninstall: list[str], profile: str | None
):
    """Process the --install and --uninstall commands."""
    app_profile = load_app_profile(profile or "default")
    plugins_updated = app_profile.plugins.copy()
    infos_installed: list[HimenaPluginInfo] = []
    infos_uninstalled: list[HimenaPluginInfo] = []

    def _install(plugin_info: HimenaPluginInfo) -> None:
        if plugin_info not in infos_installed:
            plugins_updated.append(plugin_info.place)
            infos_installed.append(plugin_info)

    # first, resolve local plugins
    for plugin_name in install:
        if _is_path_like(plugin_name):
            if not Path(plugin_name).exists():
                raise FileNotFoundError(f"Path {plugin_name!r} does not exist.")
            plugin_info_loc = HimenaPluginInfo.from_local_file(plugin_name)
            if plugin_info_loc.place in app_profile.plugins:
                print(f"Plugin {plugin_name!r} is already installed.")
            else:
                plugins_updated.append(plugin_info_loc.place)
                infos_installed.append(plugin_info_loc)
    for plugin_name in uninstall:
        if _is_path_like(plugin_name):
            plugin_info_loc = HimenaPluginInfo.from_local_file(plugin_name)
            if plugin_info_loc.place in app_profile.plugins:
                plugins_updated.remove(plugin_info_loc.place)
                infos_uninstalled.append(plugin_info_loc)
            else:
                print(f"Plugin {plugin_name!r} is not installed.")

    # then, resolve plugins from the distribution
    for info in iter_plugin_info():
        for plugin_name in install:
            if plugin_name in app_profile.plugins:
                print(f"Plugin {plugin_name!r} is already installed.")
            elif is_submodule(info.place, plugin_name):
                _install(info)
            elif info.distribution == plugin_name:
                _install(info)

        for plugin_name in uninstall:
            if is_submodule(info.place, plugin_name) and info.place in plugins_updated:
                plugins_updated.remove(info.place)
                infos_uninstalled.append(info)
            elif info.distribution == plugin_name:
                if info.place in plugins_updated:
                    plugins_updated.remove(info.place)
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
    new_prof = app_profile.with_plugins(plugins_updated)
    new_prof.save()


def get_and_install(packages: list[str], profile: str | None):
    """Get the packages from PyPI, git, local file etc. and install them."""
    result = get_install_tool().install(packages)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to get: {packages}")
    packages_normed: list[str] = []
    for package in packages:
        if package.endswith(".git") or package.startswith(("http://", "https://")):
            print(
                "Cannot determine the package name from URL yet. Please manually run\n"
                f"  himena {profile or 'default'} --install <package>"
            )
            continue
        elif Path(package).exists():
            if module_name := _extract_module_name(Path(package).resolve()):
                packages_normed.append(module_name)
            else:
                print(
                    f"Cannot determine the package name from the directory {package}. "
                    "Please manually run\n"
                    f"  himena {profile or 'default'} --install <package>"
                )
        else:
            packages_normed.append(package)
    install_and_uninstall(packages_normed, [], profile)


def uninstall_outdated(profile: str | None):
    app_profile = load_app_profile(profile or "default")
    plugins_updated = app_profile.plugins.copy()
    plugins_outdated: list[str] = []

    for plugin_name in plugins_updated:
        for info in iter_plugin_info():
            if _is_path_like(info.place):
                continue
            if is_submodule(info.place, plugin_name):
                break
            elif info.distribution == plugin_name:
                break
        else:
            plugins_outdated.append(plugin_name)

    if plugins_outdated:
        print("Plugins outdated:")
        for plugin_name in plugins_outdated:
            print(f"- {plugin_name}")

        for plugin_name in plugins_outdated:
            plugins_updated.remove(plugin_name)
        new_prof = app_profile.with_plugins(plugins_updated)
        new_prof.save()
    else:
        print("No outdated plugins found.")


def _is_path_like(name: str) -> bool:
    return "/" in name or "\\" in name


def _extract_module_name(directory: Path) -> str | None:
    """Exctract the module name from a python project directory."""
    if (pyproject_toml := directory.joinpath("pyproject.toml")).exists():
        content = pyproject_toml.read_text()
        match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
        if match:
            return match.group(1)
    if (setup_cfg := directory.joinpath("setup.cfg")).exists():
        cfg = ConfigParser()
        cfg.read(setup_cfg)
        try:
            return cfg.get("metadata", "name")
        except NoOptionError:
            return None
