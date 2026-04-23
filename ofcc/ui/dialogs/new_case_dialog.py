from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, QComboBox, QMessageBox
from PySide6.QtCore import Signal


class NewCaseDialog(QDialog):
    case_created = Signal(str, str)

    def __init__(self, templates: list, parent=None):
        super().__init__(parent)
        self.templates = templates
        self.setWindowTitle("新建 Case")
        self.setModal(True)
        self.setMinimumWidth(400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Case 名称:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("输入 Case 名称")
        layout.addWidget(self.name_input)

        layout.addWidget(QLabel("求解器:"))
        self.solver_input = QComboBox()
        self.solver_input.addItems(["simpleFoam", "pisoFoam", "icoFoam", "blockMesh"])
        layout.addWidget(self.solver_input)

        layout.addWidget(QLabel("模板（可选）:"))
        self.template_input = QComboBox()
        self.template_input.addItem("（无模板）")
        for t in self.templates:
            self.template_input.addItem(t.name)
        layout.addWidget(self.template_input)

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
            QMessageBox.warning(self, "警告", "请输入 Case 名称")
            return
        if " " in name or "/" in name or "\\" in name:
            QMessageBox.warning(self, "警告", "Case 名称不能包含空格或特殊字符")
            return
        template_name = self.template_input.currentText()
        template_path = None
        if template_name != "（无模板）":
            for t in self.templates:
                if t.name == template_name:
                    template_path = str(t.path)
                    break
        solver = self.solver_input.currentText()
        self.case_created.emit(name, template_path)
        self.accept()
