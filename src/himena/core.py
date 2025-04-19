from __future__ import annotations

from typing import TYPE_CHECKING, Any, Sequence, TypeVar
from logging import getLogger
from himena.consts import StandardType
from himena.types import WidgetDataModel
from himena.standards import BaseMetadata
from himena.profile import AppProfile, load_app_profile
from himena.workflow import ProgrammaticMethod

if TYPE_CHECKING:
    import numpy as np
    from himena.widgets import MainWindow
    from himena.standards.model_meta import ImageChannel, ArrayAxis
    from himena.standards.roi import RoiModel, RoiListModel

_LOGGER = getLogger(__name__)
_T = TypeVar("_T")


def new_window(
    profile: str | AppProfile | None = None,
    *,
    plugins: Sequence[str] | None = None,
    backend: str = "qt",
    app_attributes: dict[str, Any] = {},
) -> MainWindow:
    """Create a new window with the specified profile and additional plugins."""
    from himena._app_model import get_model_app
    from himena.widgets._initialize import init_application
    from himena.plugins import install_plugins, override_keybindings

    plugins = list(plugins or [])

    # NOTE: the name of AppProfile and the app_model.Application must be the same.
    if isinstance(profile, str):
        app_prof = load_app_profile(profile)
    elif isinstance(profile, AppProfile):
        app_prof = profile
    elif profile is None:
        try:
            app_prof = load_app_profile("default")
        except ValueError:
            app_prof = AppProfile.default(save=True)
    else:
        raise TypeError("`profile` must be a str or an AppProfile object.")
    model_app = get_model_app(app_prof.name)
    model_app.attributes.update(dict(app_attributes))
    plugins = [p for p in plugins if p not in app_prof.plugins]  # filter duplicates
    plugins = app_prof.plugins + plugins
    _init_backend(backend)
    if plugins:
        install_plugins(model_app, plugins)

    # create the main window
    init_application(model_app)
    override_keybindings(model_app, app_prof)
    main_window = _get_main_window(backend, model_app, theme=app_prof.theme)

    # execute startup commands (don't raise exceptions, just log them)
    exceptions: list[tuple[str, dict, Exception]] = []
    for cmd, kwargs in app_prof.startup_commands:
        try:
            main_window.exec_action(cmd, with_params=kwargs)
        except Exception as e:
            exceptions.append((cmd, kwargs, e))
    if exceptions:
        _LOGGER.error("Exceptions occurred during startup commands:")
        for cmd, kwargs, exc in exceptions:
            _LOGGER.error("  %r (parameters=%r): %s", cmd, kwargs, exc)
    return main_window


def _init_backend(backend: str):
    # This function needed for proper import time calculation
    if backend == "qt":
        import himena.qt  # noqa: F401


def create_model(
    value: _T,
    *,
    type: str | None = None,
    title: str | None = None,
    extension_default: str | None = None,
    extensions: list[str] | None = None,
    metadata: object | None = None,
    force_open_with: str | None = None,
    editable: bool = True,
    add_empty_workflow: bool = False,
) -> WidgetDataModel[_T]:
    """Helper function to create a WidgetDataModel."""
    if type is None:
        if isinstance(metadata, BaseMetadata):
            type = metadata.expected_type()
    if type is None:
        type = StandardType.ANY
    out = WidgetDataModel(
        value=value,
        type=type,
        title=title,
        extension_default=extension_default,
        extensions=extensions or [],
        metadata=metadata,
        force_open_with=force_open_with,
        editable=editable,
    )
    if add_empty_workflow:
        out.workflow = ProgrammaticMethod().construct_workflow()
    return out


def create_text_model(
    value: str,
    *,
    title: str | None = None,
    language: str | None = None,
    spaces: int = 4,
    selection: tuple[int, int] | None = None,
    font_family: str | None = None,
    font_size: int = 10,
    encoding: str | None = None,
    extension_default: str | None = None,
    extensions: list[str] | None = None,
    force_open_with: str | None = None,
    editable: bool = True,
) -> WidgetDataModel[str]:
    """Helper function to create a WidgetDataModel for text."""
    from himena.standards.model_meta import TextMeta

    return create_model(
        value,
        title=title,
        metadata=TextMeta(
            language=language,
            spaces=spaces,
            selection=selection,
            font_family=font_family,
            font_size=font_size,
            encoding=encoding,
        ),
        extension_default=extension_default,
        extensions=extensions or [],
        force_open_with=force_open_with,
        editable=editable,
    )


def create_table_model(
    value: Any,
    *,
    title: str | None = None,
    current_position: tuple[int, int] | None = None,
    selections: list[tuple[tuple[int, int], tuple[int, int]]] | None = None,
    separator: str | None = None,
    extension_default: str | None = None,
    extensions: list[str] | None = None,
    force_open_with: str | None = None,
    editable: bool = True,
) -> WidgetDataModel[np.ndarray[tuple[int, int], str]]:
    """Helper function to create a WidgetDataModel for tables."""
    from himena.standards.model_meta import TableMeta

    return create_model(
        value,
        title=title,
        metadata=TableMeta(
            current_position=current_position,
            selections=selections or [],
            separator=separator,
        ),
        extension_default=extension_default,
        extensions=extensions or [],
        force_open_with=force_open_with,
        editable=editable,
    )


