"""Run controls and timeline panel."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from desktop.formatters import extract_step_rows


class RunMonitorPanel(ttk.LabelFrame):
    def __init__(self, parent, app):
        super().__init__(parent, text="任务执行")
        self.app = app
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        controls = ttk.Frame(self)
        controls.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        for index, (text, command) in enumerate(
            [
                ("开始执行", app.start_run),
                ("停止", app.stop_run),
                ("刷新", app.refresh_runs),
            ]
        ):
            ttk.Button(controls, text=text, command=command).grid(row=0, column=index, padx=(0, 6))
        self.history = tk.Listbox(self, height=6, exportselection=False)
        self.history.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
        self.history.bind("<<ListboxSelect>>", self._on_history_select)
        columns = ("case", "step", "adapter", "status", "message", "error")
        self.steps = ttk.Treeview(self, columns=columns, show="headings", height=14)
        for column in columns:
            self.steps.heading(column, text=column)
            self.steps.column(column, width=110, stretch=True)
        self.steps.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.runs: list[dict] = []

    def set_runs(self, runs: list[dict]) -> None:
        self.runs = runs
        self.history.delete(0, tk.END)
        for item in runs:
            summary = item.get("summary") or {}
            self.history.insert(
                tk.END,
                f"{item.get('run_id', '-')} | {item.get('status') or item.get('state') or '-'} | {summary.get('passed', 0)}/{summary.get('total', 0)}",
            )

    def render_run(self, run: dict | None) -> None:
        for item in self.steps.get_children():
            self.steps.delete(item)
        for row in extract_step_rows(run):
            self.steps.insert(
                "",
                tk.END,
                values=(row["case"], row["step"], row["adapter"], row["status"], row["message"], row["error"]),
            )

    def _on_history_select(self, _event=None) -> None:
        selection = self.history.curselection()
        if selection:
            run = self.runs[selection[0]]
            run_id = run.get("run_id")
            if run_id:
                self.app.load_run_detail(run_id)
