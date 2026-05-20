"""Result and raw JSON inspector panel."""
from __future__ import annotations

from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from desktop.formatters import format_raw_json, format_run_console


class ResultsPanel(ttk.LabelFrame):
    def __init__(self, parent, app):
        super().__init__(parent, text="结果与详情")
        self.app = app
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        actions = ttk.Frame(self)
        actions.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        ttk.Button(actions, text="导出报告", command=app.export_selected_run_report).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(actions, text="打开产物", command=app.open_selected_run_artifacts).grid(row=0, column=1, padx=(0, 6))
        self.summary_text = ScrolledText(self, height=18, wrap="word")
        self.summary_text.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)
        self.raw_text = ScrolledText(self, height=8, wrap="none")
        self.raw_text.grid(row=2, column=0, sticky="nsew", padx=8, pady=(4, 8))
        self._last_summary = ""
        self._last_raw = ""

    def render_run(self, run: dict | None) -> None:
        summary = format_run_console(run)
        raw = format_raw_json(run)
        if summary == self._last_summary and raw == self._last_raw:
            return
        summary_y = self.summary_text.yview()[0] if self.summary_text.winfo_exists() else 0.0
        raw_y = self.raw_text.yview()[0] if self.raw_text.winfo_exists() else 0.0
        self.summary_text.delete("1.0", "end")
        self.summary_text.insert("end", summary)
        self.summary_text.yview_moveto(summary_y)
        self.raw_text.delete("1.0", "end")
        self.raw_text.insert("end", raw)
        self.raw_text.yview_moveto(raw_y)
        self._last_summary = summary
        self._last_raw = raw

    def render_case(self, case) -> None:
        self._last_summary = ""
        self._last_raw = ""
        self.summary_text.delete("1.0", "end")
        if case is None:
            self.summary_text.insert("end", "No case selected.")
            return
        self.summary_text.insert(
            "end",
            f"Case: {case.name}\nHost: {case.host}\nAction: {case.server_action}\nPing: {case.ping_enabled}\nCapture: {case.capture_enabled}",
        )