def create_dataframe_model(
    value: _T,
    *,
    title: str | None = None,
    current_position: tuple[int, int] | None = None,
    selections: list[tuple[tuple[int, int], tuple[int, int]]] | None = None,
    separator: str | None = None,
    transpose: bool = False,
    extension_default: str | None = None,
    extensions: list[str] | None = None,
    force_open_with: str | None = None,
    editable: bool = True,
) -> WidgetDataModel[_T]:
    """Helper function to create a WidgetDataModel for dataframes."""
    from himena.standards.model_meta import DataFrameMeta

    return create_model(
        value,
        title=title,
        metadata=DataFrameMeta(
            current_position=current_position,
            selections=selections or [],
            separator=separator,
            transpose=transpose,
        ),
        extension_default=extension_default,
        extensions=extensions or [],
        force_open_with=force_open_with,
        editable=editable,
    )


def create_array_model(
    value: _T,
    *,
    axes: list[str | dict | ArrayAxis] | None = None,
    current_indices: list[int] | None = None,
    selections: list[tuple[tuple[int, int], tuple[int, int]]] | None = None,
    unit: str | None = None,
    title: str | None = None,
    extension_default: str | None = None,
    extensions: list[str] | None = None,
    force_open_with: str | None = None,
    editable: bool = True,
) -> WidgetDataModel[_T]:
    """Helper function to create a WidgetDataModel for arrays."""
    from himena.standards.model_meta import ArrayMeta

    return create_model(
        value,
        title=title,
        metadata=ArrayMeta(
            axes=_norm_axes(axes, value),
            selections=selections or [],
            unit=unit,
            current_indices=current_indices,
        ),
        extension_default=extension_default,
        extensions=extensions or [],
        force_open_with=force_open_with,
        editable=editable,
    )


def create_image_model(
    value: _T,
    *,
    axes: list[str | dict | ArrayAxis] | None = None,
    channels: list[str | dict | ImageChannel] | None = None,
    channel_axis: int | None = None,
    current_roi: RoiModel | None = None,
    rois: RoiListModel | None = None,
    contrast_limits: tuple[float, float] | None = None,
    is_rgb: bool = False,
    title: str | None = None,
    extension_default: str | None = None,
    extensions: list[str] | None = None,
    force_open_with: str | None = None,
    editable: bool = True,
) -> WidgetDataModel[_T]:
    """Helper function to create a WidgetDataModel for images."""
    from himena.standards.model_meta import ImageMeta
    from himena.standards.roi import RoiListModel

    return create_model(
        value,
        title=title,
        metadata=ImageMeta(
            axes=_norm_axes(axes, value),
            channels=_norm_channels(channels),
            is_rgb=is_rgb,
            current_roi=current_roi,
            rois=rois or RoiListModel(),
            contrast_limits=contrast_limits,
            channel_axis=channel_axis,
        ),
        extension_default=extension_default,
        extensions=extensions or [],
        force_open_with=force_open_with,
        editable=editable,
    )


def _get_main_window(backend: str, *args, **kwargs) -> MainWindow:
    if backend == "qt":
        from himena.qt import MainWindowQt

        return MainWindowQt(*args, **kwargs)
    elif backend == "mock":
        from himena.mock import MainWindowMock

        return MainWindowMock(*args, **kwargs)
    raise ValueError(f"Invalid backend: {backend}")


def _norm_axes(axes, value) -> list[ArrayAxis]:
    from himena.data_wrappers import wrap_array
    from himena.standards.model_meta import ArrayAxis

    if axes is None:
        arr = wrap_array(value)
        _axes = arr.infer_axes()
    else:
        _axes: list[ArrayAxis] = []
        for axis in axes:
            if isinstance(axis, str):
                _axes.append(ArrayAxis(name=axis))
            elif isinstance(axis, dict):
                _axes.append(ArrayAxis(**axis))
            elif isinstance(axis, ArrayAxis):
                _axes.append(axis)
            else:
                raise TypeError(f"Invalid axis type: {type(axis)}")
    return _axes


def _norm_channels(channels) -> list[ImageChannel] | None:
    from himena.standards.model_meta import ImageChannel

    if channels is None:
        _channels = [ImageChannel.default()]
    else:
        _channels = []
        for ch in channels:
            if isinstance(ch, str):
                _channels.append(ImageChannel(colormap=ch))
            elif isinstance(ch, ImageChannel):
                _channels.append(ch)
            else:
                raise TypeError(f"Invalid channel type: {type(ch)}")
    return _channels
