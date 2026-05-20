"""Case library, ordered step builder, parameter editor, and queue panel."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Any

from desktop.case_models import SavedCase
from desktop.case_templates import ACTION_BY_ID, build_default_case_templates, remap_case_params_from_settings, step_from_template


GROUP_ORDER = ["通用", "基站 Web", "基站 SSH", "灌包服务器", "手机"]


class CasesPanel(ttk.LabelFrame):
    def __init__(self, parent, app):
        super().__init__(parent, text="用例构建")
        self.app = app
        self.saved_cases: list[SavedCase] = []
        self.selected_case: SavedCase | None = None
        self.step_templates: list[dict[str, Any]] = []
        self.case_templates: list[SavedCase] = []
        self._param_vars: dict[str, tk.Variable] = {}
        self._param_step_id = ""
        self.host_var = tk.StringVar(value="10.88.149.164")
        self.template_var = tk.StringVar(value="")

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.scroll_canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.scroll_canvas.yview)
        self.scroll_canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scroll_canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        self.content = ttk.Frame(self.scroll_canvas)
        self.content.columnconfigure(0, weight=1)
        self._content_window = self.scroll_canvas.create_window((0, 0), window=self.content, anchor="nw")
        self.content.bind("<Configure>", self._update_scroll_region)
        self.scroll_canvas.bind("<Configure>", self._resize_content)
        self.bind("<Enter>", self._bind_mousewheel)
        self.bind("<Leave>", self._unbind_mousewheel)

        self._build_case_library(self.content)
        self._build_step_builder(self.content)
        self._build_param_editor(self.content)

    def _build_case_library(self, parent) -> None:
        section = ttk.LabelFrame(parent, text="用例库")
        section.grid(row=0, column=0, sticky="nsew", padx=8, pady=(8, 6))
        section.columnconfigure(0, weight=1)
        section.rowconfigure(0, weight=1)

        self.case_list = tk.Listbox(section, height=7, exportselection=False)
        self.case_list.grid(row=0, column=0, columnspan=4, sticky="nsew", padx=6, pady=6)
        self.case_list.bind("<<ListboxSelect>>", self._on_case_select)

        ttk.Label(section, text="模板").grid(row=3, column=0, sticky="w", padx=3, pady=3)
        self.template_combo = ttk.Combobox(section, textvariable=self.template_var, state="readonly")
        self.template_combo.grid(row=3, column=1, columnspan=3, sticky="ew", padx=3, pady=3)

        ttk.Button(section, text="新建", command=self.create_blank_case).grid(row=1, column=0, sticky="ew", padx=3, pady=3)
        ttk.Button(section, text="从模板", command=self.create_case_from_template).grid(row=1, column=1, sticky="ew", padx=3, pady=3)
        ttk.Button(section, text="复制", command=self.copy_selected_case).grid(row=1, column=2, sticky="ew", padx=3, pady=3)
        ttk.Button(section, text="重命名", command=self.rename_selected_case).grid(row=1, column=3, sticky="ew", padx=3, pady=3)
        ttk.Button(section, text="删除", command=self.delete_selected_case).grid(row=2, column=0, sticky="ew", padx=3, pady=3)
        ttk.Button(section, text="保存", command=self.save_selected_case).grid(row=2, column=1, sticky="ew", padx=3, pady=3)
        ttk.Button(section, text="加入队列", command=self.add_selected_case_to_queue).grid(row=2, column=2, columnspan=2, sticky="ew", padx=3, pady=3)

    def _build_step_builder(self, parent) -> None:
        section = ttk.LabelFrame(parent, text="步骤顺序")
        section.grid(row=1, column=0, sticky="nsew", padx=8, pady=6)
        section.columnconfigure(0, weight=1)
        section.rowconfigure(0, weight=1)

        self.step_list = tk.Listbox(section, height=9, exportselection=False)
        self.step_list.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        self.step_list.bind("<<ListboxSelect>>", self._on_step_select)

        controls = ttk.Frame(section)
        controls.grid(row=0, column=1, sticky="ns", padx=(0, 6), pady=6)
        ttk.Button(controls, text="删除", command=self.delete_selected_step).grid(row=0, column=0, sticky="ew", pady=2)
        ttk.Button(controls, text="上移", command=self.move_step_up).grid(row=1, column=0, sticky="ew", pady=2)
        ttk.Button(controls, text="下移", command=self.move_step_down).grid(row=2, column=0, sticky="ew", pady=2)
        ttk.Button(controls, text="启用/禁用", command=self.toggle_step_enabled).grid(row=3, column=0, sticky="ew", pady=2)

        catalog = ttk.LabelFrame(section, text="添加步骤")
        catalog.grid(row=1, column=0, columnspan=2, sticky="ew", padx=6, pady=(0, 6))
        catalog.columnconfigure(0, weight=1)
        self.step_catalog = ttk.Notebook(catalog)
        self.step_catalog.grid(row=0, column=0, sticky="ew", padx=4, pady=4)

    def _build_param_editor(self, parent) -> None:
        section = ttk.LabelFrame(parent, text="步骤参数")
        section.grid(row=2, column=0, sticky="nsew", padx=8, pady=6)
        section.columnconfigure(0, weight=1)
        controls = ttk.Frame(section)
        controls.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 2))
        controls.columnconfigure(0, weight=1)
        ttk.Button(controls, text="从配置重新映射参数", command=self.remap_selected_case_params).grid(
            row=0,
            column=0,
            sticky="ew",
        )
        self.save_step_params_button = ttk.Button(
            controls,
            text="保存当前步骤参数",
            command=self.save_current_step_params,
        )
        self.save_step_params_button.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        self.step_params_frame = ttk.Frame(section)
        self.step_params_frame.grid(row=1, column=0, sticky="ew", padx=6, pady=(2, 6))

    def _build_queue(self, parent) -> None:
        section = ttk.LabelFrame(parent, text="用例队列")
        section.grid(row=3, column=0, sticky="nsew", padx=8, pady=(6, 8))
        section.columnconfigure(0, weight=1)
        section.rowconfigure(0, weight=1)
        self.queue_list = tk.Listbox(section, height=6, exportselection=False)
        self.queue_list.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        self.queue_list.bind("<<ListboxSelect>>", self._on_queue_select)
        ttk.Button(section, text="清空队列", command=self.app.clear_cases).grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 6))

    def set_templates(self, templates: list[dict]) -> None:
        settings = self._settings()
        self.step_templates = self.app.controller.get_step_templates()
        self.case_templates = self._normalize_case_templates(templates, settings)
        self._refresh_template_selector()
        self._render_step_catalog()
        self.refresh_cases()
        self.refresh_queue()

    def selected_template(self) -> dict | None:
        case = self._selected_template_case()
        if not case:
            return None
        return case.to_dict()

    def available_group_names(self) -> list[str]:
        names = {str(item.get("group", "")) for item in self.step_templates}
        return [name for name in GROUP_ORDER if name in names]

    def refresh_cases(self) -> None:
        try:
            self.saved_cases = list(self.app.controller.list_saved_cases())
        except Exception as exc:
            self.saved_cases = []
            self.app.set_message(f"加载用例库失败: {exc}")
        self.case_list.delete(0, tk.END)
        for case in self.saved_cases:
            self.case_list.insert(tk.END, f"{case.name}  ({len(case.steps)} 步)")
        if self.saved_cases:
            self.case_list.selection_set(0)
            self._select_case(0)

    def refresh_queue(self) -> None:
        if hasattr(self.app, "devices_panel"):
            self.app.devices_panel.refresh_queue()
            return
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

    def create_blank_case(self) -> None:
        name = simpledialog.askstring("新建用例", "用例名称", parent=self)
        if not name:
            return
        case = self.app.controller.create_blank_case(name.strip(), self._settings())
        self._after_case_changed(case.case_id, "已新建空白用例")

    def create_case_from_template(self) -> None:
        if not self.case_templates:
            self.app.set_message("没有可用用例模板")
            return
        names = [case.name for case in self.case_templates]
        name = simpledialog.askstring("从模板创建", "模板名称", initialvalue=names[0], parent=self)
        if not name:
            return
        if name not in names:
            messagebox.showerror("模板不存在", f"可用模板: {', '.join(names)}", parent=self)
            return
        case = self.app.controller.create_case_from_template(name, self._settings())
        self._after_case_changed(case.case_id, "已从模板创建用例")

    def copy_selected_case(self) -> None:
        case = self._current_case()
        if not case:
            return
        name = simpledialog.askstring("复制用例", "新用例名称", initialvalue=f"{case.name} copy", parent=self)
        if not name:
            return
        copied = self.app.controller.copy_case(case.case_id, name.strip())
        self._after_case_changed(copied.case_id, "已复制用例")

    def rename_selected_case(self) -> None:
        case = self._current_case()
        if not case:
            return
        name = simpledialog.askstring("重命名用例", "用例名称", initialvalue=case.name, parent=self)
        if not name:
            return
        renamed = self.app.controller.rename_case(case.case_id, name.strip())
        self._after_case_changed(renamed.case_id, "已重命名用例")

    def delete_selected_case(self) -> None:
        case = self._current_case()
        if not case:
            return
        if not messagebox.askyesno("删除用例", f"删除 {case.name}?", parent=self):
            return
        self.app.controller.delete_case(case.case_id)
        self.selected_case = None
        self._after_case_changed("", "已删除用例")

    def add_step(self, action_id: str) -> None:
        self.preview_step_template(action_id)
        case = self._current_case()
        if not case:
            self.app.set_message("请先选择或新建用例")
            return
        self._save_current_params()
        case.steps.append(step_from_template(action_id, self._settings()))
        self._render_steps(select_index=len(case.steps) - 1)

    def preview_step_template(self, action_id: str) -> None:
        try:
            step = step_from_template(action_id, self._settings())
        except Exception:
            return
        self._render_params(step, preview=True)

    def delete_selected_step(self) -> None:
        case, index = self._current_case_and_step_index()
        if case is None or index is None:
            return
        del case.steps[index]
        self._render_steps(select_index=min(index, len(case.steps) - 1))

    def move_step_up(self) -> None:
        self._save_current_params()
        case, index = self._current_case_and_step_index()
        if case is None or index is None or index == 0:
            return
        case.steps[index - 1], case.steps[index] = case.steps[index], case.steps[index - 1]
        self._render_steps(select_index=index - 1)

    def move_step_down(self) -> None:
        self._save_current_params()
        case, index = self._current_case_and_step_index()
        if case is None or index is None or index >= len(case.steps) - 1:
            return
        case.steps[index + 1], case.steps[index] = case.steps[index], case.steps[index + 1]
        self._render_steps(select_index=index + 1)

    def toggle_step_enabled(self) -> None:
        self._save_current_params()
        case, index = self._current_case_and_step_index()
        if case is None or index is None:
            return
        case.steps[index].enabled = not case.steps[index].enabled
        self._render_steps(select_index=index)

    def save_selected_case(self) -> None:
        case = self._current_case()
        if not case:
            return
        self._save_current_params()
        self.app.controller.save_case(case)
        self._after_case_changed(case.case_id, "已保存用例")

    def save_current_step_params(self) -> None:
        case, index = self._current_case_and_step_index()
        if case is None or index is None:
            self.app.set_message("请选择要保存参数的步骤")
            return
        self._save_current_params()
        self.app.controller.save_case(case)
        self._render_steps(select_index=index)
        if hasattr(self.app, "inspector_panel"):
            self.app.inspector_panel.render_case(case)
        self.app.set_message("当前步骤参数已保存")

    def add_selected_case_to_queue(self) -> None:
        case = self._current_case()
        if not case:
            self.app.set_message("请先选择用例")
            return
        self._save_current_params()
        self.app.state.add_case(case)
        self.refresh_queue()
        self.app.set_message(f"已加入队列: {case.name}")

    def remap_selected_case_params(self) -> None:
        case = self._current_case()
        if not case:
            self.app.set_message("请先选择用例")
            return
        self._save_current_params()
        changed = remap_case_params_from_settings(case, self._settings())
        self.app.controller.save_case(case)
        selection = self.step_list.curselection()
        self._render_steps(select_index=selection[0] if selection else -1)
        if hasattr(self.app, "inspector_panel"):
            self.app.inspector_panel.render_case(case)
        self.app.set_message(f"已从配置重新映射当前用例参数，更新 {changed} 项")

    def _render_step_catalog(self) -> None:
        for tab_id in self.step_catalog.tabs():
            self.step_catalog.forget(tab_id)
        for group in GROUP_ORDER:
            actions = [item for item in self.step_templates if item.get("group") == group]
            if not actions:
                continue
            frame = ttk.Frame(self.step_catalog)
            frame.columnconfigure(0, weight=1)
            self.step_catalog.add(frame, text=group)
            for row, item in enumerate(actions):
                label = str(item.get("label") or item.get("action"))
                action = str(item.get("action"))
                ttk.Button(frame, text=label, command=lambda action=action: self.add_step(action)).grid(
                    row=row,
                    column=0,
                    sticky="ew",
                    padx=4,
                    pady=2,
                )

    def _render_steps(self, *, select_index: int = -1) -> None:
        self.step_list.delete(0, tk.END)
        case = self._current_case()
        if not case:
            self._render_params(None)
            return
        for index, step in enumerate(case.steps, start=1):
            marker = " " if step.enabled else "x"
            self.step_list.insert(tk.END, f"{index}. [{marker}] {step.label}")
        if 0 <= select_index < len(case.steps):
            self.step_list.selection_set(select_index)
            self._render_params(case.steps[select_index])
        else:
            self._render_params(None)

    def _render_params(self, step, *, preview: bool = False) -> None:
        for child in self.step_params_frame.winfo_children():
            child.destroy()
        self._param_vars = {}
        self._param_step_id = "" if preview else getattr(step, "step_id", "")
        if step is None:
            ttk.Label(self.step_params_frame, text="选择一个步骤后编辑参数").grid(row=0, column=0, sticky="w")
            return

        template = ACTION_BY_ID.get(step.action)
        fields = list(template.fields if template else [])
        known = {field["name"] for field in fields}
        for key in step.params:
            if key not in known:
                fields.append({"name": key, "label": key, "type": "text"})

        for row, field in enumerate(fields):
            name = str(field["name"])
            ttk.Label(self.step_params_frame, text=str(field.get("label") or name)).grid(row=row, column=0, sticky="w", padx=(0, 6), pady=2)
            value = step.params.get(name, "")
            field_type = field.get("type")
            if field_type == "bool":
                var = tk.BooleanVar(value=bool(value))
                widget = ttk.Checkbutton(self.step_params_frame, variable=var)
            elif field_type == "choice":
                var = tk.StringVar(value=str(value or "FAPI1"))
                widget = ttk.Combobox(
                    self.step_params_frame,
                    textvariable=var,
                    values=list(field.get("choices") or ["FAPI1", "FAPI3"]),
                    state="readonly",
                )
            else:
                var = tk.StringVar(value=str(value))
                widget = ttk.Entry(self.step_params_frame, textvariable=var, show="*" if field_type == "password" else "")
            widget.grid(row=row, column=1, sticky="ew", pady=2)
            self.step_params_frame.columnconfigure(1, weight=1)
            self._param_vars[name] = var

    def _save_current_params(self) -> None:
        case = self._current_case()
        if not case or not self._param_step_id:
            return
        for step in case.steps:
            if step.step_id == self._param_step_id:
                for name, var in self._param_vars.items():
                    step.params[name] = var.get()
                return

    def _on_case_select(self, _event=None) -> None:
        selection = self.case_list.curselection()
        if selection:
            self._save_current_params()
            self._select_case(selection[0])

    def _on_step_select(self, _event=None) -> None:
        self._save_current_params()
        case, index = self._current_case_and_step_index()
        self._render_params(case.steps[index] if case is not None and index is not None else None)

    def _on_queue_select(self, _event=None) -> None:
        selection = self.queue_list.curselection()
        if selection:
            self.app.state.select_case(selection[0])

    def _select_case(self, index: int) -> None:
        if 0 <= index < len(self.saved_cases):
            self.selected_case = self.saved_cases[index]
            self._render_steps(select_index=0 if self.selected_case.steps else -1)
            if hasattr(self.app, "inspector_panel"):
                self.app.inspector_panel.render_case(self.selected_case)

    def _current_case(self) -> SavedCase | None:
        return self.selected_case

    def _current_case_and_step_index(self) -> tuple[SavedCase | None, int | None]:
        case = self._current_case()
        selection = self.step_list.curselection()
        if not case or not selection:
            return case, None
        index = selection[0]
        if not 0 <= index < len(case.steps):
            return case, None
        return case, index

    def _after_case_changed(self, case_id: str, message: str) -> None:
        self.refresh_cases()
        if case_id:
            for index, case in enumerate(self.saved_cases):
                if case.case_id == case_id:
                    self.case_list.selection_clear(0, tk.END)
                    self.case_list.selection_set(index)
                    self._select_case(index)
                    break
        self.app.set_message(message)

    def create_case_from_template(self) -> None:
        if not self.case_templates:
            self.app.set_message("没有可用用例模板")
            return
        selected = self._selected_template_case()
        if not selected:
            messagebox.showerror("模板不存在", "请选择可用模板", parent=self)
            return
        case = self.app.controller.create_case_from_template(selected.name, self._settings())
        self._after_case_changed(case.case_id, "已从模板创建用例")

    def _normalize_case_templates(self, templates: list[dict], settings: dict[str, Any]) -> list[SavedCase]:
        cases: list[SavedCase] = []
        for item in templates:
            if isinstance(item, dict) and item.get("steps"):
                cases.append(SavedCase.from_dict(item))
        return cases or build_default_case_templates(settings)

    def _refresh_template_selector(self) -> None:
        names = [case.name for case in self.case_templates]
        self.template_combo.configure(values=names)
        current = self.template_var.get()
        if names and current not in names:
            self.template_var.set(names[0])
        if not names:
            self.template_var.set("")

    def _selected_template_case(self) -> SavedCase | None:
        selected_name = self.template_var.get()
        for case in self.case_templates:
            if case.name == selected_name:
                return case
        return self.case_templates[0] if self.case_templates else None

    def _settings(self) -> dict[str, Any]:
        try:
            return self.app.controller.load_settings()
        except Exception:
            return {}

    def _update_scroll_region(self, _event=None) -> None:
        self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all"))

    def _resize_content(self, event) -> None:
        self.scroll_canvas.itemconfigure(self._content_window, width=event.width)

    def _bind_mousewheel(self, _event=None) -> None:
        for widget in (self, self.scroll_canvas, self.content):
            widget.bind("<MouseWheel>", self._on_mousewheel, add="+")

    def _unbind_mousewheel(self, _event=None) -> None:
        for widget in (self, self.scroll_canvas, self.content):
            widget.unbind("<MouseWheel>")

    def _on_mousewheel(self, event) -> None:
        widget = self.winfo_containing(event.x_root, event.y_root)
        if widget and self._should_scroll_outer(widget):
            self.scroll_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _should_scroll_outer(self, widget) -> bool:
        for blocked in (tk.Listbox, ttk.Combobox):
            if isinstance(widget, blocked):
                return False
        return str(widget).startswith(str(self))
