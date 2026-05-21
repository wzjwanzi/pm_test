from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QComboBox, QListWidget, QTextEdit, QVBoxLayout, QWidget

from desktop.formatters import format_run_console


class ResultsPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        layout = QVBoxLayout(self)
        self.run_list = QListWidget()
        self.step_list = QListWidget()
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["全部", "ADB", "SSH", "Web 抓包", "灌包服务器", "错误"])
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.artifact_list = QListWidget()
        layout.addWidget(self.run_list)
        layout.addWidget(self.step_list)
        layout.addWidget(self.filter_combo)
        layout.addWidget(self.log_text)
        layout.addWidget(self.artifact_list)

    def render_run(self, run: dict[str, Any] | None) -> None:
        self.step_list.clear()
        self.artifact_list.clear()
        self.log_text.setPlainText(format_run_console(run))
        for case in (run or {}).get("case_records") or []:
            for step in case.get("step_records") or []:
                self.step_list.addItem(str(step.get("step_id") or step.get("kind") or "-"))
                for path in _artifact_paths(step):
                    self.artifact_list.addItem(path)


def _artifact_paths(step: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for artifact in step.get("artifacts") or []:
        if isinstance(artifact, dict):
            path = artifact.get("path")
        else:
            path = artifact
        if path:
            paths.append(str(path))
    return paths
