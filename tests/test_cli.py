import sys
from royalapp.__main__ import main

def test_simple():
    sys.argv = ["royalapp"]
    main()
