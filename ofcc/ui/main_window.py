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
    QProgressBar,
    QSplitter,
    QGroupBox,
    QComboBox,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QAction, QTextCursor
from typing import Dict, Any, Optional

from ofcc.core.project_manager import ProjectManager, Project
from ofcc.core.case_manager import CaseManager, Case
from ofcc.core.template_manager import TemplateManager
from ofcc.core.task_executor import TaskExecutor, TaskStatus
from ofcc.core.settings_manager import SettingsManager
from ofcc.ui.dialogs.new_project_dialog import NewProjectDialog
from ofcc.ui.dialogs.new_case_dialog import NewCaseDialog
from ofcc.ui.dialogs.tutorial_dialog import TutorialDialog
from ofcc.infra.logger import get_logger

logger = get_logger(__name__)


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
        self.current_case: Optional[Case] = None
        self.current_project: Optional[Project] = None
        self.project_manager = ProjectManager()
        self.case_manager = CaseManager()
        self.template_manager = TemplateManager()
        self.task_executor = TaskExecutor()
        self.settings_manager = SettingsManager()
        self._connect_task_signals()
        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_statusbar()
        self._refresh_project_tree()
        self._update_status()
        self._show_tutorial_if_needed()

    def _connect_task_signals(self):
        self.task_executor.task_started.connect(self._on_task_started)
        self.task_executor.task_output.connect(self._on_task_output)
        self.task_executor.task_error.connect(self._on_task_error)
        self.task_executor.task_status.connect(self._on_task_status_changed)
        self.task_executor.task_finished.connect(self._on_task_finished)

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
        self.project_tree.itemDoubleClicked.connect(self._on_tree_item_double_clicked)
        self.project_tree_dock.setWidget(self.project_tree)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.project_tree_dock)

    def _refresh_project_tree(self):
        self.project_tree.clear()
        projects = self.project_manager.get_all()
        for project in projects:
            project_item = QTreeWidgetItem([project.name])
            project_item.setData(0, Qt.UserRole, {"type": "project", "id": project.id, "name": project.name})
            cases = self.case_manager.get_by_project(project.id)
            for case in cases:
                status = case.status
                display_name = f"{case.name} [{status}]"
                case_item = QTreeWidgetItem([display_name])
                case_item.setData(0, Qt.UserRole, {"type": "case", "id": case.id, "project_id": project.id})
                project_item.addChild(case_item)
            self.project_tree.addTopLevelItem(project_item)
        self.project_tree.expandAll()
        self.log(f"项目树已刷新，共 {len(projects)} 个项目")

    def _create_config_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("参数配置页面 - 求解器、边界条件、物理模型配置"))
        layout.addStretch()
        return widget

    def _create_run_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 求解器控制区
        control_group = QGroupBox("求解运行控制")
        control_layout = QHBoxLayout()

        self.solver_combo = QComboBox()
        self.solver_combo.addItems(["blockMesh", "simpleFoam", "pisoFoam", "icoFoam", "snappyHexMesh"])

        self.run_btn = QPushButton("▶ 运行")
        self.run_btn.clicked.connect(self._on_run_solver)
        self.stop_btn = QPushButton("■ 停止")
        self.stop_btn.clicked.connect(self._on_stop_solver)
        self.stop_btn.setEnabled(False)

        control_layout.addWidget(QLabel("求解器:"))
        control_layout.addWidget(self.solver_combo)
        control_layout.addWidget(self.run_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addStretch()

        control_group.setLayout(control_layout)
        layout.addWidget(control_group)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # 实时日志预览
        self.run_log = QTextEdit()
        self.run_log.setReadOnly(True)
        self.run_log.setMaximumHeight(200)
        layout.addWidget(QLabel("运行日志:"))
        layout.addWidget(self.run_log)

        layout.addStretch()
        return widget

    def _create_log_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        toolbar = QHBoxLayout()
        self.clear_log_btn = QPushButton("清空日志")
        self.clear_log_btn.clicked.connect(lambda: self.log_text.clear())
        self.export_log_btn = QPushButton("导出日志")
        self.export_log_btn.clicked.connect(self._on_export_log)
        toolbar.addWidget(self.clear_log_btn)
        toolbar.addWidget(self.export_log_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

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
        file_menu.addAction("刷新项目", self._on_refresh_projects)
        file_menu.addSeparator()
        file_menu.addAction("退出", self.close)

        project_menu = menubar.addMenu("项目")
        project_menu.addAction("新建 Case", self._on_new_case)
        project_menu.addAction("删除项目", self._on_delete_project)
        project_menu.addAction("保存", self._on_save)

        solver_menu = menubar.addMenu("求解器")
        solver_menu.addAction("运行求解", self._on_run_solver)
        solver_menu.addAction("停止求解", self._on_stop_solver)

        tool_menu = menubar.addMenu("工具")
        tool_menu.addAction("设置", self._on_settings)
        tool_menu.addAction("环境诊断", self._on_diagnostics)

        help_menu = menubar.addMenu("帮助")
        help_menu.addAction("新手教程", self._on_show_tutorial)
        help_menu.addSeparator()
        help_menu.addAction("关于", self._on_about)

    def _setup_toolbar(self):
        toolbar = QToolBar("主工具栏")
        self.addToolBar(toolbar)

        toolbar.addAction("新建项目", self._on_new_project)
        toolbar.addAction("新建Case", self._on_new_case)
        toolbar.addAction("刷新", self._on_refresh_projects)
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
        else:
            self.of_version_label.setText("OpenFOAM: 未检测到")

        if self.current_project:
            self.status_label.setText(f"项目: {self.current_project.name}")
        else:
            self.status_label.setText("未打开项目")

    def _on_tree_item_double_clicked(self, item, column):
        data = item.data(0, Qt.UserRole)
        if data and data["type"] == "case":
            case = self.case_manager.get_by_id(data["id"])
            if case:
                self.current_case = case
                self.current_project = self.project_manager.get_by_id(data["project_id"])
                self._update_status()
                self.log(f"选中 Case: {case.name} (求解器: {case.solver})")
                self.solver_combo.setCurrentText(case.solver)

    def _on_new_project(self):
        dialog = NewProjectDialog(self)
        dialog.project_created.connect(self._create_project)
        dialog.exec()

    def _create_project(self, name: str):
        try:
            if self.project_manager.exists(name):
                QMessageBox.warning(self, "警告", f"项目 '{name}' 已存在")
                return
            project = self.project_manager.create(name)
            self._refresh_project_tree()
            self.log(f"项目创建成功: {name}")
        except Exception as e:
            logger.error(f"创建项目失败: {e}")
            QMessageBox.critical(self, "错误", f"创建项目失败: {e}")

    def _on_new_case(self):
        if not self.current_project:
            QMessageBox.warning(self, "提示", "请先在项目树中选择一个项目")
            return
        templates = self.template_manager.get_all()
        dialog = NewCaseDialog(templates, self)
        dialog.case_created.connect(lambda name, tpath: self._create_case(name, tpath))
        dialog.exec()

    def _create_case(self, name: str, template_path: str = None):
        try:
            case = self.case_manager.create(self.current_project.id, name, template_path)
            self._refresh_project_tree()
            self.log(f"Case 创建成功: {name}")
        except Exception as e:
            logger.error(f"创建 Case 失败: {e}")
            QMessageBox.critical(self, "错误", f"创建 Case 失败: {e}")

    def _on_delete_project(self):
        if not self.current_project:
            QMessageBox.warning(self, "提示", "请先在项目树中选择要删除的项目")
            return
        reply = QMessageBox.question(self, "确认", f"确定要删除项目 '{self.current_project.name}' 吗？此操作不可恢复。")
        if reply == QMessageBox.Yes:
            try:
                self.project_manager.delete(self.current_project.id)
                self.current_project = None
                self.current_case = None
                self._refresh_project_tree()
                self._update_status()
                self.log("项目已删除")
            except Exception as e:
                logger.error(f"删除项目失败: {e}")
                QMessageBox.critical(self, "错误", f"删除项目失败: {e}")

    def _on_refresh_projects(self):
        self._refresh_project_tree()

    def _on_save(self):
        self.log("保存")

    def _on_run_solver(self):
        if not self.current_case:
            QMessageBox.warning(self, "提示", "请先在项目树中选择一个 Case")
            return

        solver = self.solver_combo.currentText()
        case = self.current_case

        self.log(f"启动求解器: {solver}, Case: {case.name}")
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.task_label.setText(f"任务: 运行中")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        self.task_executor.start_task(case.id, solver, case.path)

    def _on_stop_solver(self):
        if self.current_case:
            self.task_executor.stop_task(self.current_case.id)
            self.log("请求停止任务...")

    def _on_task_started(self, case_id: str):
        self.log(f"[任务开始] case_id={case_id}")

    def _on_task_output(self, case_id: str, line: str):
        self.run_log.append(line)
        self.log_text.append(line)
        self.run_log.moveCursor(QTextCursor.End)
        self.log_text.moveCursor(QTextCursor.End)

    def _on_task_error(self, case_id: str, line: str):
        self.run_log.append(f"<font color='red'>{line}</font>")
        self.log_text.append(f"<font color='red'>{line}</font>")
        self.run_log.moveCursor(QTextCursor.End)
        self.log_text.moveCursor(QTextCursor.End)

    def _on_task_status_changed(self, case_id: str, status: str):
        self.task_label.setText(f"任务: {status}")
        if self.current_case and self.current_case.id == case_id:
            self.case_manager.update_status(case_id, status)
            self._refresh_project_tree()

    def _on_task_finished(self, case_id: str, returncode: int, stdout: str, stderr: str):
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)

        if returncode == 0:
            self.log(f"[任务完成] case_id={case_id}, returncode=0")
        else:
            self.log(f"[任务失败] case_id={case_id}, returncode={returncode}")

        if self.current_case and self.current_case.id == case_id:
            status = "completed" if returncode == 0 else "failed"
            self.case_manager.update_status(case_id, status)
            self._refresh_project_tree()

    def _on_export_log(self):
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "导出日志", "ofcc_log.txt", "Text Files (*.txt)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.log_text.toPlainText())
            self.log(f"日志已导出: {path}")

    def _on_settings(self):
        QMessageBox.information(self, "提示", "设置功能（待实现）")

    def _on_diagnostics(self):
        QMessageBox.information(self, "环境诊断", f"OpenFOAM: {self.of_env['message']}")

    def _show_tutorial_if_needed(self):
        if self.settings_manager.get("show_tutorial_on_startup", True):
            self.log("新手教程已自动弹出")
            QTimer.singleShot(500, self._on_show_tutorial)

    def _on_show_tutorial(self):
        dialog = TutorialDialog(self)
        dialog.closed_permanently.connect(self._on_tutorial_closed_permanently)
        dialog.exec()

    def _on_tutorial_closed_permanently(self):
        self.settings_manager.update("show_tutorial_on_startup", False)
        self.log("新手教程已永久关闭")

    def _on_about(self):
        QMessageBox.about(
            self,
            "关于 OFCC",
            "OFCC - OpenFOAM CFD Client\n版本 0.1.0\n基于 PySide6 的 OpenFOAM 仿真客户端",
        )

    def log(self, message: str):
        self.log_text.append(f"[INFO] {message}")
        self.log_text.moveCursor(QTextCursor.End)
