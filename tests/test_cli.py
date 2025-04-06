from pathlib import Path
import sys
import pytest
from himena.__main__ import main
from himena.profile import load_app_profile
from himena._cli.install import uninstall_outdated

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

def test_install_uninstall_local(sample_dir):
    plugin_path = sample_dir / "local_plugin.py"
    sys.argv = ["himena", "--install", str(plugin_path)]
    main()
    prof = load_app_profile("default")
    assert Path(plugin_path).resolve().as_posix() in prof.plugins
    with pytest.raises(FileNotFoundError):
        sys.argv = ["himena", "--install", str(plugin_path) + "xyz"]
        main()
    # just run again (no effect)
    sys.argv = ["himena", "--install", str(plugin_path)]
    main()
    assert prof.plugins == load_app_profile("default").plugins

    sys.argv = ["himena", "--uninstall", str(plugin_path)]
    main()
    prof = load_app_profile("default")
    assert Path(plugin_path).resolve().as_posix() not in prof.plugins

def test_uninstall_outdated():
    prof = load_app_profile(PROF_NAME)
    prof.plugins.append("himena_outdated_module")
    prof.plugins.append("himena_builtins.outdated_submodule")
    uninstall_outdated(PROF_NAME)
    prof = load_app_profile(PROF_NAME)
    assert "himena_outdated_module" not in prof.plugins
    assert "himena_builtins.outdated_submodule" not in prof.plugins
