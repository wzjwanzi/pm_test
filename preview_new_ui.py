"""Launch the standalone redesigned desktop UI preview."""
from desktop_app import _prepare_local_tk_environment
from desktop.ui_preview import main


if __name__ == "__main__":
    _prepare_local_tk_environment()
    main()
