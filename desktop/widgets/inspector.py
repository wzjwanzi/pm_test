"""Right-side case summary and parameter inspector."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText


class InspectorPanel(ttk.LabelFrame):
    def __init__(self, parent, app):
        super().__init__(parent, text="测试案例与参数")
        self.app = app
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=2)

        summary_frame = ttk.LabelFrame(self, text="测试案例简要描述")
        summary_frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=(8, 6))
        summary_frame.columnconfigure(0, weight=1)
        summary_frame.rowconfigure(0, weight=1)
        self.case_summary = ScrolledText(summary_frame, height=10, wrap="word")
        self.case_summary.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)

        params_frame = ttk.LabelFrame(self, text="案例参数")
        params_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=(6, 8))
        params_frame.columnconfigure(0, weight=1)
        params_frame.rowconfigure(0, weight=1)
        columns = ("group", "param", "value")
        self.parameter_table = ttk.Treeview(params_frame, columns=columns, show="headings")
        for column, title, width in (
            ("group", "组号", 56),
            ("param", "参数", 140),
            ("value", "值", 220),
        ):
            self.parameter_table.heading(column, text=title)
            self.parameter_table.column(column, width=width, stretch=True, anchor="w")
        self.parameter_table.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=6)
        scrollbar = ttk.Scrollbar(params_frame, orient=tk.VERTICAL, command=self.parameter_table.yview)
        scrollbar.grid(row=0, column=1, sticky="ns", padx=(0, 6), pady=6)
        self.parameter_table.configure(yscrollcommand=scrollbar.set)
        self.render_case(None)

    def render_case(self, case) -> None:
        self.case_summary.delete("1.0", tk.END)
        self._clear_params()
        if case is None:
            self.case_summary.insert(tk.END, "请选择左侧案例后查看说明和参数。")
            return

        name = getattr(case, "name", "case")
        description = getattr(case, "description", "") or "未填写"
        steps = list(getattr(case, "steps", []) or [])
        self.case_summary.insert(tk.END, f"案例名称:\n{name}\n\n")
        self.case_summary.insert(tk.END, f"测试目的:\n{description}\n\n")
        self.case_summary.insert(tk.END, f"步骤数量:\n{len(steps)}\n")

        for index, step in enumerate(steps, start=1):
            label = getattr(step, "label", getattr(step, "action", f"step-{index}"))
            group = self._parameter_group(step)
            params = dict(getattr(step, "params", {}) or {})
            if not params:
                self.parameter_table.insert("", tk.END, values=(group, label, ""))
                continue
            for key, value in params.items():
                self.parameter_table.insert("", tk.END, values=(group, key, value))

    def render_run(self, _run: dict | None) -> None:
        return

    def _clear_params(self) -> None:
        for item in self.parameter_table.get_children():
            self.parameter_table.delete(item)

    def _parameter_group(self, step) -> str:
        action = str(getattr(step, "action", ""))
        label = str(getattr(step, "label", ""))
        if action.startswith("base_") or label.startswith("基站"):
            return "基站"
        if action.startswith("traffic_server_") or "灌包服务器" in label:
            return "灌包"
        if action.startswith("phone_") or label.startswith("手机"):
            return "手机"
        return "其他"
