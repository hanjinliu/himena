import numpy as np
from himena import testing
from himena.widgets import MainWindow

def test_image_view_change_dimensionality(himena_ui: MainWindow):
    testing.image.test_change_dimensionality(himena_ui)

def test_image_view_setting_colormap(himena_ui: MainWindow):
    testing.image.test_setting_colormap(himena_ui)

def test_image_view_setting_unit(himena_ui: MainWindow):
    testing.image.test_setting_unit(himena_ui)

def test_image_view_setting_axis_names(himena_ui: MainWindow):
    testing.image.test_setting_axis_names(himena_ui)

def test_image_view_setting_pixel_scale(himena_ui: MainWindow):
    testing.image.test_setting_pixel_scale(himena_ui)

def test_image_view_setting_current_indices(himena_ui: MainWindow):
    testing.image.test_setting_current_indices(himena_ui)

def test_image_view_current_roi(himena_ui: MainWindow):
    testing.image.test_current_roi(himena_ui)

def test_table_view_accepts_table_like(himena_ui: MainWindow):
    testing.table.test_accepts_table_like(himena_ui)

def test_table_view_current_position(himena_ui: MainWindow):
    testing.table.test_current_position(himena_ui)

def test_table_view_selections(himena_ui: MainWindow):
    testing.table.test_selections(himena_ui)
