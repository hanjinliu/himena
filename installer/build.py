"""Build a stand-alone himena installer without conda.

The bundle is a relocatable CPython distribution (python-build-standalone) with
himena and its dependencies pip-installed into it. Because the bundle ships a
real Python interpreter and pip, ``himena --get <plugin>`` keeps working from
the installed application.

Usage
-----
    python installer/build.py                 # build everything for this platform
    python installer/build.py --skip-package  # only prepare the staging directory
    python installer/build.py --himena-spec himena==0.2.6  # bundle a PyPI release

Outputs (in ``installer/build/dist``):

- Windows: ``himena-<version>-windows-<arch>.exe`` (Inno Setup installer)
- macOS:   ``himena-<version>-macos-<arch>.dmg``
- Linux:   ``himena-<version>-linux-<arch>.tar.gz``

Only PySide6 (LGPL) is bundled as the Qt binding, so that the binary
distribution does not fall under the GPL terms of PyQt. The GPL-only Qt add-on
modules shipped in the PySide6 wheels are removed as well, and a
``THIRD_PARTY_LICENSES.txt`` listing every bundled distribution is generated.
"""

from __future__ import annotations

import argparse
import os
import platform
import plistlib
import shutil
import stat
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
RESOURCES = HERE / "resources"

# https://github.com/astral-sh/python-build-standalone/releases
PBS_TAG = "20260901"
PYTHON_VERSION = "3.13.15"
PBS_URL = "https://github.com/astral-sh/python-build-standalone/releases/download"

APP_NAME = "himena"
BUNDLE_ID = "io.github.hanjinliu.himena"
DEFAULT_EXTRAS = "pyside6,all"
# must match himena.profile.STANDALONE_MARKER
STANDALONE_MARKER = "himena-standalone"


# ----------------------------------------------------------------------------
# Platform helpers
# ----------------------------------------------------------------------------

IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")


def _arch() -> str:
    machine = platform.machine().lower()
    if machine in ("x86_64", "amd64"):
        return "x86_64"
    if machine in ("arm64", "aarch64"):
        return "aarch64"
    raise RuntimeError(f"Unsupported architecture: {machine}")


def _pbs_triple() -> str:
    arch = _arch()
    if IS_WINDOWS:
        return f"{arch}-pc-windows-msvc"
    if IS_MACOS:
        return f"{arch}-apple-darwin"
    if IS_LINUX:
        return f"{arch}-unknown-linux-gnu"
    raise RuntimeError(f"Unsupported platform: {sys.platform}")


def _python_exe(python_dir: Path) -> Path:
    if IS_WINDOWS:
        return python_dir / "python.exe"
    return python_dir / "bin" / "python3"


