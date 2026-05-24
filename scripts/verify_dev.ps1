$ErrorActionPreference = 'Stop'

Set-Location (Split-Path -Parent $PSScriptRoot)

Write-Host "== pytest =="
python -m pytest -v

Write-Host "== py_compile =="
python -m py_compile `
  app.py `
  desktop_app.py `
  desktop/controller.py `
  desktop/state.py `
  desktop/formatters.py `
  desktop_qt/app.py `
  desktop_qt/main_window.py `
  desktop_qt/pages/home.py `
  desktop_qt/pages/case_library.py `
  desktop_qt/pages/settings.py `
  desktop_qt/pages/results.py `
  desktop_qt/pages/devices.py `
  pm_tests/core/models.py `
  pm_tests/core/facade.py

Write-Host "== flask smoke =="
python -c "from app import app; c=app.test_client(); r=c.get('/api/pm/templates'); print(r.status_code); print(r.get_json()['success'])"

Write-Host "== qt smoke =="
@'
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
from desktop_qt.main_window import MainWindow
app = QApplication.instance() or QApplication([])
window = MainWindow(start_polling=False)
print("pages=", window.stack.count())
window.close()
'@ | python -
