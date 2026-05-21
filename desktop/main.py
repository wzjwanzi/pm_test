"""Tkinter desktop application shell."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from desktop.case_models import SavedCase
from desktop.case_templates import remap_case_params_from_settings
from desktop.controller import DesktopController
from desktop.state import CaseDraft, DesktopState, normalize_status
from desktop.widgets.cases import CasesPanel
from desktop.widgets.devices import DevicesPanel
from desktop.widgets.inspector import InspectorPanel
from desktop.widgets.results import ResultsPanel
from desktop.widgets.run_monitor import RunMonitorPanel
from desktop.widgets.settings import SettingsPanel


class DesktopApp:
    """Desktop workbench for PM automation."""

    def __init__(self, root, *, controller: DesktopController | None = None, start_polling: bool = True):
        self.root = root
        self.controller = controller or DesktopController()
        self.state = DesktopState()
        self._polling = start_polling
        self.root.title("基站自动化测试平台")
        self.root.geometry("1500x900")
        self.root.minsize(1200, 760)
        self._configure_styles()
        self._build_layout()
        self.load_templates()
        self.refresh_devices()
        self.refresh_runs()
        self.settings_panel.load()
        if start_polling:
            self._schedule_poll()

    def _configure_styles(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        self.root.configure(bg="#e9edf2")
        style.configure("Toolbar.TFrame", background="#1f5d99")
        style.configure(
            "ToolbarTitle.TLabel",
            background="#1f5d99",
            foreground="white",
            font=("Microsoft YaHei UI", 17, "bold"),
        )
        style.configure("Toolbar.TLabel", background="#1f5d99", foreground="white", font=("Microsoft YaHei UI", 9))
        style.configure("Workbench.TFrame", background="#e9edf2")
        style.configure("Compact.TButton", padding=(10, 3), font=("Microsoft YaHei UI", 9))
        style.configure("Treeview", rowheight=24, font=("Microsoft YaHei UI", 9))
        style.configure("Treeview.Heading", font=("Microsoft YaHei UI", 9, "bold"))

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)
        self._build_toolbar()

        body = ttk.Frame(self.root, style="Workbench.TFrame", padding=10)
        body.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        self.workbench = ttk.PanedWindow(body, orient=tk.HORIZONTAL)
        self.workbench.grid(row=0, column=0, sticky="nsew")

        self.left_pane = ttk.Frame(self.workbench)
        self.center_pane = ttk.Frame(self.workbench)
        self.right_pane = ttk.Frame(self.workbench)
        self.workbench.add(self.left_pane, weight=1)
        self.workbench.add(self.center_pane, weight=4)
        self.workbench.add(self.right_pane, weight=1)

        self.left_pane.columnconfigure(0, weight=1)
        self.left_pane.rowconfigure(0, weight=3)
        self.left_pane.rowconfigure(1, weight=1)
        self.center_pane.columnconfigure(0, weight=1)
        self.center_pane.rowconfigure(0, weight=3)
        self.center_pane.rowconfigure(1, weight=1)
        self.right_pane.columnconfigure(0, weight=1)
        self.right_pane.rowconfigure(0, weight=1)

        self.cases_panel = CasesPanel(self.left_pane, self)
        self.cases_panel.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        self.devices_panel = DevicesPanel(self.left_pane, self)
        self.devices_panel.grid(row=1, column=0, sticky="nsew")

        self.results_panel = ResultsPanel(self.center_pane, self)
        self.results_panel.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        self.run_monitor_panel = RunMonitorPanel(self.center_pane, self)
        self.run_monitor_panel.grid(row=1, column=0, sticky="nsew")

        self.inspector_panel = InspectorPanel(self.right_pane, self)
        self.inspector_panel.grid(row=0, column=0, sticky="nsew")
        self.settings_panel = SettingsPanel(self.right_pane, self)

    def _build_toolbar(self) -> None:
        self.toolbar = ttk.Frame(self.root, style="Toolbar.TFrame", padding=(14, 10))
        self.toolbar.grid(row=0, column=0, sticky="ew")
        self.toolbar.columnconfigure(20, weight=1)

        ttk.Label(self.toolbar, text="基站自动化测试平台", style="ToolbarTitle.TLabel").grid(
            row=0,
            column=0,
            rowspan=2,
            sticky="w",
            padx=(0, 28),
        )
        toolbar_actions = [
            ("刷新基站", self.refresh_devices),
            ("刷新案例", self.load_templates),
            ("新增用例", lambda: self.cases_panel.create_blank_case()),
            ("编辑用例", lambda: self.inspector_panel.render_case(self.cases_panel.selected_case)),
            ("删除用例", lambda: self.cases_panel.delete_selected_case()),
            ("FAQ帮助", lambda: self.set_message("FAQ帮助暂未接入")),
            ("版本说明", lambda: self.set_message("版本说明暂未接入")),
            ("打开配置", self.open_settings_window),
            ("打开案例", lambda: self.cases_panel.refresh_cases()),
            ("打开结果", self.open_selected_run_artifacts),
            ("新增基站", lambda: self.set_message("新增基站暂未接入")),
            ("删除基站", lambda: self.set_message("删除基站暂未接入")),
        ]
        for column, (text, command) in enumerate(toolbar_actions, start=1):
            ttk.Button(self.toolbar, text=text, command=command, style="Compact.TButton").grid(
                row=0,
                column=column,
                sticky="ew",
                padx=5,
            )

        self.message_var = tk.StringVar(value="")
        ttk.Label(self.toolbar, text="并发", style="Toolbar.TLabel").grid(row=1, column=1, sticky="e", padx=(0, 4), pady=(10, 0))
        self.concurrent_spin = ttk.Spinbox(self.toolbar, from_=1, to=20, width=5)
        self.concurrent_spin.set("1")
        self.concurrent_spin.grid(row=1, column=2, sticky="w", pady=(10, 0))
        ttk.Label(self.toolbar, text="Gatherlog等待(秒)", style="Toolbar.TLabel").grid(
            row=1,
            column=3,
            sticky="e",
            padx=(16, 4),
            pady=(10, 0),
        )
        self.wait_spin = ttk.Spinbox(self.toolbar, from_=0, to=9999, width=7)
        self.wait_spin.set("120")
        self.wait_spin.grid(row=1, column=4, sticky="w", pady=(10, 0))
        ttk.Button(self.toolbar, text="开始", command=self.start_run, style="Compact.TButton").grid(row=1, column=5, padx=(24, 0), pady=(10, 0))
        ttk.Button(self.toolbar, text="停止", command=self.stop_run, style="Compact.TButton").grid(row=1, column=6, padx=(5, 0), pady=(10, 0))
        self.header_status = ttk.Label(self.toolbar, text="状态: 空闲", style="Toolbar.TLabel")
        self.header_status.grid(row=1, column=7, sticky="w", padx=(14, 0), pady=(10, 0))
        ttk.Label(self.toolbar, textvariable=self.message_var, style="Toolbar.TLabel").grid(
            row=1,
            column=8,
            columnspan=10,
            sticky="w",
            padx=(20, 0),
            pady=(10, 0),
        )

    def set_message(self, text: str) -> None:
        self.state.message = text
        self.message_var.set(text)

    def open_settings_window(self) -> None:
        if hasattr(self, "settings_window") and self.settings_window.winfo_exists():
            self.settings_window.lift()
            return
        self.settings_window = tk.Toplevel(self.root)
        self.settings_window.title("运行配置")
        self.settings_window.geometry("820x620")
        self.settings_window.minsize(700, 500)
        self.settings_window.columnconfigure(0, weight=1)
        self.settings_window.rowconfigure(0, weight=1)
        self.active_settings_panel = SettingsPanel(self.settings_window, self)
        self.active_settings_panel.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.active_settings_panel.load()
        self.set_message("配置窗口已打开")

    def set_selected_device(self, device_id: str) -> None:
        self.set_selected_devices([device_id] if device_id else [])

    def set_selected_devices(self, device_ids: list[str]) -> None:
        self.state.set_selected_devices(device_ids)
        self.devices_panel.refresh_selected()
        self._refresh_header()

    def refresh_devices(self) -> None:
        try:
            devices = self.controller.refresh_devices()
            self.devices_panel.set_devices(devices)
            self.set_message(f"检测到 {len(devices)} 台设备")
        except Exception as exc:
            self.set_message(f"刷新设备失败: {exc}")

    def run_preflight(self) -> None:
        if not self.state.selected_device_id:
            self.set_message("请先选择设备")
            return
        try:
            result = self.controller.inspect_device(self.state.selected_device_id)
            self.devices_panel.set_preflight(result)
            self.set_message("预检完成")
        except Exception as exc:
            self.set_message(f"预检失败: {exc}")

    def load_templates(self) -> None:
        try:
            templates = self.controller.get_templates()
            self.cases_panel.set_templates(templates)
            self.inspector_panel.render_case(self.cases_panel.selected_case)
        except Exception as exc:
            self.set_message(f"加载模板失败: {exc}")

    def add_selected_template_case(self) -> None:
        template = self.cases_panel.selected_template()
        if template:
            self.add_case_from_template(template)

    def add_case_from_template(self, template: dict) -> None:
        if isinstance(template, dict) and template.get("steps"):
            case = SavedCase.from_dict(template)
            self.controller.save_case(case)
            self.state.add_case(case)
            self.cases_panel.refresh_queue()
            self.inspector_panel.render_case(case)
            self.set_message(f"已加入队列: {case.name}")
            return
        host = self.cases_panel.host_var.get().strip() or template.get("host") or "10.88.149.164"
        case = CaseDraft(
            name=str(template.get("name") or template.get("template_id") or "Ping Case"),
            host=host,
            count=int(template.get("count") or 5),
            capture_enabled=bool(template.get("capture_enabled", False)),
            ping_enabled=template.get("ping_enabled", True) is not False,
            server_action=str(template.get("server_action") or "none"),
        )
        self.state.add_case(case)
        self.cases_panel.refresh_queue()
        self.results_panel.render_case(case)
        self.inspector_panel.render_case(case)

    def clear_cases(self) -> None:
        self.state.clear_cases()
        self.cases_panel.refresh_queue()
        self.results_panel.render_case(None)
        self.inspector_panel.render_case(None)

    def start_run(self) -> None:
        devices = self.state.selected_device_ids or ([self.state.selected_device_id] if self.state.selected_device_id else [])
        if not devices:
            self.set_message("请先选择设备")
            return
        if not self._ensure_case_queue():
            return
        try:
            settings = self.controller.load_settings()
            for case in self.state.case_queue:
                if hasattr(case, "steps"):
                    remap_case_params_from_settings(case, settings)
                    self.controller.save_case(case)
            runs = self._create_runs_for_mode(devices)
            if not runs:
                self.set_message("没有可创建的任务")
                return
            self.state.selected_run_ids = [run.get("run_id", "") for run in runs if run.get("run_id")]
            self.state.selected_run_id = self.state.selected_run_ids[-1] if self.state.selected_run_ids else ""
            self.state.latest_run = runs[-1]
            self.results_panel.render_run(runs[-1])
            self.run_monitor_panel.render_run(runs[-1])
            self.inspector_panel.render_run(runs[-1])
            self.refresh_runs()
            self.set_message(f"任务已创建: {', '.join(self.state.selected_run_ids)}")
        except Exception as exc:
            self.set_message(f"创建任务失败: {exc}")

    def _ensure_case_queue(self) -> bool:
        if self.state.case_queue:
            return True
        selected_case = self.cases_panel.selected_case
        if selected_case:
            self.state.add_case(selected_case)
            self.cases_panel.refresh_queue()
            return True
        self.set_message("请先选择或加入用例")
        return False

    def _create_runs_for_mode(self, devices: list[str]) -> list[dict]:
        mode = self.devices_panel.run_mode_var.get()
        if mode == self.devices_panel.RUN_MODE_BY_CASE:
            grouped: dict[str, list] = {}
            for case in self.state.case_queue:
                assigned = self.state.case_devices(case) or devices
                for device_id in assigned:
                    grouped.setdefault(device_id, []).append(case)
            return [self._create_single_run(device_id, cases) for device_id, cases in grouped.items()]
        return [self._create_single_run(device_id, self.state.case_queue) for device_id in devices]

    def _create_single_run(self, device_id: str, cases) -> dict:
        result = self.controller.create_run(device_id, cases)
        return result.get("run", result)

    def stop_run(self) -> None:
        run_ids = self.state.selected_run_ids or ([self.state.selected_run_id] if self.state.selected_run_id else [])
        if not run_ids:
            self.set_message("没有选中的任务")
            return
        latest = None
        for run_id in run_ids:
            result = self.controller.request_stop(run_id)
            if result:
                latest = result
        if latest:
            self.state.latest_run = latest
            self.results_panel.render_run(latest)
            self.inspector_panel.render_run(latest)
            self.set_message("已请求停止任务")

    def refresh_runs(self) -> None:
        try:
            runs = self.controller.list_runs(limit=20)
            self.run_monitor_panel.set_runs(runs)
        except Exception as exc:
            self.set_message(f"刷新任务失败: {exc}")

    def load_run_detail(self, run_id: str) -> None:
        run = self.controller.get_run(run_id)
        if not run:
            self.set_message("未找到任务")
            return
        self.state.selected_run_id = run_id
        self.state.selected_run_ids = [run_id]
        self.state.latest_run = run
        self.results_panel.render_run(run)
        self.run_monitor_panel.render_run(run)
        self.inspector_panel.render_run(run)
        self._refresh_header()

    def export_selected_run_report(self) -> None:
        if not self.state.latest_run:
            self.set_message("没有选中的任务")
            return
        try:
            report_path = self.controller.export_run_report(self.state.latest_run)
            self.set_message(f"报告已导出: {report_path}")
        except Exception as exc:
            self.set_message(f"导出报告失败: {exc}")

    def open_selected_run_artifacts(self) -> None:
        if not self.state.latest_run:
            self.set_message("没有选中的任务")
            return
        try:
            artifact_dir = self.controller.open_artifact_dir(self.state.latest_run)
            self.set_message(f"已打开产物目录: {artifact_dir}")
        except Exception as exc:
            self.set_message(f"打开产物目录失败: {exc}")

    def _refresh_header(self) -> None:
        status = normalize_status(self.state.latest_run)
        devices = self.state.selected_device_ids or ([self.state.selected_device_id] if self.state.selected_device_id else [])
        run_ids = self.state.selected_run_ids or ([self.state.selected_run_id] if self.state.selected_run_id else [])
        self.header_status.configure(
            text=f"设备: {', '.join(devices) if devices else '-'} | 任务: {', '.join(run_ids) if run_ids else '-'} | 状态: {status}"
        )

    def _schedule_poll(self) -> None:
        if self.state.selected_run_id:
            self.load_run_detail(self.state.selected_run_id)
            self.refresh_runs()
        self.root.after(2000, self._schedule_poll)
