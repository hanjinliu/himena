# Stand-alone installers

This directory builds stand-alone installers of himena that do not require a
pre-existing Python (and do not use conda).

## How it works

1. A relocatable CPython from
   [python-build-standalone](https://github.com/astral-sh/python-build-standalone)
   is downloaded (version pinned in `build.py`).
2. `himena[pyside6,all]` is pip-installed into that interpreter. Only
   **PySide6** (LGPL) is bundled; PyQt6 is GPL and must not be redistributed
   with a BSD-licensed application.
3. The Qt add-on modules that The Qt Company offers only under the GPL
   (Charts, DataVisualization, Graphs, Quick3D, VirtualKeyboard, Lottie,
   QuickTimeline, NetworkAuth, HttpServer, WaylandCompositor) are always
   removed. himena does not use them, and keeping them out means everything
   left in the bundle is under a permissive license or the LGPL. See
   `GPL_ONLY_QT_MODULES` in `build.py`.
4. Qt WebEngine (an entire Chromium, unused by himena) and the Qt developer
   tools are removed to shrink the bundle (`--keep-webengine` / `--no-trim`
   disable this).
5. `LICENSE.txt` (himena, BSD-3-Clause) and a generated
   `THIRD_PARTY_LICENSES.txt` (every bundled distribution with its declared
   license, plus the LGPL-3.0/GPL-3.0 texts required for redistributing the
   Qt libraries) are placed next to the launcher.
6. Small launchers are written and the tree is packaged:

   | Platform | Package                                  | Layout                                                 |
   |----------|------------------------------------------|--------------------------------------------------------|
   | Windows  | `himena-<ver>-windows-x86_64.exe` (Inno Setup) | `%LOCALAPPDATA%\Programs\himena\{himena.exe, python, bin\himena.exe}` |
   | macOS    | `himena-<ver>-macos-<arch>.dmg`          | `himena.app/Contents/Resources/python`                 |
   | Linux    | `himena-<ver>-linux-x86_64.tar.gz`       | `himena-<ver>-linux-x86_64/{python, bin/himena, install.sh}` |

   On Windows, `himena.exe` is a tiny native launcher compiled from
   `resources/launcher.c` (with the icon and version information from
   `resources/launcher.rc`) that runs `python\pythonw.exe -m himena`. Windows
   therefore shows "himena" instead of "python" in the "Open with" dialog,
   file associations and the Task Manager, and the installer registers it as
   an application (`HKCU\Software\Classes\Applications\himena.exe`) so that
   any file type can be opened with himena. `bin\himena.exe` is the same
   launcher built as a console application (for `himena --version` etc.).

7. A marker file `himena-standalone` is written next to the launcher (on macOS
   into `himena.app/Contents/Resources`). `himena.profile.is_standalone_app()`
   detects it and the application then keeps all of its user data (profiles,
   recent files, plugin data, ...) in a `data` directory next to the marker
   instead of the platform user data directory, so that the installation is
   self-contained.

Because the bundle contains a real interpreter with `pip`, plugins can still
be installed from the application (`himena --get <package>`), exactly as with
a pip-based installation. Plugins are installed into the bundled interpreter,
which is why the Windows installer defaults to a per-user, writable location.

## Building locally

```shell
python installer/build.py
```

Requirements: any Python 3.10+ to run the script (nothing else from the
repository is needed), network access, and

- Windows: [Inno Setup 6](https://jrsoftware.org/isinfo.php) (`ISCC.exe`) and
  MSVC for the `himena.exe` launcher (Visual Studio or the
  [Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
  with the "Desktop development with C++" workload; found via `vswhere`, or
  run from a developer command prompt)
- macOS: `hdiutil` (ships with macOS)
- Linux: nothing extra

Useful options:

- `--skip-package`: only build `installer/build/stage` (no Inno Setup / `hdiutil` needed)
- `--skip-install`: reuse the staging directory, only rewrite launchers/package
- `--himena-spec himena==0.2.6`: bundle a PyPI release instead of the checkout
- `--extras pyside6`: bundle fewer optional dependencies

## CI

`.github/workflows/installer.yml` builds all platforms on `v*` tags and
attaches the files to the GitHub release. It also runs on pull requests that
touch `installer/` (files are uploaded as workflow artifacts), and can be run
manually (`workflow_dispatch`).

## Known limitations

- The macOS app is not code-signed or notarized. Gatekeeper will refuse to open
  it until the quarantine attribute is removed:
  `xattr -cr /Applications/himena.app`.
- On Linux the bundle relies on the system Qt runtime libraries
  (libxcb, libGL, ...), like any pip-installed PySide6.
- Windows: the bundle contains deeply nested paths (e.g. `debugpy`), so
  installing into a very long directory path can fail with a `MoveFile` error
  when the 260-character limit is hit. The default location
  (`%LOCALAPPDATA%\Programs\himena`) is short enough.
