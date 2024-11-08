from royalapp.qt._qwindow_resize import ResizeState, RESIZE_STATE_MAP, CURSOR_SHAPE_MAP

def test_dict_complete():
    for rs in ResizeState:
        assert rs in RESIZE_STATE_MAP.values()
        assert rs in CURSOR_SHAPE_MAP
