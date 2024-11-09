import sys
from himena.__main__ import main

def test_simple():
    sys.argv = ["himena"]
    main()
