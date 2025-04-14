from contextlib import contextmanager
import json
from pathlib import Path
from typing import Any, Iterable
import warnings
from platformdirs import user_data_dir
from pydantic_compat import BaseModel, Field, field_validator
import importlib.metadata
from packaging.version import Version
from himena.consts import ALLOWED_LETTERS


USER_DATA_DIR = Path(user_data_dir("himena"))


@contextmanager
def patch_user_data_dir(path: str | Path):
    """Change the user data directory to avoid pytest updates the local state."""
    global USER_DATA_DIR
    old = USER_DATA_DIR
    USER_DATA_DIR = Path(path)
    try:
        yield
    finally:
        USER_DATA_DIR = old


def data_dir() -> Path:
    """Get the user data directory."""
    if not USER_DATA_DIR.exists():
        USER_DATA_DIR.mkdir(parents=True)
    return USER_DATA_DIR


def profile_dir() -> Path:
    _dir = data_dir() / "profiles"
    if not _dir.exists():
        _dir.mkdir(parents=True)
    return _dir


# Plugin place and the version added.
# NOTE: The version that added this `DEFAULT_PLUGINS` variable is 0.0.8.
DEFAULT_PLUGINS: list[tuple[str, Version]] = [
    # Dock widgets
    ("himena_builtins.qt.console", Version("0.0.0")),
    ("himena_builtins.qt.explorer", Version("0.0.0")),
    ("himena_builtins.qt.favorites", Version("0.0.9")),
    ("himena_builtins.qt.history", Version("0.0.0")),
    ("himena_builtins.qt.output", Version("0.0.0")),
    # Matplotlib
    ("himena_builtins.qt.plot", Version("0.0.0")),
    # Widgets
    ("himena_builtins.qt.array", Version("0.0.8")),
    ("himena_builtins.qt.basic", Version("0.0.8")),
    ("himena_builtins.qt.dataframe", Version("0.0.8")),
    ("himena_builtins.qt.image", Version("0.0.8")),
    ("himena_builtins.qt.ipynb", Version("0.0.8")),
    ("himena_builtins.qt.rois", Version("0.0.8")),
    ("himena_builtins.qt.stack", Version("0.0.8")),
    ("himena_builtins.qt.table", Version("0.0.8")),
    ("himena_builtins.qt.text", Version("0.0.8")),
    # Tools
    ("himena_builtins.tools.array", Version("0.0.8")),
    ("himena_builtins.tools.conversions", Version("0.0.8")),
    ("himena_builtins.tools.dataframe", Version("0.0.8")),
    ("himena_builtins.tools.dict", Version("0.0.8")),
    ("himena_builtins.tools.image", Version("0.0.8")),
    ("himena_builtins.tools.others", Version("0.0.8")),
    ("himena_builtins.tools.plot", Version("0.0.8")),
    ("himena_builtins.tools.table", Version("0.0.8")),
    ("himena_builtins.tools.text", Version("0.0.8")),
    # Others
    ("himena_builtins.io", Version("0.0.0")),
    ("himena_builtins.new", Version("0.0.0")),
    ("himena_builtins.user_modifications", Version("0.0.8")),
]


def _default_plugins() -> list[str]:
    """Factory function for the default plugin list."""
    return [place for place, _ in DEFAULT_PLUGINS]


def _current_version() -> str:
    """Get the current version of himena."""
    try:
        return importlib.metadata.version("himena")
    except Exception:
        return "0.0.1"


class KeyBindingOverride(BaseModel):
    key: str
    command_id: str


