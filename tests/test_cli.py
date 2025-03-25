import sys
import pytest
from himena.__main__ import main

def test_simple():
    sys.argv = ["himena"]
    main()

PROF_NAME = "test"

def test_new_profile():
    sys.argv = ["himena", "--new", PROF_NAME]
    main()
    with pytest.raises(ValueError):
        sys.argv = ["himena", PROF_NAME, "--new", "xyz"]
        main()
    sys.argv = ["himena", "--remove", PROF_NAME]
    main()

def test_list_plugins():
    sys.argv = ["himena", "--new", PROF_NAME]
    main()
    sys.argv = ["himena", "--list-plugins"]
    main()
    sys.argv = ["himena", PROF_NAME, "--list-plugins"]
    main()
    sys.argv = ["himena", PROF_NAME, "--install", "himena_builtins"]
    main()
    sys.argv = ["himena", PROF_NAME, "--install", "himena_builtins.io"]
    main()
    sys.argv = ["himena", PROF_NAME, "--uninstall", "himena_builtins"]
    main()
    sys.argv = ["himena", PROF_NAME, "--uninstall", "himena_builtins.qt.widgets"]
    main()

def test_install_uninstall():
    sys.argv = ["himena", "--uninstall", "himena-builtins"]
    main()
    sys.argv = ["himena", "--install", "himena-builtins"]
    main()
    sys.argv = ["himena", "--uninstall", "himena_builtins.new"]
    main()
    sys.argv = ["himena", "--install", "himena_builtins.new"]
    main()