def _run(cmd: list[str | Path], **kwargs) -> None:
    print("+", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run([str(c) for c in cmd], check=True, **kwargs)


# ----------------------------------------------------------------------------
# Build steps
# ----------------------------------------------------------------------------


def fetch_python(python_version: str, pbs_tag: str, cache_dir: Path) -> Path:
    """Download the python-build-standalone tarball (cached)."""
    name = f"cpython-{python_version}+{pbs_tag}-{_pbs_triple()}-install_only_stripped.tar.gz"
    dest = cache_dir / name
    if dest.exists():
        print(f"Using cached {dest}")
        return dest
    cache_dir.mkdir(parents=True, exist_ok=True)
    url = f"{PBS_URL}/{pbs_tag}/{name}"
    print(f"Downloading {url}")
    tmp = dest.with_suffix(".part")
    with urllib.request.urlopen(url) as resp, tmp.open("wb") as f:
        shutil.copyfileobj(resp, f)
    tmp.replace(dest)
    return dest


def extract_python(tarball: Path, python_dir: Path) -> None:
    """Extract the tarball so that the interpreter lives in ``python_dir``."""
    if python_dir.exists():
        shutil.rmtree(python_dir)
    python_dir.parent.mkdir(parents=True, exist_ok=True)
    tmp = python_dir.parent / "_pbs_extract"
    if tmp.exists():
        shutil.rmtree(tmp)
    with tarfile.open(tarball) as tar:
        if hasattr(tarfile, "data_filter"):
            tar.extractall(tmp, filter="data")
        else:  # pragma: no cover
            tar.extractall(tmp)
    # the archive has a single top-level "python" directory
    (tmp / "python").rename(python_dir)
    shutil.rmtree(tmp)


def install_packages(python_dir: Path, himena_spec: str, extras: str) -> None:
    py = _python_exe(python_dir)
    env = os.environ.copy()
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "0"
    _run([py, "-m", "pip", "install", "--upgrade", "pip"], env=env)
    spec = f"{himena_spec}[{extras}]" if extras else himena_spec
    _run([py, "-m", "pip", "install", "--no-warn-script-location", spec], env=env)
    # sanity check: himena must import with PySide6 and nothing else
    _run(
        [
            py,
            "-c",
            "import himena, qtpy; assert qtpy.API_NAME == 'PySide6', qtpy.API_NAME; "
            "print('himena', himena.__version__, 'on', qtpy.API_NAME)",
        ],
        env=env,
    )


def get_version(python_dir: Path) -> str:
    out = subprocess.check_output(
        [
            str(_python_exe(python_dir)),
            "-c",
            "import himena; print(himena.__version__)",
        ],
        text=True,
    )
    return out.strip()


def _site_packages(python_dir: Path) -> Path:
    out = subprocess.check_output(
        [
            str(_python_exe(python_dir)),
            "-c",
            "import sysconfig; print(sysconfig.get_paths()['purelib'])",
        ],
        text=True,
    )
    return Path(out.strip())


def _rm(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def trim(python_dir: Path, keep_webengine: bool) -> None:
    """Remove files that are useless for the bundled application."""
    # standard library test suite
    if IS_WINDOWS:
        _rm(python_dir / "Lib" / "test")
    else:
        for p in (python_dir / "lib").glob("python3.*/test"):
            _rm(p)

    pyside_dir = _site_packages(python_dir) / "PySide6"
    if not pyside_dir.exists():
        return
    # Qt development tools (designer, linguist, ...) shipped with PySide6
    for p in pyside_dir.iterdir():
        if p.suffix == ".app" and p.is_dir():
            _rm(p)
        elif p.is_file() and (
            p.suffix == ".exe"
            or (p.suffix == "" and p.stat().st_mode & stat.S_IXUSR and not IS_WINDOWS)
        ):
            if not p.name.startswith("QtWebEngineProcess") or not keep_webengine:
                _rm(p)
    if not keep_webengine:
        # Qt WebEngine is a full Chromium; himena does not use it.
        for p in list(pyside_dir.rglob("*WebEngine*")):
            if p.exists():
                _rm(p)
        for pattern in (
            "resources",
            "Qt/resources",
            "translations/qtwebengine_locales",
            "Qt/translations/qtwebengine_locales",
        ):
            _rm(pyside_dir / pattern)


# Qt add-on modules that The Qt Company offers only under GPL-3.0 (or a
# commercial license), see the "Licenses" section of each module's docs.
# himena does not use any of them, and shipping them in a BSD-licensed
# bundle would raise GPL questions, so they are always removed.
GPL_ONLY_QT_MODULES = (
    "Charts",
    "DataVisualization",
    "Graphs",
    "Quick3D",
    "VirtualKeyboard",
    "Lottie",
    "QuickTimeline",
    "NetworkAuth",
    "HttpServer",
    "WaylandCompositor",
)


def remove_gpl_only_qt_modules(python_dir: Path) -> None:
    """Delete the GPL-only Qt modules (binaries, stubs, QML and plugins)."""
    pyside_dir = _site_packages(python_dir) / "PySide6"
    if not pyside_dir.exists():
        return
    needles = tuple(m.lower() for m in GPL_ONLY_QT_MODULES)
    removed = 0
    # walk top-down so that a matched directory is removed as a whole
    for root, dirs, files in os.walk(pyside_dir):
        root_path = Path(root)
        for name in list(dirs):
            if any(n in name.lower() for n in needles):
                _rm(root_path / name)
                dirs.remove(name)
                removed += 1
        for name in files:
            if any(n in name.lower() for n in needles):
                _rm(root_path / name)
                removed += 1
    print(f"Removed {removed} GPL-only Qt module files/directories")


def write_third_party_licenses(python_dir: Path, dest: Path) -> None:
    """Write a summary of the licenses of all bundled distributions.

    The PySide6 wheels ship without the LGPL text, so it is appended here to
    satisfy the LGPL notice requirement for the redistributed Qt libraries.
    """
    script = """
from importlib.metadata import distributions
rows = []
for d in distributions():
    md = d.metadata
    lic = md.get("License-Expression") or ""
    if not lic:
        lic = "; ".join(
            c.split("::")[-1].strip()
            for c in md.get_all("Classifier", [])
            if c.startswith("License ::")
        )
    if not lic and md.get("License"):
        lic = md.get("License").splitlines()[0]
    rows.append((md["Name"], d.version, lic or "(see package metadata)"))
for row in sorted(rows, key=lambda r: r[0].lower()):
    print("\t".join(row))
"""
    out = subprocess.check_output(
        [str(_python_exe(python_dir)), "-c", script], text=True
    )
    lines = [
        "THIRD-PARTY LICENSES",
        "====================",
        "",
        "This himena bundle contains a CPython interpreter (python-build-standalone,",
        "PSF-2.0) and the following Python distributions. The license of each",
        "distribution is listed as declared in its package metadata; the full texts",
        "are found in the corresponding *.dist-info directories under site-packages.",
        "",
        f"{'Distribution':<32}{'Version':<16}License",
        f"{'-' * 32}{'-' * 16}{'-' * 30}",
    ]
    for line in out.strip().splitlines():
        name, version, lic = line.split("\t")
        lines.append(f"{name:<32}{version:<16}{lic}")
    lines += [
        "",
        "Qt / PySide6 / shiboken6",
        "------------------------",
        "The Qt libraries bundled with PySide6 are used under the GNU Lesser General",
        "Public License version 3 (LGPL-3.0). The Qt add-on modules that are only",
        "available under the GPL (" + ", ".join(GPL_ONLY_QT_MODULES) + ") have been",
        "removed from this bundle. The Qt libraries are separate, dynamically loaded",
        "files inside site-packages/PySide6 and can be replaced by the user. Their",
        "source code is available at https://code.qt.io/ and on PyPI (sdist of",
        "PySide6). The LGPL-3.0 and GPL-3.0 texts follow.",
        "",
        "=" * 72,
        (RESOURCES / "LGPL-3.0.txt").read_text(encoding="utf-8"),
        "=" * 72,
        (RESOURCES / "GPL-3.0.txt").read_text(encoding="utf-8"),
    ]
    dest.write_text("\n".join(lines), encoding="utf-8")


def write_standalone_marker(app_root: Path) -> None:
    """Mark the bundle so that himena knows it runs from the stand-alone app.

    himena.profile looks for this file next to the bundled python directory
    (``Path(sys.prefix).parent``) and, when found, stores profiles and other
    user data in ``<app_root>/data`` instead of the platform user data directory.
    """
    (app_root / STANDALONE_MARKER).write_text(
        "This file marks the stand-alone himena bundle. Do not delete it.\n"
        "himena keeps its profiles and other user data in the 'data' directory\n"
        "next to this file.\n",
        encoding="utf-8",
    )


def _write_executable(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, newline="\n")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _find_vcvarsall() -> Path:
    """Locate vcvarsall.bat of the newest Visual Studio (or Build Tools)."""
    vswhere = (
        Path(os.environ.get("ProgramFiles(x86)", ""))
        / "Microsoft Visual Studio"
        / "Installer"
        / "vswhere.exe"
    )
    component = {
        "x86_64": "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
        "aarch64": "Microsoft.VisualStudio.Component.VC.Tools.ARM64",
    }[_arch()]
    install_path = ""
    if vswhere.exists():
        install_path = subprocess.check_output(
            [
                str(vswhere),
                "-latest",
                "-products",
                "*",
                "-requires",
                component,
                "-property",
                "installationPath",
            ],
            text=True,
        ).strip()
    vcvarsall = Path(install_path) / "VC" / "Auxiliary" / "Build" / "vcvarsall.bat"
    if not install_path or not vcvarsall.exists():
        raise FileNotFoundError(
            "MSVC (cl.exe) not found. Install the Visual Studio Build Tools with the "
            '"Desktop development with C++" workload (https://visualstudio.microsoft.com/'
            "visual-cpp-build-tools/) or run from a developer command prompt."
        )
    return vcvarsall


def _msvc_env() -> dict[str, str]:
    """Environment with the MSVC toolchain (cl.exe, rc.exe) on PATH."""
    if shutil.which("cl") and shutil.which("rc"):
        return os.environ.copy()
    vcvarsall = _find_vcvarsall()
    vc_arch = {"x86_64": "x64", "aarch64": "arm64"}[_arch()]
    # vcvarsall may print a harmless "vswhere.exe is not recognized" message
    out = subprocess.check_output(
        f'"{vcvarsall}" {vc_arch} >nul 2>&1 && set',
        shell=True,
        text=True,
        errors="replace",
    )
    env: dict[str, str] = {}
    for line in out.splitlines():
        key, sep, value = line.partition("=")
        if sep:
            env[key] = value
    return env


def _version_tuple(version: str) -> str:
    """'0.2.7.dev12' -> '0,2,7,0' (four numeric fields for VERSIONINFO)."""
    fields: list[int] = []
    for part in version.split("."):
        if not part.isdigit():
            break
        fields.append(int(part))
    fields = (fields + [0, 0, 0, 0])[:4]
    return ",".join(str(f) for f in fields)


def write_launchers_windows(stage: Path, version: str, build_dir: Path) -> None:
    """Compile resources/launcher.c into himena.exe (GUI) and bin/himena.exe."""
    env = _msvc_env()
    # environment variable names are case-insensitive on Windows ("Path")
    path = next((v for k, v in env.items() if k.upper() == "PATH"), "")
    cl = shutil.which("cl", path=path)
    rc = shutil.which("rc", path=path)
    if cl is None or rc is None:
        raise FileNotFoundError("cl.exe / rc.exe not found in the MSVC environment")

    work = build_dir / "launcher"
    work.mkdir(parents=True, exist_ok=True)
    rc_src = (
        (RESOURCES / "launcher.rc")
        .read_text()
        .replace("@ICON@", str(RESOURCES / "himena.ico").replace("\\", "\\\\"))
        .replace("@VERSION_COMMA@", _version_tuple(version))
        .replace("@VERSION@", version)
    )
    (work / "launcher.rc").write_text(rc_src)
    res = work / "launcher.res"
    _run([rc, "/nologo", "/fo", res, work / "launcher.rc"], env=env)

    (stage / "bin").mkdir(exist_ok=True)
    targets = [
        (stage / f"{APP_NAME}.exe", "WINDOWS", []),
        (stage / "bin" / f"{APP_NAME}.exe", "CONSOLE", ["/DHIMENA_CONSOLE"]),
    ]
    for exe, subsystem, defines in targets:
        _run(
            [
                cl,
                "/nologo",
                "/O1",
                "/W4",
                "/MT",
                "/DUNICODE",
                "/D_UNICODE",
                *defines,
                f"/Fo:{work / (subsystem.lower() + '.obj')}",
                f"/Fe:{exe}",
                RESOURCES / "launcher.c",
                res,
                "/link",
                f"/SUBSYSTEM:{subsystem}",
                "kernel32.lib",
                "user32.lib",
            ],
            env=env,
            cwd=work,
        )


def write_launchers_macos(app_dir: Path, version: str) -> None:
    contents = app_dir / "Contents"
    _write_executable(
        contents / "MacOS" / APP_NAME,
        "#!/bin/bash\n"
        'HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"\n'
        'exec "$HERE/../Resources/python/bin/python3" -m himena "$@"\n',
    )
    shutil.copy(RESOURCES / "himena.icns", contents / "Resources" / "himena.icns")
    info = {
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleIdentifier": BUNDLE_ID,
        "CFBundleVersion": version,
        "CFBundleShortVersionString": version,
        "CFBundleExecutable": APP_NAME,
        "CFBundleIconFile": "himena.icns",
        "CFBundlePackageType": "APPL",
        "CFBundleInfoDictionaryVersion": "6.0",
        "LSMinimumSystemVersion": "11.0",
        "NSHighResolutionCapable": True,
        "LSApplicationCategoryType": "public.app-category.developer-tools",
    }
    with (contents / "Info.plist").open("wb") as f:
        plistlib.dump(info, f)


def write_launchers_linux(stage: Path) -> None:
    _write_executable(
        stage / "bin" / APP_NAME,
        "#!/bin/bash\n"
        'HERE="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"\n'
        'exec "$HERE/../python/bin/python3" -m himena "$@"\n',
    )
    shutil.copy(RESOURCES / "himena.png", stage / "himena.png")
    shutil.copy(RESOURCES / "himena.desktop", stage / "himena.desktop")
    shutil.copy(HERE / "linux_install.sh", stage / "install.sh")
    (stage / "install.sh").chmod(0o755)


# ----------------------------------------------------------------------------
# Packaging
# ----------------------------------------------------------------------------


def _find_iscc() -> Path:
    if found := shutil.which("ISCC"):
        return Path(found)
    candidates = [
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Inno Setup 6",
        Path(os.environ.get("ProgramFiles", "")) / "Inno Setup 6",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6",
    ]
    for base in candidates:
        if (p := base / "ISCC.exe").exists():
            return p
    raise FileNotFoundError(
        "Inno Setup compiler (ISCC.exe) not found. Install it from "
        "https://jrsoftware.org/isinfo.php or run with --skip-package."
    )


def package_windows(stage: Path, dist: Path, version: str, build_dir: Path) -> Path:
    base_name = f"{APP_NAME}-{version}-windows-{_arch()}"
    template = (RESOURCES / "himena.iss").read_text()
    iss = (
        template.replace("@VERSION@", version)
        .replace("@STAGE_DIR@", str(stage))
        .replace("@OUTPUT_DIR@", str(dist))
        .replace("@OUTPUT_NAME@", base_name)
        .replace("@ICON@", str(RESOURCES / "himena.ico"))
        .replace("@LICENSE@", str(REPO_ROOT / "LICENSE"))
    )
    iss_path = build_dir / "himena.iss"
    iss_path.write_text(iss)
    _run([_find_iscc(), iss_path])
    return dist / f"{base_name}.exe"


def package_macos(app_dir: Path, dist: Path, version: str, build_dir: Path) -> Path:
    out = dist / f"{APP_NAME}-{version}-macos-{_arch()}.dmg"
    dmg_root = build_dir / "dmg_root"
    if dmg_root.exists():
        shutil.rmtree(dmg_root)
    dmg_root.mkdir(parents=True)
    shutil.copytree(app_dir, dmg_root / app_dir.name, symlinks=True)
    os.symlink("/Applications", dmg_root / "Applications")
    out.unlink(missing_ok=True)
    _run(
        [
            "hdiutil",
            "create",
            "-volname",
            APP_NAME,
            "-srcfolder",
            dmg_root,
            "-ov",
            "-format",
            "UDZO",
            out,
        ]
    )
    shutil.rmtree(dmg_root)
    return out


def package_linux(stage: Path, dist: Path, version: str) -> Path:
    base_name = f"{APP_NAME}-{version}-linux-{_arch()}"
    out = dist / f"{base_name}.tar.gz"
    out.unlink(missing_ok=True)
    with tarfile.open(out, "w:gz", compresslevel=6) as tar:
        tar.add(stage, arcname=base_name)
    return out


# ----------------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--python-version", default=PYTHON_VERSION)
    parser.add_argument("--pbs-tag", default=PBS_TAG)
    parser.add_argument(
        "--himena-spec",
        default=str(REPO_ROOT),
        help="pip requirement for himena (default: this repository).",
    )
    parser.add_argument("--extras", default=DEFAULT_EXTRAS)
    parser.add_argument("--build-dir", type=Path, default=HERE / "build")
    parser.add_argument("--keep-webengine", action="store_true")
    parser.add_argument("--no-trim", action="store_true")
    parser.add_argument(
        "--skip-install",
        action="store_true",
        help="Reuse the existing staging directory.",
    )
    parser.add_argument(
        "--skip-package",
        action="store_true",
        help="Stop after preparing the staging directory.",
    )
    args = parser.parse_args(argv)

    build_dir: Path = args.build_dir.resolve()
    cache_dir = build_dir / "cache"
    stage = build_dir / "stage"
    dist = build_dir / "dist"
    dist.mkdir(parents=True, exist_ok=True)

    if IS_MACOS:
        app_dir = stage / f"{APP_NAME}.app"
        python_dir = app_dir / "Contents" / "Resources" / "python"
    else:
        app_dir = stage
        python_dir = stage / "python"

    if not args.skip_install:
        if stage.exists():
            shutil.rmtree(stage)
        tarball = fetch_python(args.python_version, args.pbs_tag, cache_dir)
        extract_python(tarball, python_dir)
        install_packages(python_dir, args.himena_spec, args.extras)
        remove_gpl_only_qt_modules(python_dir)
        if not args.no_trim:
            trim(python_dir, keep_webengine=args.keep_webengine)

    version = get_version(python_dir)
    print(f"Bundled himena version: {version}")

    if IS_WINDOWS:
        write_launchers_windows(stage, version, build_dir)
        licenses_dir = stage
    elif IS_MACOS:
        write_launchers_macos(app_dir, version)
        licenses_dir = app_dir / "Contents" / "Resources"
    else:
        write_launchers_linux(stage)
        licenses_dir = stage
    shutil.copy(REPO_ROOT / "LICENSE", licenses_dir / "LICENSE.txt")
    write_third_party_licenses(python_dir, licenses_dir / "THIRD_PARTY_LICENSES.txt")
    write_standalone_marker(licenses_dir)

    # smoke test through the launcher
    if IS_WINDOWS:
        launcher = stage / "bin" / f"{APP_NAME}.exe"
    elif IS_MACOS:
        launcher = app_dir / "Contents" / "MacOS" / APP_NAME
    else:
        launcher = stage / "bin" / APP_NAME
    out = subprocess.check_output([str(launcher), "--version"], text=True)
    print(out.strip())
    if f"himena version: {version}" not in out:
        raise RuntimeError(f"Launcher smoke test failed: {out!r}")

    if args.skip_package:
        print(f"Staging directory ready: {stage}")
        return 0

    if IS_WINDOWS:
        out = package_windows(stage, dist, version, build_dir)
    elif IS_MACOS:
        out = package_macos(app_dir, dist, version, build_dir)
    else:
        out = package_linux(stage, dist, version)
    print(f"Created {out} ({out.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
