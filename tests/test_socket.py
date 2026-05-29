from typing import Callable
from qtpy import QtWidgets as QtW
from himena.__main__ import _send_or_create_window
from himena._socket import lock_file_path, SocketInfo, lock_file_dir
from himena.profile import new_app_profile
from himena.app import QtEventLoopHandler
from himena.widgets._main_window import MainWindow

def test_event_loop_hander(make_himena_ui: Callable[..., MainWindow]):
    himena_ui = make_himena_ui("mock")
    eh = QtEventLoopHandler(himena_ui.app_profile.name)
    qapp = eh.get_app()
    eh._setup_socket(qapp)
    SocketInfo().send_to_window(himena_ui.app_profile.name, [])
    QtW.QApplication.processEvents()
    QtW.QApplication.processEvents()

def test_remained_lock_file(capfd):
    prof_name = "dead_profile"
    lock_file = lock_file_path("dead_profile", 49200)
    with lock_file.open("w") as f:
        SocketInfo(port=49220).dump(f)
    prof = new_app_profile(prof_name)
    ui, _, _ = _send_or_create_window(prof)
    assert ui.app_profile.name == prof_name
    assert lock_file.exists()
    QtW.QApplication.processEvents()
    QtW.QApplication.processEvents()
    ui.close()

def test_using_same_port_without_file():
    prof = new_app_profile("prof")
    ui0, lock0, _ = _send_or_create_window(prof, attrs={"port": 49210})
    assert ui0 is not None
    assert lock0 is not None
    assert lock_file_path("prof", 49210).exists(), str(list(lock_file_dir().glob("*.lock")))

    ui1, lock1, _ = _send_or_create_window(prof, attrs={"port": 49210})
    assert ui1 is not None
    assert lock1 is None

    ui0.close()
    ui1.close()
