# Dock Widgets

[Dock widgets](../usage/basics.md#appearance) can be added to the `himena` main window.
Unlike the widgets that are supposed to be added to inside sub-windows, dock widgets
don't need any `WidgetDataModel` to represent their state.

??? note "When to use dock widgets?"

    Unlike sub-windows, dock widgets are always visible to the user but don't have any
    internal data. Therefore, dock widgets are suitable for widgets that make data
    processing routines more efficiently. For example, dock widgets defined in
    `himena_builtins` include:

    - Python interpreter console.
    - File explorers.
    - Command history viewer.

## Register Widget

## Plugin Configuration
