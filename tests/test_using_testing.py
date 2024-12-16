import numpy as np
from himena import testing
from himena.widgets import MainWindow

def test_image_view_change_dimensionality(ui: MainWindow):
    testing.image.test_change_dimensionality(ui)

def test_image_view_setting_colormap(ui: MainWindow):
    testing.image.test_setting_colormap(ui)

def test_image_view_setting_unit(ui: MainWindow):
    testing.image.test_setting_unit(ui)

def test_image_view_setting_axis_names(ui: MainWindow):
    testing.image.test_setting_axis_names(ui)

def test_image_view_setting_pixel_scale(ui: MainWindow):
    testing.image.test_setting_pixel_scale(ui)

def test_image_view_setting_current_indices(ui: MainWindow):
    testing.image.test_setting_current_indices(ui)

def test_image_view_current_roi(ui: MainWindow):
    testing.image.test_current_roi(ui)

def test_table_view_accepts_table_like(ui: MainWindow):
    testing.table.test_accepts_table_like(ui)

def test_table_view_current_position(ui: MainWindow):
    testing.table.test_current_position(ui)

def test_table_view_selections(ui: MainWindow):
    testing.table.test_selections(ui)
