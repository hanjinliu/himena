import numpy as np
from himena import testing, StandardType
from himena.widgets import MainWindow

def test_image_view_change_dimensionality(ui: MainWindow):
    win = ui.add_data(np.zeros((2, 2)), type=StandardType.IMAGE)
    testing.image.test_change_dimensionality(win)

def test_image_view_setting_colormap(ui: MainWindow):
    win = ui.add_data(np.zeros((2, 2)), type=StandardType.IMAGE)
    testing.image.test_setting_colormap(win)

def test_image_view_setting_unit(ui: MainWindow):
    win = ui.add_data(np.zeros((2, 2)), type=StandardType.IMAGE)
    testing.image.test_setting_unit(win)

def test_image_view_setting_axis_names(ui: MainWindow):
    win = ui.add_data(np.zeros((2, 2)), type=StandardType.IMAGE)
    testing.image.test_setting_axis_names(win)

def test_image_view_setting_pixel_scale(ui: MainWindow):
    win = ui.add_data(np.zeros((2, 2)), type=StandardType.IMAGE)
    testing.image.test_setting_pixel_scale(win)

def test_image_view_setting_current_indices(ui: MainWindow):
    win = ui.add_data(np.zeros((2, 2)), type=StandardType.IMAGE)
    testing.image.test_setting_current_indices(win)

def test_image_view_current_roi(ui: MainWindow):
    win = ui.add_data(np.zeros((2, 2)), type=StandardType.IMAGE)
    testing.image.test_current_roi(win)
