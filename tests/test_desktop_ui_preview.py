import tkinter as tk


def test_desktop_ui_preview_builds_three_column_workbench():
    import desktop_app

    desktop_app._prepare_local_tk_environment()

    from desktop.ui_preview import DesktopWorkbenchPreview

    root = tk.Tk()
    root.withdraw()
    try:
        preview = DesktopWorkbenchPreview(root)
        root.update_idletasks()

        assert hasattr(preview, "toolbar")
        assert hasattr(preview, "case_tree")
        assert hasattr(preview, "station_table")
        assert hasattr(preview, "realtime_log")
        assert hasattr(preview, "step_table")
        assert hasattr(preview, "case_summary")
        assert hasattr(preview, "parameter_table")
    finally:
        root.destroy()
