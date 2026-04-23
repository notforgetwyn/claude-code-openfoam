from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSlider, QGroupBox, QCheckBox, QLineEdit,
    QDialogButtonBox, QTabWidget, QWidget, QFontComboBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class SettingsDialog(QDialog):
    settings_changed = Signal(dict)

    def __init__(self, current_settings: dict, parent=None):
        super().__init__(parent)
        self.current_settings = current_settings
        self.setWindowTitle("设置")
        self.setModal(True)
        self.setMinimumSize(500, 400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        tabs = QTabWidget()

        # 外观设置
        tabs.addTab(self._create_appearance_tab(), "外观")
        # 仿真设置
        tabs.addTab(self._create_simulation_tab(), "仿真")
        # 环境设置
        tabs.addTab(self._create_environment_tab(), "环境")

        layout.addWidget(tabs)

        # 按钮
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _create_appearance_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 字体设置
        font_group = QGroupBox("字体")
        font_layout = QVBoxLayout()

        # 字体类型
        font_family_layout = QHBoxLayout()
        font_family_layout.addWidget(QLabel("字体:"))
        self.font_combo = QFontComboBox()
        current_font = self.current_settings.get("font_family", "Microsoft YaHei")
        self.font_combo.setCurrentFont(QFont(current_font))
        font_family_layout.addWidget(self.font_combo)
        font_layout.addLayout(font_family_layout)

        # 字体大小
        font_size_layout = QHBoxLayout()
        font_size_layout.addWidget(QLabel("大小:"))
        self.font_size_slider = QSlider(Qt.Horizontal)
        self.font_size_slider.setRange(8, 24)
        self.font_size_slider.setValue(int(self.current_settings.get("font_size", 10)))
        self.font_size_slider.setTickPosition(QSlider.TicksBelow)
        self.font_size_slider.setTickInterval(2)
        self.font_size_value = QLabel(f"{self.font_size_slider.value()} px")
        self.font_size_slider.valueChanged.connect(
            lambda v: self.font_size_value.setText(f"{v} px")
        )
        font_size_layout.addWidget(self.font_size_slider)
        font_size_layout.addWidget(self.font_size_value)
        font_layout.addLayout(font_size_layout)

        # 预览
        self.font_preview = QLabel("OpenFOAM CFD Client - 预览文字")
        self.font_preview.setAlignment(Qt.AlignCenter)
        self.font_preview.setStyleSheet("border: 1px solid gray; padding: 8px;")
        font_layout.addWidget(self.font_preview)

        self.font_combo.currentFontChanged.connect(self._update_font_preview)
        self.font_size_slider.valueChanged.connect(self._update_font_preview)

        font_group.setLayout(font_layout)
        layout.addWidget(font_group)

        # 主题设置
        theme_group = QGroupBox("主题")
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("颜色主题:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["浅色", "深色", "跟随系统"])
        theme_name = self.current_settings.get("theme", "浅色")
        self.theme_combo.setCurrentText(theme_name)
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()
        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)

        layout.addStretch()
        return widget

    def _create_simulation_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        default_solver_layout = QHBoxLayout()
        default_solver_layout.addWidget(QLabel("默认求解器:"))
        self.default_solver_combo = QComboBox()
        self.default_solver_combo.addItems(["simpleFoam", "pisoFoam", "icoFoam", "snappyHexMesh"])
        self.default_solver_combo.setCurrentText(
            self.current_settings.get("default_solver", "simpleFoam")
        )
        default_solver_layout.addWidget(self.default_solver_combo)
        default_solver_layout.addStretch()
        layout.addLayout(default_solver_layout)

        auto_save_layout = QHBoxLayout()
        self.auto_save_check = QCheckBox("自动保存")
        self.auto_save_check.setChecked(self.current_settings.get("auto_save", True))
        auto_save_layout.addWidget(self.auto_save_check)
        auto_save_layout.addStretch()
        layout.addLayout(auto_save_layout)

        expert_mode_layout = QHBoxLayout()
        self.expert_mode_check = QCheckBox("专家模式（显示全部参数）")
        self.expert_mode_check.setChecked(self.current_settings.get("expert_mode", False))
        expert_mode_layout.addWidget(self.expert_mode_check)
        expert_mode_layout.addStretch()
        layout.addLayout(expert_mode_layout)

        layout.addStretch()
        return widget

    def _create_environment_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        bashrc_layout = QHBoxLayout()
        bashrc_layout.addWidget(QLabel("OpenFOAM bashrc:"))
        self.bashrc_input = QLineEdit(
            self.current_settings.get("openfoam_bashrc", "/home/shihuayue/openfoam/OpenFOAM-dev/etc/bashrc")
        )
        bashrc_layout.addWidget(self.bashrc_input)
        layout.addLayout(bashrc_layout)

        workspace_layout = QHBoxLayout()
        workspace_layout.addWidget(QLabel("工作空间路径:"))
        self.workspace_input = QLineEdit(
            self.current_settings.get("workspace_path", "")
        )
        workspace_layout.addWidget(self.workspace_input)
        layout.addLayout(workspace_layout)

        layout.addStretch()
        return widget

    def _update_font_preview(self):
        font = self.font_combo.currentFont()
        font.setPointSize(self.font_size_slider.value())
        self.font_preview.setFont(font)

    def _on_accept(self):
        settings = {
            "font_family": self.font_combo.currentFont().family(),
            "font_size": self.font_size_slider.value(),
            "theme": self.theme_combo.currentText(),
            "default_solver": self.default_solver_combo.currentText(),
            "auto_save": self.auto_save_check.isChecked(),
            "expert_mode": self.expert_mode_check.isChecked(),
            "openfoam_bashrc": self.bashrc_input.text(),
            "workspace_path": self.workspace_input.text(),
        }
        self.settings_changed.emit(settings)
        self.accept()
