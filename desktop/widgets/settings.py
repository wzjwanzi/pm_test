"""Runtime settings panel."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText

import config
from desktop.settings_forms import (
    MODULE_FIELDS,
    MODULE_LABELS,
    SettingsValidationError,
    extract_business_modules,
    merge_all_business_modules,
    merge_business_module,
)


class SettingsPanel(ttk.LabelFrame):
    def __init__(self, parent, app):
        super().__init__(parent, text="运行配置")
        self.app = app
        self.module_order = list(MODULE_FIELDS)
        self.field_vars: dict[str, dict[str, tk.Variable]] = {}
        self.text_widgets: dict[str, dict[str, ScrolledText]] = {}

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        controls = ttk.Frame(self)
        controls.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        ttk.Button(controls, text="重新读取", command=self.load).grid(row=0, column=0, padx=(0, 6))
        self.save_current_button = ttk.Button(controls, text="保存当前模块", command=self.save_current_group)
        self.save_current_button.grid(
            row=0,
            column=1,
            padx=(0, 6),
        )
        ttk.Button(controls, text="保存全部", command=self.save).grid(row=0, column=2, padx=(0, 6))
        ttk.Button(controls, text="恢复默认", command=self.reset).grid(row=0, column=3, padx=(0, 6))

        self.notebook = ttk.Notebook(self)
        self.notebook.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        for module in self.module_order:
            self._build_module_tab(module)

    def _build_module_tab(self, module: str) -> None:
        tab = ttk.Frame(self.notebook)
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(0, weight=1)

        canvas = tk.Canvas(tab, highlightthickness=0)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        frame = ttk.Frame(canvas, padding=8)
        frame.columnconfigure(1, weight=1)
        window_id = canvas.create_window((0, 0), window=frame, anchor="nw")
        frame.bind(
            "<Configure>",
            lambda _event, scroll_canvas=canvas: scroll_canvas.configure(
                scrollregion=scroll_canvas.bbox("all")
            ),
        )
        canvas.bind(
            "<Configure>",
            lambda event, scroll_canvas=canvas, item=window_id: scroll_canvas.itemconfigure(
                item,
                width=event.width,
            ),
        )
        on_mousewheel = self._bind_mousewheel(canvas, frame)

        self.field_vars[module] = {}
        self.text_widgets[module] = {}

        for row, field in enumerate(MODULE_FIELDS[module]):
            label = ttk.Label(frame, text=field.label)
            label.grid(row=row, column=0, sticky="w", padx=(0, 8), pady=3)
            self._bind_widget_mousewheel(label, on_mousewheel)
            if field.kind == "bool":
                var = tk.BooleanVar(value=False)
                widget = ttk.Checkbutton(frame, variable=var)
            elif field.kind == "choice":
                var = tk.StringVar(value=field.choices[0] if field.choices else "")
                widget = ttk.Combobox(
                    frame,
                    textvariable=var,
                    values=list(field.choices),
                    state="readonly",
                )
            elif field.kind == "multiline":
                widget = ScrolledText(frame, height=4, wrap="word")
                widget.grid(row=row, column=1, sticky="ew", pady=3)
                self.text_widgets[module][field.key] = widget
                continue
            else:
                var = tk.StringVar(value="")
                widget = ttk.Entry(frame, textvariable=var)

            widget.grid(row=row, column=1, sticky="ew", pady=3)
            self._bind_widget_mousewheel(widget, on_mousewheel)
            self.field_vars[module][field.key] = var

        self.notebook.add(tab, text=MODULE_LABELS[module])

    def load(self) -> None:
        try:
            settings = self.app.controller.load_settings()
            modules = extract_business_modules(settings)
            for module, values in modules.items():
                self._set_module_values(module, values)
        except Exception as exc:  # Tk callbacks should report controller errors, not escape.
            self._show_controller_error("读取配置", exc)

    def save_group(self, module: str) -> None:
        try:
            settings = self.app.controller.load_settings()
            values = self._collect_module_values(module)
            saved = self.app.controller.save_settings(merge_business_module(settings, module, values))
            self._set_module_values(module, extract_business_modules(saved)[module])
        except SettingsValidationError as exc:
            messagebox.showerror("配置格式错误", str(exc), parent=self)
            return
        except Exception as exc:  # Tk callbacks should report controller errors, not escape.
            self._show_controller_error(f"保存{MODULE_LABELS.get(module, module)}配置", exc)
            return

        self.app.set_message(
            f"{MODULE_LABELS[module]}配置已保存: {self._settings_path_text()}"
        )

    def save_current_group(self) -> None:
        current_tab = self.notebook.select()
        current_index = self.notebook.index(current_tab)
        self.save_group(self.module_order[current_index])

    def save(self) -> None:
        try:
            settings = self.app.controller.load_settings()
            values = {
                module: self._collect_module_values(module)
                for module in self.module_order
            }
            saved = self.app.controller.save_settings(merge_all_business_modules(settings, values))
            modules = extract_business_modules(saved)
            for module, module_values in modules.items():
                self._set_module_values(module, module_values)
        except SettingsValidationError as exc:
            messagebox.showerror("配置格式错误", str(exc), parent=self)
            return
        except Exception as exc:  # Tk callbacks should report controller errors, not escape.
            self._show_controller_error("保存全部配置", exc)
            return

        self.app.set_message(f"配置已全部保存: {self._settings_path_text()}")

    def reset(self) -> None:
        if not messagebox.askyesno(
            "恢复默认配置",
            f"确认将全部运行配置恢复为默认值？\n\n{self._settings_path_text()}",
            parent=self,
        ):
            return
        try:
            settings = self.app.controller.reset_settings()
            modules = extract_business_modules(settings)
            for module, values in modules.items():
                self._set_module_values(module, values)
        except Exception as exc:  # Tk callbacks should report controller errors, not escape.
            self._show_controller_error("恢复默认配置", exc)
            return
        self.app.set_message(f"配置已恢复默认: {self._settings_path_text()}")

    def _set_module_values(self, module: str, values: dict) -> None:
        fields = {field.key: field for field in MODULE_FIELDS[module]}
        for key, var in self.field_vars.get(module, {}).items():
            field = fields[key]
            var.set(self._field_value_or_default(field, values.get(key)))
        for key, widget in self.text_widgets.get(module, {}).items():
            field = fields[key]
            widget.delete("1.0", "end")
            widget.insert("end", str(self._field_value_or_default(field, values.get(key))))

    def _collect_module_values(self, module: str) -> dict:
        values = {
            key: var.get()
            for key, var in self.field_vars.get(module, {}).items()
        }
        for key, widget in self.text_widgets.get(module, {}).items():
            values[key] = widget.get("1.0", "end").strip()
        return values

    def _settings_path_text(self) -> str:
        return str(config.SETTINGS_FILE)

    def _field_value_or_default(self, field, value):
        if value is not None:
            return value
        if field.kind == "bool":
            return False
        if field.kind == "choice":
            return field.choices[0] if field.choices else ""
        return ""

    def _show_controller_error(self, action: str, exc: Exception) -> None:
        messagebox.showerror(
            "配置操作失败",
            f"{action}失败: {self._settings_path_text()}\n{exc}",
            parent=self,
        )

    def _bind_mousewheel(self, canvas: tk.Canvas, frame: ttk.Frame):
        def on_mousewheel(event):
            if event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")
            else:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            canvas.bind(sequence, on_mousewheel, add="+")
            frame.bind(sequence, on_mousewheel, add="+")
        return on_mousewheel

    def _bind_widget_mousewheel(self, widget, callback) -> None:
        for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            widget.bind(sequence, callback, add="+")
