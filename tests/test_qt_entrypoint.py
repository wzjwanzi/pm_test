def test_desktop_app_imports_qt_entrypoint():
    import desktop_app

    assert callable(desktop_app.main)
