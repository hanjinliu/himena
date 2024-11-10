import sys
from app_model import Application
from himena.widgets import current_instance
from himena.__main__ import main

def test_simple():
    sys.argv = ["himena"]
    try:
        main()
    finally:
        Application.destroy("himena")
    current_instance("himena").close()
