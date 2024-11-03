import json
from pathlib import Path
from typing import Iterable
import warnings
from platformdirs import user_data_dir
from pydantic_compat import BaseModel, Field

USER_DATA_DIR = Path(user_data_dir("royalapp"))


def profile_dir() -> Path:
    _dir = USER_DATA_DIR / "profiles"
    if not _dir.exists():
        _dir.mkdir(parents=True)
    return _dir


def list_recent_files() -> list[Path | list[Path]]:
    """List the recent files (older first)."""
    _path = USER_DATA_DIR / "recent.json"
    if not _path.exists():
        return []
    with open(USER_DATA_DIR / "recent.json") as f:
        js = json.load(f)
    if not isinstance(js, list):
        return []
    paths: list[Path | list[Path]] = []
    for each in js:
        if not isinstance(each, dict):
            continue
        if "type" not in each:
            continue
        if each["type"] == "group":
            paths.append([Path(p) for p in each["path"]])
        elif each["type"] == "file":
            path = Path(each["path"])
            paths.append(path)
    return paths


def _path_to_list(obj: list[Path | list[Path]]) -> list[str | list[str]]:
    out = []
    for each in obj:
        if isinstance(each, list):
            out.append([p.as_posix() for p in each])
        else:
            out.append(each.as_posix())
    return out


def append_recent_files(inputs: list[Path | list[Path]]) -> None:
    _path = USER_DATA_DIR / "recent.json"
    inputs_str = _path_to_list(inputs)
    if _path.exists():
        with open(_path) as f:
            all_info = json.load(f)
        if not isinstance(all_info, list):
            all_info = []
    else:
        all_info = []
    existing_paths = [each["path"] for each in all_info]
    to_remove: list[int] = []
    for each in inputs_str:
        if each in existing_paths:
            to_remove.append(existing_paths.index(each))
        if isinstance(each, list):
            all_info.append({"type": "group", "path": each})
        elif Path(each).is_file():
            all_info.append({"type": "file", "path": each})
        else:
            all_info.append({"type": "folder", "path": each})
    for i in sorted(to_remove, reverse=True):
        all_info.pop(i)
    if len(all_info) > 60:
        all_info = all_info[-60:]
    with open(_path, "w") as f:
        json.dump(all_info, f, indent=2)
    return None


def _default_plugins() -> list[str]:
    """Factory function for the default plugin list."""
    out = []
    _builtins_dir = Path(__file__).parent.joinpath("builtins")
    for path in _builtins_dir.joinpath("qt").glob("*"):
        if path.name == "__pycache__":
            continue
        out.append(f"royalapp.builtins.qt.{path.name}")
    for path in _builtins_dir.glob("*.py"):
        out.append(f"royalapp.builtins.{path.stem}")
    return out


class AppProfile(BaseModel):
    """Model of a profile."""

    name: str = Field(default="default", description="Name of the profile.")
    plugins: list[str] = Field(
        default_factory=_default_plugins, description="List of plugins to load."
    )
    theme: str = Field(default="default", description="Theme to use.")

    @classmethod
    def from_json(cls, path) -> "AppProfile":
        """Construct an AppProfile from a json file."""
        with open(path) as f:
            data = json.load(f)
        return cls(**data)

    @classmethod
    def default(self) -> "AppProfile":
        """Return the default profile."""
        return AppProfile()

    def save(self, path):
        """Save profile as a json file."""
        with open(path, "w") as f:
            json.dump(self.model_dump(), f, indent=4)
        return None


def load_app_profile(name: str) -> AppProfile:
    path = profile_dir() / f"{name}.json"
    if path.exists():
        return AppProfile.from_json(path)
    return AppProfile.default()


def iter_app_profiles() -> Iterable[AppProfile]:
    for path in profile_dir().glob("*.json"):
        try:
            yield AppProfile.from_json(path)
        except Exception:
            warnings.warn(f"Could not load profile {path}.")


def define_app_profile(name: str, plugins: list[str]):
    path = profile_dir() / f"{name}.json"
    profile = AppProfile(name=name, plugins=plugins)
    profile.save(path)
    return None
