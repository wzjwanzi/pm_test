from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QHBoxLayout, QListWidget, QMainWindow, QStackedWidget, QWidget

from desktop.controller import DesktopController
from desktop_qt.pages.case_library import CaseLibraryPage
from desktop_qt.pages.devices import DevicesPage
from desktop_qt.pages.home import HomePage
from desktop_qt.pages.results import ResultsPage
from desktop_qt.pages.settings import SettingsPage
from desktop_qt.state import QtDesktopState


class MainWindow(QMainWindow):
    def __init__(self, *, controller=None, start_polling: bool = True):
        super().__init__()
        self.controller = controller or DesktopController()
        self.state = QtDesktopState()
        self.setWindowTitle("基站自动化测试平台")
        self.resize(1500, 900)

        self.nav_list = QListWidget()
        self.stack = QStackedWidget()
        self.home_page = HomePage(self)
        self.case_library_page = CaseLibraryPage(self)
        self.settings_page = SettingsPage(self)
        self.results_page = ResultsPage(self)
        self.devices_page = DevicesPage(self)

        self._build_layout()
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.refresh_runs)
        if start_polling:
            self.poll_timer.start(2000)

    def _build_layout(self) -> None:
        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(self.nav_list, 0)
        layout.addWidget(self.stack, 1)

        pages = [
            ("首页运行", self.home_page),
            ("用例库", self.case_library_page),
            ("运行配置", self.settings_page),
            ("结果日志", self.results_page),
            ("设备管理", self.devices_page),
        ]
        for label, page in pages:
            self.nav_list.addItem(label)
            self.stack.addWidget(page)

        self.nav_list.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav_list.setCurrentRow(0)
        self.setCentralWidget(central)

    def refresh_runs(self) -> None:
        self.controller.list_runs(limit=20)
        run_id = self.state.selected_run_id
        if not run_id or not hasattr(self.controller, "get_run"):
            return
        run = self.controller.get_run(run_id)
        self.state.latest_run = run
        self.home_page.render_run(run)
        self.results_page.render_run(run)
