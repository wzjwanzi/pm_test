$ErrorActionPreference = 'Stop'

Set-Location (Split-Path -Parent $PSScriptRoot)

Write-Host "== pytest =="
python -m pytest -v

Write-Host "== py_compile =="
python -m py_compile `
  app.py `
  desktop_app.py `
  desktop/main.py `
  desktop/controller.py `
  desktop/state.py `
  desktop/formatters.py `
  desktop/widgets/devices.py `
  desktop/widgets/cases.py `
  desktop/widgets/run_monitor.py `
  desktop/widgets/results.py `
  desktop/widgets/settings.py `
  pm_tests/core/models.py `
  pm_tests/core/facade.py

Write-Host "== flask smoke =="
python -c "from app import app; c=app.test_client(); r=c.get('/api/pm/templates'); print(r.status_code); print(r.get_json()['success'])"

Write-Host "== tk smoke =="
@'
import desktop_app
desktop_app._prepare_frozen_gui_environment()
desktop_app._import_tk_modules()
tk = desktop_app.tk
root = tk.Tk()
root.withdraw()
app = desktop_app.DesktopApp(root, start_polling=False)
root.update_idletasks()
print("panels=", all(hasattr(app, name) for name in ["devices_panel", "cases_panel", "run_monitor_panel", "results_panel", "settings_panel"]))
root.destroy()
'@ | python -
