from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, QMessageBox
from PySide6.QtCore import Signal


class NewProjectDialog(QDialog):
    project_created = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新建项目")
        self.setModal(True)
        self.setMinimumWidth(400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("项目名称:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("输入项目名称")
        layout.addWidget(self.name_input)

        button_layout = QHBoxLayout()
        self.ok_btn = QPushButton("创建")
        self.cancel_btn = QPushButton("取消")
        self.ok_btn.clicked.connect(self._on_ok)
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)

    def _on_ok(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "警告", "请输入项目名称")
            return
        if " " in name or "/" in name or "\\" in name:
            QMessageBox.warning(self, "警告", "项目名称不能包含空格或特殊字符")
            return
        self.project_created.emit(name)
        self.accept()
