"""Device and preflight panel."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class DevicesPanel(ttk.LabelFrame):
    def __init__(self, parent, app):
        super().__init__(parent, text="设备与预检")
        self.app = app
        self.columnconfigure(0, weight=1)
        ttk.Button(self, text="刷新设备", command=app.refresh_devices).grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        ttk.Button(self, text="执行预检", command=app.run_preflight).grid(row=1, column=0, sticky="ew", padx=8, pady=4)
        self.device_list = tk.Listbox(self, height=7, exportselection=False)
        self.device_list.grid(row=2, column=0, sticky="nsew", padx=8, pady=4)
        self.device_list.bind("<<ListboxSelect>>", self._on_select)
        self.selected_label = ttk.Label(self, text="当前设备: -")
        self.selected_label.grid(row=3, column=0, sticky="w", padx=8, pady=4)
        queue_frame = ttk.LabelFrame(self, text="用例队列")
        queue_frame.grid(row=4, column=0, sticky="nsew", padx=8, pady=(4, 8))
        queue_frame.columnconfigure(0, weight=1)
        queue_frame.rowconfigure(0, weight=1)
        self.queue_list = tk.Listbox(queue_frame, height=8, exportselection=False)
        self.queue_list.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        self.queue_list.bind("<<ListboxSelect>>", self._on_queue_select)
        ttk.Button(queue_frame, text="清空队列", command=app.clear_cases).grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 6))
        self.rowconfigure(4, weight=1)

    def set_devices(self, devices: list[str]) -> None:
        self.device_list.delete(0, tk.END)
        for item in devices:
            self.device_list.insert(tk.END, item)
        if devices and not self.app.state.selected_device_id:
            self.device_list.selection_set(0)
            self.app.set_selected_device(devices[0])

    def set_preflight(self, data: dict) -> None:
        status = "通过" if data.get("success") else "失败"
        self.app.set_message(f"预检{status}: {data.get('device_id') or self.app.state.selected_device_id or '-'}")

    def refresh_selected(self) -> None:
        self.selected_label.configure(text=f"当前设备: {self.app.state.selected_device_id or '-'}")

    def _on_select(self, _event=None) -> None:
        selection = self.device_list.curselection()
        if selection:
            self.app.set_selected_device(self.device_list.get(selection[0]))

    def refresh_queue(self) -> None:
        self.queue_list.delete(0, tk.END)
        for index, item in enumerate(self.app.state.case_queue, start=1):
            name = getattr(item, "name", "case")
            step_count = len(getattr(item, "steps", []) or [])
            if step_count:
                text = f"{index}. {name} | {step_count} 步"
            else:
                text = f"{index}. {name}"
            self.queue_list.insert(tk.END, text)
        if 0 <= self.app.state.selected_case_index < self.queue_list.size():
            self.queue_list.selection_clear(0, tk.END)
            self.queue_list.selection_set(self.app.state.selected_case_index)

    def _on_queue_select(self, _event=None) -> None:
        selection = self.queue_list.curselection()
        if selection:
            self.app.state.select_case(selection[0])
