from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QDockWidget,
    QStatusBar,
    QToolBar,
    QMenuBar,
    QMessageBox,
    QTabWidget,
    QLabel,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QPushButton,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QAction
from typing import Dict, Any


class MainWindow(QMainWindow):
    """
    OpenFOAM CFD Client 主窗口

    布局：
    ┌──────────────────────────────────────────────────────────┐
    │  菜单栏（文件 / 项目 / Case / 求解器 / 工具 / 帮助）        │
    ├──────────────────────────────────────────────────────────┤
    │  工具栏（新建项目 / 打开 / 保存 / 运行 / 停止 / 设置）       │
    ├────────────┬─────────────────────────────────────────────┤
    │  项目树     │  主工作区                                   │
    │  （左侧面板）│  ┌─────────────────────────────────────────┐ │
    │  - 项目A    │  │ 标签页：参数配置 / 求解运行 / 日志 / 结果  │ │
    │    - Case1  │  ├─────────────────────────────────────────┤ │
    │    - Case2  │  │                                         │ │
    │  - 项目B    │  │  （内容区）                              │ │
    │            │  │                                         │ │
    │            │  └─────────────────────────────────────────┘ │
    ├────────────┴─────────────────────────────────────────────┤
    │  状态栏（当前 Case / 任务状态 / OpenFOAM 版本）            │
    └──────────────────────────────────────────────────────────┘
    """

    def __init__(self, of_env: Dict[str, Any]):
        super().__init__()
        self.of_env = of_env
        self.current_case = None
        self.current_project = None
        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_statusbar()
        self._update_status()

    def _setup_ui(self):
        self.setWindowTitle("OFCC - OpenFOAM CFD Client")
        self.setMinimumSize(1200, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self._create_config_page(), "参数配置")
        self.tab_widget.addTab(self._create_run_page(), "求解运行")
        self.tab_widget.addTab(self._create_log_page(), "日志")
        self.tab_widget.addTab(self._create_result_page(), "结果")
        main_layout.addWidget(self.tab_widget)

        self._setup_project_tree()

    def _setup_project_tree(self):
        self.project_tree_dock = QDockWidget("项目", self)
        self.project_tree = QTreeWidget()
        self.project_tree.setHeaderLabel("项目 / Case")
        self.project_tree_dock.setWidget(self.project_tree)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.project_tree_dock)

    def _create_config_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("参数配置页面 - 求解器、边界条件、物理模型配置"))
        layout.addStretch()
        return widget

    def _create_run_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("求解运行页面 - 运行控制、进度显示"))
        layout.addStretch()
        return widget

    def _create_log_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        return widget

    def _create_result_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("结果页面 - 后处理、可视化"))
        layout.addStretch()
        return widget

    def _setup_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("文件")
        file_menu.addAction("新建项目", self._on_new_project)
        file_menu.addAction("打开项目", self._on_open_project)
        file_menu.addSeparator()
        file_menu.addAction("退出", self.close)

        project_menu = menubar.addMenu("项目")
        project_menu.addAction("新建 Case", self._on_new_case)
        project_menu.addAction("保存", self._on_save)

        solver_menu = menubar.addMenu("求解器")
        solver_menu.addAction("运行求解", self._on_run_solver)
        solver_menu.addAction("停止求解", self._on_stop_solver)

        tool_menu = menubar.addMenu("工具")
        tool_menu.addAction("设置", self._on_settings)
        tool_menu.addAction("环境诊断", self._on_diagnostics)

        help_menu = menubar.addMenu("帮助")
        help_menu.addAction("关于", self._on_about)

    def _setup_toolbar(self):
        toolbar = QToolBar("主工具栏")
        self.addToolBar(toolbar)

        toolbar.addAction("新建项目", self._on_new_project)
        toolbar.addAction("打开", self._on_open_project)
        toolbar.addAction("保存", self._on_save)
        toolbar.addSeparator()
        toolbar.addAction("运行", self._on_run_solver)
        toolbar.addAction("停止", self._on_stop_solver)
        toolbar.addSeparator()
        toolbar.addAction("设置", self._on_settings)

    def _setup_statusbar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("未打开项目")
        self.task_label = QLabel("任务: 空闲")
        self.of_version_label = QLabel()
        self.status_bar.addPermanentWidget(self.status_label, 1)
        self.status_bar.addPermanentWidget(self.task_label, 1)
        self.status_bar.addPermanentWidget(self.of_version_label, 1)

    def _update_status(self):
        if self.of_env["of_installed"]:
            self.of_version_label.setText(f"OpenFOAM: {self.of_env['version']}")
            self.status_bar.showMessage(f"✓ {self.of_env['message']}", 3000)
        else:
            self.of_version_label.setText("OpenFOAM: 未检测到")
            self.status_bar.showMessage(f"✗ {self.of_env['message']}", 3000)

        if self.current_project:
            self.status_label.setText(f"项目: {self.current_project}")
        else:
            self.status_label.setText("未打开项目")

    def _on_new_project(self):
        self.log("新建项目")
        QMessageBox.information(self, "提示", "新建项目功能（待实现）")

    def _on_open_project(self):
        self.log("打开项目")
        QMessageBox.information(self, "提示", "打开项目功能（待实现）")

    def _on_new_case(self):
        self.log("新建 Case")
        QMessageBox.information(self, "提示", "新建 Case 功能（待实现）")

    def _on_save(self):
        self.log("保存")

    def _on_run_solver(self):
        self.log("运行求解")
        QMessageBox.information(self, "提示", "运行求解功能（待实现）")

    def _on_stop_solver(self):
        self.log("停止求解")

    def _on_settings(self):
        QMessageBox.information(self, "提示", "设置功能（待实现）")

    def _on_diagnostics(self):
        QMessageBox.information(self, "环境诊断", f"OpenFOAM: {self.of_env['message']}")

    def _on_about(self):
        QMessageBox.about(
            self,
            "关于 OFCC",
            "OFCC - OpenFOAM CFD Client\n版本 0.1.0\n基于 PySide6 的 OpenFOAM 仿真客户端",
        )

    def log(self, message: str):
        self.log_text.append(f"[INFO] {message}")
