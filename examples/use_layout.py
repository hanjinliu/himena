from himena import new_window

# This example will create a layout like this:
# +-------+-------------+--------+
# |       |             | Right  |
# |       |             |    top |
# | Left  |   Center    +--------+
# |       |             | Right  |
# |       |             | bottom |
# +-------+-------------+--------+
# This layout is kept when the main window is resized.

if __name__ == "__main__":
    ui = new_window()
    tab = ui.add_tab("Main tab")

    win_left = ui.add_object("Left side", type="text")
    win_center = ui.add_object("Center", type="text")
    win_right_top = ui.add_object("Right top side", type="text")
    win_right_bottom = ui.add_object("Right bottom side", type="text")

    layout = tab.add_hbox_layout()
    layout.add(win_left)
    layout.add(win_center, stretch=3)
    sub_layout = layout.add_vbox_layout()
    sub_layout.add(win_right_top)
    sub_layout.add(win_right_bottom)

    ui.show(run=True)
