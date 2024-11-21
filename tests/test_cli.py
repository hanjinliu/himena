import sys
from app_model import Application
from himena.__main__ import main

def test_simple():
    sys.argv = ["himena"]
    try:
        main()
    finally:
        Application.destroy("default")
