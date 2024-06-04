import json
from pathlib import Path
from platformdirs import user_data_dir
from pydantic_compat import BaseModel, Field

USER_DATA_DIR = Path(user_data_dir("royalapp"))


def profile_dir() -> Path:
    _dir = USER_DATA_DIR / "profiles"
    if not _dir.exists():
        _dir.mkdir(parents=True)
    return _dir


def _default_plugins() -> list[str]:
    """Factory function for the default plugin list."""
    out = []
    for path in Path(__file__).parent.joinpath("builtins").glob("*"):
        out.append(f"royalapp.builtins.{path.name}")
    return out


class AppProfile(BaseModel):
    name: str = Field(default="default", description="Name of the profile.")
    plugins: list[str] = Field(
        default_factory=_default_plugins, description="List of plugins to load."
    )
    theme: str = Field(default="default", description="Theme to use.")

    @classmethod
    def from_json(cls, path) -> "AppProfile":
        with open(path) as f:
            data = json.load(f)
        return cls(**data)

    def save(self, path):
        with open(path, "w") as f:
            json.dump(self.dict(), f, indent=4)
        return None


def load_app_profile(name: str):
    path = profile_dir() / f"{name}.json"
    return AppProfile.from_json(path)


def define_app_profile(name: str, plugins: list[str]):
    path = profile_dir() / f"{name}.json"
    profile = AppProfile(name=name, plugins=plugins)
    profile.save(path)
    return None