class AppProfile(BaseModel):
    """Model of a profile."""

    name: str = Field(
        default="default",
        description="Name of the profile.",
        frozen=True,
    )
    version: str = Field(
        default_factory=_current_version,
        description="Version of this profile created.",
        frozen=True,
    )
    plugins: list[str] = Field(
        default_factory=_default_plugins, description="List of plugins to load."
    )
    theme: str = Field(default="light-green", description="Theme to use.")
    startup_commands: list[tuple[str, dict[str, Any] | None]] = Field(
        default_factory=list,
        description="Startup commands that will be executed when the app starts.",
    )
    keybinding_overrides: list[KeyBindingOverride] = Field(default_factory=list)
    plugin_configs: dict[str, dict[str, Any]] = Field(default_factory=dict)

    @classmethod
    def from_json(cls, path) -> "AppProfile":
        """Construct an AppProfile from a json file."""
        with open(path) as f:
            data = json.load(f)
        version_saved = Version(data.get("version", "0.0.1"))
        self = cls(**data)
        if version_saved < Version(_current_version()):
            for place, version_added in DEFAULT_PLUGINS:
                if version_added > version_saved and place not in self.plugins:
                    # Add the default plugin that is implemented after the profile was
                    # saved.
                    self.plugins.append(place)
        return self

    @classmethod
    def default(cls, save: bool = False) -> "AppProfile":
        """Return the default profile."""
        prof = AppProfile()
        if save and not (profile_dir() / f"{prof.name}.json").exists():
            prof.save()
        return prof

    def save(self, path: str | Path | None = None) -> None:
        """Save profile as a json file."""
        if path is None:
            path = self.profile_path()
        json_string = json.dumps(self.model_dump(), indent=4)
        with open(path, "w") as f:
            f.write(json_string)
        return None

    def profile_path(self) -> Path:
        """Path to this profile."""
        return profile_dir() / f"{self.name}.json"

    def with_name(self, name: str) -> "AppProfile":
        """Return a new profile with a new name."""
        return self.model_copy(update={"name": name})

    def with_plugins(self, plugins: list[str]) -> "AppProfile":
        """Return a new profile with new plugins."""
        return self.model_copy(update={"plugins": plugins})

    def with_plugin_configs(self, configs: dict[str, dict[str, Any]]) -> "AppProfile":
        """Return a new profile with new plugin configs."""
        return self.model_copy(update={"plugin_configs": configs})

    def with_keybinding_override(self, key: str, command_id: str) -> "AppProfile":
        """Return a new profile with new keybind overrides."""
        _overrides = self.keybinding_overrides.copy()
        for entry in _overrides:
            if entry.command_id == command_id:
                if key:
                    entry.key = key
                else:
                    _overrides.remove(entry)
                break
        else:
            if key:
                _overrides.append(KeyBindingOverride(key=key, command_id=command_id))
        return self.model_copy(update={"keybinding_overrides": _overrides})

    def update_plugin_config(self, plugin_id: str, **kwargs) -> None:
        """Update the config of the plugin specified by `plugin_id`"""
        from himena.plugins import AppActionRegistry
        from himena.plugins.widget_plugins import WidgetCallbackBase

        reg = AppActionRegistry.instance()
        configs = self.plugin_configs.copy()
        # NOTE: during development, keys of cur_config and configs[plugin_id] may
        # differ. `cur_config` has all the keys that should exist in the current
        # implementation.
        cur_config = reg._plugin_default_configs[plugin_id].as_dict()
        if plugin_id in configs:
            # Profile already has the plugin config
            for ckey, cval in configs[plugin_id].items():
                if ckey in cur_config:
                    cur_config[ckey] = cval
        for k, v in kwargs.items():
            if k in cur_config:
                cur_config[k]["value"] = v
        configs[plugin_id] = cur_config
        self.with_plugin_configs(configs).save()

        # update existing dock widgets with the new config
        params = {}
        for key, opt in cur_config.items():
            params[key] = opt["value"]
        if cb := WidgetCallbackBase.instance_for_command_id(plugin_id):
            for dock in cb._all_widgets:
                # the internal widget should always has the method "update_configs"
                dock.update_configs(params)

    @field_validator("name")
    def _validate_name(cls, value):
        # check if value is a valid file name
        if not all(c in ALLOWED_LETTERS for c in value):
            raise ValueError(f"Invalid profile name: {value}")
        return value


def load_app_profile(name: str) -> AppProfile:
    path = profile_dir() / f"{name}.json"
    if path.exists():
        return AppProfile.from_json(path)
    raise ValueError(
        f"Profile {name!r} does not exist. Please create a new profile with:\n"
        f"$ himena {name} --new"
    )


def iter_app_profiles() -> Iterable[AppProfile]:
    for path in profile_dir().glob("*.json"):
        try:
            yield AppProfile.from_json(path)
        except Exception:
            warnings.warn(f"Could not load profile {path}.")


def new_app_profile(name: str) -> None:
    """Create a new profile."""
    path = profile_dir() / f"{name}.json"
    if path.exists():
        raise ValueError(f"Profile {name!r} already exists.")
    profile = AppProfile.default().with_name(name)
    return profile.save(path)


def remove_app_profile(name: str) -> None:
    """Remove an existing profile."""
    path = profile_dir() / f"{name}.json"
    return path.unlink()
