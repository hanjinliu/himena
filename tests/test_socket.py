from typing import Callable
from qtpy import QtWidgets as QtW
from himena.__main__ import _send_or_create_window
from himena._socket import send_to_window, lock_file_path, SocketInfo
from himena.profile import new_app_profile
from himena.app import QtEventLoopHandler
from himena.widgets._main_window import MainWindow

def test_event_loop_hander(make_himena_ui: Callable[..., MainWindow]):
    himena_ui = make_himena_ui("mock")
    eh = QtEventLoopHandler(himena_ui.app_profile.name)
    qapp = eh.get_app()
    eh._setup_socket(qapp)
    send_to_window(himena_ui.app_profile.name, [])
    QtW.QApplication.processEvents()
    QtW.QApplication.processEvents()

def test_remained_lock_file(capfd):
    prof_name = "dead_profile"
    lock_file = lock_file_path("dead_profile")
    with lock_file.open("w") as f:
        SocketInfo(port=49220).dump(f)
    prof = new_app_profile(prof_name)
    ui, _ = _send_or_create_window(prof)
    assert ui.app_profile.name == prof_name
    assert lock_file.exists()
    QtW.QApplication.processEvents()
    QtW.QApplication.processEvents()
    ui.close()
    assert capfd.readouterr().out.startswith("Socket is not available")
