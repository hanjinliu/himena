from __future__ import annotations
from pathlib import Path
from app_model import Application
from royalapp.types import TabTitle, WindowTitle, FileData


_APPLICATIONS: dict[str, Application] = {}


def get_application(name: str) -> Application:
    """Get application by name."""
    if name not in _APPLICATIONS:
        app = Application(name)
        _APPLICATIONS[name] = app
        _init_application(app)
    return _APPLICATIONS[name]


_APP_INSTANCES: dict[str, list[MainWindowMixin]] = {}


class MainWindowMixin:
    def _provide_current_tab_name(self) -> TabTitle:
        raise NotImplementedError

    def _provide_current_sub_window_title(self) -> WindowTitle:
        raise NotImplementedError

    def _process_file_input(self, file_data: FileData) -> None:
        raise NotImplementedError

    def _provide_file_output(self) -> FileData:
        raise NotImplementedError

    def _open_file_dialog(self, mode: str = "r") -> Path | list[Path] | None:
        raise NotImplementedError

    def _close_window(self) -> None:
        raise NotImplementedError


def current_instance(name: str) -> MainWindowMixin:
    return _APP_INSTANCES[name][-1]


def set_current_instance(name: str, instance: MainWindowMixin) -> None:
    if name not in _APP_INSTANCES:
        _APP_INSTANCES[name] = []
    elif instance in _APP_INSTANCES[name]:
        _APP_INSTANCES[name].remove(instance)
    _APP_INSTANCES[name].append(instance)
    return None


def remove_instance(name: str, instance: MainWindowMixin) -> None:
    if name in _APP_INSTANCES:
        _APP_INSTANCES[name].remove(instance)
    return None


def _init_application(app: Application) -> None:
    from royalapp._app_model._actions import ACTIONS

    app.register_actions(ACTIONS)

    @app.injection_store.mark_provider
    def _current_instance() -> MainWindowMixin:
        return current_instance(app.name)

    @app.injection_store.mark_provider
    def _current_tab_name() -> TabTitle:
        return current_instance(app.name)._provide_current_tab_name()

    @app.injection_store.mark_provider
    def _current_sub_window_title() -> WindowTitle:
        return current_instance(app.name)._provide_current_sub_window_title()

    @app.injection_store.mark_provider
    def _provide_file_output() -> FileData:
        return current_instance(app.name)._provide_file_output()

    @app.injection_store.mark_processor
    def _process_file_input(file_data: FileData) -> None:
        return current_instance(app.name)._process_file_input(file_data)
