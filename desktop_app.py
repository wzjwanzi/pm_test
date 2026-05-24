"""Native desktop entrypoint for the mobile automation platform."""
from __future__ import annotations

import logging
import os
from pathlib import Path
import sys


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
    exe_dir = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    for root in (exe_dir / "_internal", exe_dir):
        _add_runtime_root(root)


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


def main() -> None:
    log_path = _configure_logging()
    logging.info("Desktop application startup. frozen=%s", getattr(sys, "frozen", False))
    try:
        _prepare_frozen_gui_environment()
        from desktop_qt.app import main as qt_main

        logging.info("Desktop application entering main loop.")
        qt_main()
    except Exception as exc:
        logging.exception("Desktop application startup failed.")
        logging.error("Startup failed. See log file: %s", log_path)
        raise


if __name__ == "__main__":
    main()
