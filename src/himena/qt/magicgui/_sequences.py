from typing import Any, Iterable
from magicgui.types import Undefined, _Undefined
from magicgui.widgets import TupleEdit as _TupleEdit
from magicgui.widgets.bases import BaseValueWidget, ValuedContainerWidget


class TupleEdit(_TupleEdit[tuple]):
    def __init__(
        self,
        value=Undefined,
        *,
        options: dict[str, Any] | None = None,
        **container_kwargs,
    ) -> None:
        from himena.qt.magicgui._register import get_type_map

        self._args_types: tuple[type, ...] | None = None
        container_kwargs.setdefault("labels", False)
        container_kwargs.setdefault("layout", "horizontal")
        ValuedContainerWidget.__init__(self, **container_kwargs)
        self._child_options = options or {}
        self.margins = (0, 0, 0, 0)

        if not isinstance(value, _Undefined):
            if self._args_types is None:
                self._args_types = tuple(type(a) for a in value)
            _value: Iterable[Any] = value
        elif self._args_types is not None:
            _value = (Undefined,) * len(self._args_types)
        else:
            raise ValueError(
                "Either 'value' or 'annotation' must be specified in "
                f"{type(self).__name__}."
            )

        typemap = get_type_map()
        for a in _value:
            i = len(self)
            widget = typemap.create_widget(
                value=a,
                annotation=self._args_types[i],
                name=f"value_{i}",
                options=self._child_options,
            )
            assert isinstance(widget, BaseValueWidget)
            self._insert_widget(i, widget)
            widget.changed.connect(self._emit)

    def _emit(self):
        self.changed.emit(self.value)
