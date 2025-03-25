from himena.profile import load_app_profile
from himena.utils.entries import iter_plugin_info, is_submodule, HimenaPluginInfo


def install_and_uninstall(
    install: list[str], uninstall: list[str], profile: str | None
):
    app_profile = load_app_profile(profile or "default")
    plugins_to_write = app_profile.plugins.copy()
    infos_installed: list[HimenaPluginInfo] = []
    infos_uninstalled: list[HimenaPluginInfo] = []
    for info in iter_plugin_info():
        for plugin_name in install:
            if plugin_name in app_profile.plugins:
                print(f"Plugin {plugin_name!r} is already installed.")
            elif _is_path_like(plugin_name):
                raise NotImplementedError
            elif is_submodule(info.place, plugin_name):
                plugins_to_write.append(info.place)
                infos_installed.append(info)
            elif info.distribution == plugin_name:
                plugins_to_write.append(info.place)
                infos_installed.append(info)

        for plugin_name in uninstall:
            if is_submodule(info.place, plugin_name) and info.place in plugins_to_write:
                plugins_to_write.remove(info.place)
                infos_uninstalled.append(info)
            elif _is_path_like(plugin_name):
                raise NotImplementedError
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


def _is_path_like(name: str) -> bool:
    return "/" in name or "\\" in name
