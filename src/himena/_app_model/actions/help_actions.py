from importlib import import_module
import sys
from himena.consts import MenuId
from himena.widgets import MainWindow
from himena.types import ClipboardDataModel
from himena._app_model.actions._registry import ACTIONS


def _open_url(url: str):
    import webbrowser

    webbrowser.open(url)


REPOSITORY_URL = "https://github.com/hanjinliu/himena"


@ACTIONS.append_from_fn(
    id="github-repo",
    title="GitHub Repository",
    menus=[{"id": MenuId.HELP, "group": "98_open-github-group"}],
)
def open_github_repo(ui: MainWindow) -> None:
    """Open the GitHub repository in the default browser."""
    _open_url(REPOSITORY_URL)


@ACTIONS.append_from_fn(
    id="report-issue",
    title="Report Issue",
    menus=[{"id": MenuId.HELP, "group": "98_open-github-group"}],
)
def report_issue(ui: MainWindow) -> None:
    """Open the issue tracker in the default browser."""
    _open_url(REPOSITORY_URL + "/issues/new")


@ACTIONS.append_from_fn(
    id="show-about",
    title="About",
    menus=[{"id": MenuId.HELP, "group": "99_about-group"}],
)
def show_about(ui: MainWindow) -> None:
    """Show the about dialog."""
    from himena import __version__

    lines: list[str] = []
    lines.append(f"<h3>himena {__version__}</h3>")
    lines.append("<b>Dependencies:</b>")
    for dependency in [
        "numpy",
        "app_model",
        "pydantic",
        "superqt",
        "magicgui",
        "platformdirs",
        "pygments",
        "pyyaml",
        "pillow",
        "tabulate",
    ]:
        try:
            mod = import_module(dependency)
            lines.append(f"&nbsp;&nbsp;{dependency}={mod.__version__}")
        except ImportError:
            pass

    lines.append("")
    lines.append("<b>Python:</b>")
    lines.append(f"&nbsp;&nbsp;{sys.version}")
    lines.append("<b>Platform:</b>")
    lines.append(f"&nbsp;&nbsp;{sys.platform}")
    info = "<br>".join(lines)
    if ui.exec_choose_one_dialog(
        "About",
        message=info,
        choices=[("Copy", True), ("OK", False)],
        how="buttons",
    ):
        ui.clipboard = ClipboardDataModel(value=info, type="text.html")
    return None
