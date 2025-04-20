from himena._socket import send_to_window
from himena.app import QtEventLoopHandler

def test_event_loop_hander():
    eh = QtEventLoopHandler("default")
    qapp = eh.get_app()
    eh._setup_socket(qapp)
    send_to_window("default", [])
