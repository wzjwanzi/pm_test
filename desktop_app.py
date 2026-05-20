"""Native desktop entrypoint for the mobile automation platform."""
from __future__ import annotations

import logging
import os
from pathlib import Path
import sys
from typing import Any

from desktop.main import DesktopApp


tk: Any = None
ttk: Any = None
messagebox: Any = None
scrolledtext: Any = None


def _configure_logging() -> Path:
    if getattr(sys, "frozen", False):
        log_dir = Path(sys.executable).resolve().parent
    else:
        log_dir = Path(__file__).resolve().parent

    log_path = log_dir / "desktop_app.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
        ],
        force=True,
    )
    return log_path


def _prepare_frozen_gui_environment() -> None:
    if not getattr(sys, "frozen", False):
        _prepare_local_tk_environment()
        return

    exe_dir = Path(sys.executable).resolve().parent
    for root in (exe_dir / "_internal", exe_dir):
        _add_runtime_root(root)


def _prepare_local_tk_environment() -> None:
    base_dir = Path(__file__).resolve().parent
    for root in (
        base_dir / "release" / "MobileTestPlatform" / "_internal",
        base_dir / "release_fixed" / "MobileTestPlatform" / "_internal",
        base_dir / "release_ui_review" / "MobileTestPlatform" / "_internal",
    ):
        if root.exists():
            _add_runtime_root(root)
            break


def _add_runtime_root(root: Path) -> None:
    if not root.exists():
        return

    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)

    try:
        os.add_dll_directory(root_str)
    except (AttributeError, FileNotFoundError):
        pass

    tcl_library = root / "_tcl_data"
    tk_library = root / "_tk_data"
    if not tcl_library.exists():
        tcl_library = root / "tcl" / "tcl8.6"
    if not tk_library.exists():
        tk_library = root / "tcl" / "tk8.6"
    if tcl_library.exists():
        os.environ.setdefault("TCL_LIBRARY", str(tcl_library))
    if tk_library.exists():
        os.environ.setdefault("TK_LIBRARY", str(tk_library))


def _import_tk_modules() -> None:
    global tk, ttk, messagebox, scrolledtext
    import tkinter as _tk
    from tkinter import messagebox as _messagebox
    from tkinter import scrolledtext as _scrolledtext
    from tkinter import ttk as _ttk

    tk = _tk
    ttk = _ttk
    messagebox = _messagebox
    scrolledtext = _scrolledtext


def main() -> None:
    log_path = _configure_logging()
    logging.info("Desktop application startup. frozen=%s", getattr(sys, "frozen", False))
    try:
        _prepare_frozen_gui_environment()
        _import_tk_modules()
        root = tk.Tk()
        DesktopApp(root)
        logging.info("Desktop application entering main loop.")
        root.mainloop()
    except Exception as exc:
        logging.exception("Desktop application startup failed.")
        try:
            if messagebox is not None:
                messagebox.showerror(
                    "启动失败",
                    f"桌面程序启动失败：{exc}\n\n日志文件：{log_path}",
                )
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
