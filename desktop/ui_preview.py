"""Standalone preview for the redesigned desktop workbench UI."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText


class DesktopWorkbenchPreview:
    """Reference-style preview window for the next desktop UI."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("自动化测试平台 - 新UI预览")
        self.root.geometry("1500x900")
        self.root.minsize(1200, 760)
        self._configure_styles()
        self._build()
        self._load_mock_data()

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
        style.configure(
            "Toolbar.TLabel",
            background="#1f5d99",
            foreground="white",
            font=("Microsoft YaHei UI", 9),
        )
        style.configure("Workbench.TFrame", background="#e9edf2")
        style.configure("Panel.TLabelframe", background="#f4f6f8")
        style.configure("Panel.TLabelframe.Label", font=("Microsoft YaHei UI", 9, "bold"))
        style.configure("Compact.TButton", padding=(10, 3), font=("Microsoft YaHei UI", 9))
        style.configure("Treeview", rowheight=24, font=("Microsoft YaHei UI", 9))
        style.configure("Treeview.Heading", font=("Microsoft YaHei UI", 9, "bold"))

    def _build(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)
        self._build_toolbar()
        self._build_body()

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

        actions = [
            ("刷新基站", 1),
            ("刷新案例", 2),
            ("新增用例", 3),
            ("编辑用例", 4),
            ("删除用例", 5),
            ("FAQ帮助", 6),
            ("版本说明", 7),
            ("打开配置", 8),
            ("打开案例", 9),
            ("打开结果", 10),
            ("新增基站", 11),
            ("删除基站", 12),
        ]
        for text, column in actions:
            ttk.Button(self.toolbar, text=text, style="Compact.TButton").grid(
                row=0,
                column=column,
                sticky="ew",
                padx=5,
            )

        ttk.Label(self.toolbar, text="并发", style="Toolbar.TLabel").grid(
            row=1,
            column=1,
            sticky="e",
            padx=(0, 4),
            pady=(10, 0),
        )
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

        ttk.Button(self.toolbar, text="开始", style="Compact.TButton").grid(
            row=1,
            column=5,
            padx=(24, 0),
            pady=(10, 0),
        )
        ttk.Button(self.toolbar, text="停止", style="Compact.TButton").grid(
            row=1,
            column=6,
            padx=(5, 0),
            pady=(10, 0),
        )
        ttk.Label(self.toolbar, text="状态：空闲", style="Toolbar.TLabel").grid(
            row=1,
            column=7,
            sticky="w",
            padx=(14, 0),
            pady=(10, 0),
        )

    def _build_body(self) -> None:
        body = ttk.Frame(self.root, style="Workbench.TFrame", padding=10)
        body.grid(row=1, column=0, sticky="nsew")
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

        self._build_left()
        self._build_center()
        self._build_right()

    def _build_left(self) -> None:
        self.left_pane.columnconfigure(0, weight=1)
        self.left_pane.rowconfigure(0, weight=3)
        self.left_pane.rowconfigure(1, weight=1)

        case_frame = ttk.LabelFrame(self.left_pane, text="案例树", style="Panel.TLabelframe", padding=6)
        case_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        case_frame.columnconfigure(0, weight=1)
        case_frame.rowconfigure(0, weight=1)

        self.case_tree = ttk.Treeview(case_frame, show="tree")
        case_scrollbar = ttk.Scrollbar(case_frame, orient=tk.VERTICAL, command=self.case_tree.yview)
        self.case_tree.configure(yscrollcommand=case_scrollbar.set)
        self.case_tree.grid(row=0, column=0, sticky="nsew")
        case_scrollbar.grid(row=0, column=1, sticky="ns")

        station_frame = ttk.LabelFrame(self.left_pane, text="基站列表", style="Panel.TLabelframe", padding=6)
        station_frame.grid(row=1, column=0, sticky="nsew")
        station_frame.columnconfigure(0, weight=1)
        station_frame.rowconfigure(0, weight=1)

        columns = ("selected", "name", "ip", "user")
        self.station_table = ttk.Treeview(station_frame, columns=columns, show="headings", height=6)
        headings = {"selected": "选中", "name": "名称", "ip": "IP", "user": "用户"}
        widths = {"selected": 46, "name": 120, "ip": 130, "user": 70}
        for column in columns:
            self.station_table.heading(column, text=headings[column])
            self.station_table.column(column, width=widths[column], anchor="w", stretch=True)
        self.station_table.grid(row=0, column=0, sticky="nsew")

    def _build_center(self) -> None:
        self.center_pane.columnconfigure(0, weight=1)
        self.center_pane.rowconfigure(0, weight=4)
        self.center_pane.rowconfigure(1, weight=1)

        log_frame = ttk.LabelFrame(self.center_pane, text="实时日志", style="Panel.TLabelframe", padding=6)
        log_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.realtime_log = ScrolledText(log_frame, wrap="word", font=("Consolas", 10), relief="solid", bd=1)
        self.realtime_log.grid(row=0, column=0, sticky="nsew")

        step_frame = ttk.LabelFrame(self.center_pane, text="步骤明细", style="Panel.TLabelframe", padding=6)
        step_frame.grid(row=1, column=0, sticky="nsew")
        step_frame.columnconfigure(0, weight=1)
        step_frame.rowconfigure(0, weight=1)

        columns = ("step", "name", "condition", "expected", "actual", "result", "note")
        self.step_table = ttk.Treeview(step_frame, columns=columns, show="headings", height=7)
        headings = {
            "step": "步骤",
            "name": "步骤名称",
            "condition": "判断条件",
            "expected": "期望值",
            "actual": "实际值",
            "result": "结果",
            "note": "说明",
        }
        for column in columns:
            self.step_table.heading(column, text=headings[column])
            self.step_table.column(column, width=110, stretch=True)
        self.step_table.grid(row=0, column=0, sticky="nsew")

    def _build_right(self) -> None:
        self.right_pane.columnconfigure(0, weight=1)
        self.right_pane.rowconfigure(0, weight=1)
        self.right_pane.rowconfigure(1, weight=2)

        summary_frame = ttk.LabelFrame(
            self.right_pane,
            text="测试案例简要描述",
            style="Panel.TLabelframe",
            padding=6,
        )
        summary_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        summary_frame.columnconfigure(0, weight=1)
        summary_frame.rowconfigure(0, weight=1)
        self.case_summary = ScrolledText(
            summary_frame,
            wrap="word",
            height=12,
            font=("Microsoft YaHei UI", 10),
            relief="solid",
            bd=1,
        )
        self.case_summary.grid(row=0, column=0, sticky="nsew")

        params_frame = ttk.LabelFrame(
            self.right_pane,
            text="案例参数（点击左侧案例后显示）",
            style="Panel.TLabelframe",
            padding=6,
        )
        params_frame.grid(row=1, column=0, sticky="nsew")
        params_frame.columnconfigure(0, weight=1)
        params_frame.rowconfigure(0, weight=1)

        columns = ("group", "param", "value")
        self.parameter_table = ttk.Treeview(params_frame, columns=columns, show="headings")
        for column, title, width in (("group", "组号", 56), ("param", "参数", 130), ("value", "值", 220)):
            self.parameter_table.heading(column, text=title)
            self.parameter_table.column(column, width=width, stretch=True)
        self.parameter_table.grid(row=0, column=0, sticky="nsew")

    def _load_mock_data(self) -> None:
        root = self.case_tree.insert("", tk.END, text="5G产品测试", open=True)
        power = self.case_tree.insert(root, tk.END, text="LA大功率", open=True)
        manage = self.case_tree.insert(power, tk.END, text="5G基站管理", open=True)
        for text in ("RU射频状态开关", "RU通道使能开关", "升级管理-BBU-协议栈", "升级管理-RRU-内置-uf"):
            self.case_tree.insert(manage, tk.END, text=text)
        reliable = self.case_tree.insert(root, tk.END, text="可靠性", open=True)
        for text in ("设备自启-硬件故障-CPU死锁与内核崩溃", "设备自启-软件故障-5G"):
            self.case_tree.insert(reliable, tk.END, text=text)

        for row in (
            ("☑", "LA_192.168.13.13", "192.168.13.13", "root"),
            ("☐", "自研SL 7+9", "192.168.16.199", "root"),
        ):
            self.station_table.insert("", tk.END, values=row)

        self.realtime_log.insert("end", "17:05:17  ready\n")
        self.realtime_log.insert("end", "17:05:17  ssh=D:\\desktop\\dependencies\\OpenSSH\\ssh.exe\n")
        self.realtime_log.insert("end", "17:05:17  layout.caseTreeWidth=360\n")

        for row in (
            ("1", "打开RU页面", "页面加载成功", "可见", "", "等待", ""),
            ("2", "切换射频状态", "接口返回正常", "success", "", "等待", ""),
            ("3", "校验状态", "状态等于目标值", "on", "", "等待", ""),
        ):
            self.step_table.insert("", tk.END, values=row)

        self.case_summary.insert("end", "案例名称:\nRU射频状态开关\n\n")
        self.case_summary.insert("end", "测试目的:\n验证通过网页开关射频。\n\n")
        self.case_summary.insert("end", "关键标签:\nweb / upgrade / bbu / lan / parameter-set\n")

        params = [
            ("1", "web_url", "http://${station_ip}:8400/project"),
            ("1", "web_username", "root"),
            ("1", "web_password", "5GNR@root"),
            ("1", "web_vercode", ".."),
            ("1", "expected_version", "aa.fdd.fr1.5.1.72.192"),
            ("1", "测试次数", "1"),
        ]
        for row in params:
            self.parameter_table.insert("", tk.END, values=row)


def main() -> None:
    root = tk.Tk()
    DesktopWorkbenchPreview(root)
    root.mainloop()


if __name__ == "__main__":
    main()
