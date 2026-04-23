from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QDockWidget, QStatusBar, QToolBar, QMenuBar,
    QMessageBox, QTabWidget, QLabel, QTextEdit,
    QTreeWidget, QTreeWidgetItem, QPushButton, QProgressBar,
    QGroupBox, QComboBox, QListWidget, QSplitter,
    QFrame, QSizePolicy, QSpacerItem,
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QAction, QIcon, QTextCursor, QFont

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


class ActivityBarButton(QPushButton):
    """活动栏图标按钮"""
    def __init__(self, icon_char: str, tooltip: str, parent=None):
        super().__init__(parent)
        self.setText(icon_char)
        self.setToolTip(tooltip)
        self.setFixedSize(48, 48)
        self.setCheckable(True)
        self.setFlat(True)


class MainWindow(QMainWindow):
    """
    OFCC 主窗口 - VS Code 风格布局

    ┌─────────────────────────────────────────────────────────────────┐
    │  标题栏（菜单）                                    ─ □ ✕ │
    ├────┬───────────────────────────────────┬────────────────────┤
    │ 活 │  选项卡栏（config / run / log）     │                    │
    │ 动 │ ┌───────────────────────────────┐   │                    │
    │ 栏 │ │                               │   │                    │
    │    │ │         编辑器区域              │   │                    │
    │ 📁 │ │                               │   │                    │
    │ 🔍 │ └───────────────────────────────┘   │                    │
    │ 🐛 │                                    │                    │
    │ ⚙  ├───────────────────────────────────┤                    │
    │    │  面板（终端 / 日志 / 问题）          │                    │
    ├────┴───────────────────────────────────┴────────────────────┤
    │  状态栏：分支 / 求解器 / 行号 / OF 版本                      │
    └─────────────────────────────────────────────────────────────┘
    """

    ACTIVITY_ICONS = {
        "explorer": "📁",
        "search": "🔍",
        "git": "🐙",
        "simulation": "▶",
        "settings": "⚙",
    }

    def __init__(self, of_env):
        super().__init__()
        self.of_env = of_env
        self.current_case: Case = None
        self.current_project: Project = None
        self.active_panel = "explorer"

        # Managers
        self.project_manager = ProjectManager()
        self.case_manager = CaseManager()
        self.template_manager = TemplateManager()
        self.task_executor = TaskExecutor()
        self.settings_manager = SettingsManager()

        # Connect signals
        self._connect_task_signals()

        # Setup
        self._setup_ui()
        self._setup_menu()
        self._setup_activity_bar()
        self._setup_sidebar()
        self._setup_editor_tabs()
        self._setup_panel()
        self._setup_statusbar()

        self._refresh_project_tree()
        self._update_status()
        self._show_tutorial_if_needed()

    # ────────────────────────────────────────────────────────────────
    # UI Setup
    # ───────────────────────────────────────────────────────────────

    def _setup_ui(self):
        self.setWindowTitle("OFCC - OpenFOAM CFD Client")
        self.setMinimumSize(1200, 800)

        # Central widget: horizontal splitter (sidebar + editor + right sidebar)
        central = QWidget()
        self.setCentralWidget(central)
        central_layout = QHBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        self.main_splitter = QSplitter(Qt.Horizontal)

        # Sidebar (left, activity bar is overlaid on this)
        self.sidebar = QDockWidget()
        self.sidebar.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.sidebar.setTitleBarWidget(QWidget())  # hide title
        self.main_splitter.addWidget(self.sidebar)

        # Editor area (center)
        self.editor_container = QWidget()
        editor_layout = QVBoxLayout(self.editor_container)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(0)
        self.main_splitter.addWidget(self.editor_container)

        # Right sidebar (properties panel)
        self.right_sidebar = QDockWidget("属性")
        self.right_sidebar.setFeatures(QDockWidget.NoDockWidgetFeatures | QDockWidget.DockWidgetClosable)
        self.right_sidebar.setMaximumWidth(280)
        self._setup_right_sidebar()
        self.addDockWidget(Qt.RightDockWidgetArea, self.right_sidebar)

        central_layout.addWidget(self.main_splitter)

        # Panel (bottom, integrated with main window)
        self.panel_dock = QDockWidget()
        self.panel_dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.panel_dock.setTitleBarWidget(QWidget())
        self.addDockWidget(Qt.BottomDockWidgetArea, self.panel_dock)

    def _setup_activity_bar(self):
        """左侧活动栏"""
        self.activity_bar = QFrame()
        self.activity_bar.setFixedWidth(48)
        self.activity_bar.setFrameShape(QFrame.StyledPanel)
        activity_layout = QVBoxLayout(self.activity_bar)
        activity_layout.setContentsMargins(4, 8, 4, 4)
        activity_layout.setSpacing(4)

        self.activity_buttons = {}
        for key, char in self.ACTIVITY_ICONS.items():
            btn = ActivityBarButton(char, key.capitalize())
            btn.setChecked(key == "explorer")
            btn.clicked.connect(lambda checked, k=key: self._on_activity_click(k))
            self.activity_buttons[key] = btn
            activity_layout.addWidget(btn)

        activity_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Place activity bar over sidebar
        self.activity_bar.setParent(self)
        self.activity_bar.move(0, 0)
        self.activity_bar.show()

    def _setup_sidebar(self):
        """侧边栏 - 项目资源管理器"""
        self.sidebar.setWidget(self._create_explorer_panel())
        self._update_sidebar_visibility()

    def _create_explorer_panel(self) -> QWidget:
        """项目浏览器面板"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # 标题栏
        title = QLabel("  项目浏览器")
        title.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        title.setFixedHeight(28)
        layout.addWidget(title)

        # 工具栏
        toolbar_layout = QHBoxLayout()
        new_proj_btn = QPushButton("新建项目")
        new_proj_btn.setFixedHeight(24)
        new_proj_btn.clicked.connect(self._on_new_project)
        new_case_btn = QPushButton("新建Case")
        new_case_btn.setFixedHeight(24)
        new_case_btn.clicked.connect(self._on_new_case)
        toolbar_layout.addWidget(new_proj_btn)
        toolbar_layout.addWidget(new_case_btn)
        toolbar_layout.addStretch()
        layout.addLayout(toolbar_layout)

        # 项目树
        self.project_tree = QTreeWidget()
        self.project_tree.setHeaderLabel("项目 / Case")
        self.project_tree.itemDoubleClicked.connect(self._on_tree_item_double_clicked)
        layout.addWidget(self.project_tree)

        return widget

    def _create_search_panel(self) -> QWidget:
        """搜索面板"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        title = QLabel("  搜索")
        title.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        title.setFixedHeight(28)
        layout.addWidget(title)
        layout.addWidget(QLabel("（搜索功能待实现）"))
        layout.addStretch()
        return widget

    def _create_simulation_panel(self) -> QWidget:
        """仿真控制面板"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        title = QLabel("  仿真控制")
        title.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        title.setFixedHeight(28)
        layout.addWidget(title)

        if self.current_case:
            layout.addWidget(QLabel(f"Case: {self.current_case.name}"))
            layout.addWidget(QLabel(f"求解器: {self.current_case.solver}"))
            layout.addWidget(QLabel(f"状态: {self.current_case.status}"))
        else:
            layout.addWidget(QLabel("请先选择一个 Case"))

        layout.addStretch()
        return widget

    def _setup_editor_tabs(self):
        """编辑器选项卡区"""
        self.editor_tabs = QTabWidget()
        self.editor_tabs.setTabsClosable(True)

        # 参数配置页
        self.config_editor = self._create_config_page()
        self.editor_tabs.addTab(self.config_editor, "参数配置")

        # 求解运行页
        self.run_editor = self._create_run_page()
        self.editor_tabs.addTab(self.run_editor, "求解运行")

        # 日志页（可编辑 OpenFOAM 日志）
        self.log_editor = self._create_log_page()
        self.editor_tabs.addTab(self.log_editor, "日志")

        # 结果页
        self.result_editor = self._create_result_page()
        self.editor_tabs.addTab(self.result_editor, "结果")

        self.editor_tabs.widget(1).layout().addWidget(self._create_run_controls())

        self.editor_container.layout().addWidget(self.editor_tabs)

    def _create_config_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("参数配置 - 编辑 OpenFOAM 配置文件（待实现）"))
        layout.addStretch()
        return widget

    def _create_run_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("求解运行 - 选择求解器并执行（待实现）"))
        layout.addStretch()
        return widget

    def _create_run_controls(self) -> QWidget:
        """求解运行控制条（底部面板区）"""
        group = QGroupBox("求解运行控制")
        hl = QHBoxLayout()

        self.solver_combo = QComboBox()
        self.solver_combo.addItems(["blockMesh", "simpleFoam", "pisoFoam", "icoFoam", "snappyHexMesh"])

        self.run_btn = QPushButton("▶ 运行")
        self.run_btn.setFixedWidth(80)
        self.run_btn.clicked.connect(self._on_run_solver)

        self.stop_btn = QPushButton("■ 停止")
        self.stop_btn.setFixedWidth(80)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._on_stop_solver)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(200)

        hl.addWidget(QLabel("求解器:"))
        hl.addWidget(self.solver_combo)
        hl.addWidget(self.run_btn)
        hl.addWidget(self.stop_btn)
        hl.addWidget(self.progress_bar)
        hl.addStretch()

        group.setLayout(hl)
        return group

    def _create_log_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        toolbar = QHBoxLayout()
        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(lambda: self.log_text.clear())
        export_btn = QPushButton("导出")
        export_btn.clicked.connect(self._on_export_log)
        toolbar.addWidget(clear_btn)
        toolbar.addWidget(export_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

        return widget

    def _create_result_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("结果 - 后处理与可视化（待实现）"))
        layout.addStretch()
        return widget

    def _setup_panel(self):
        """底部面板 - 终端 + 问题"""
        self.panel_widget = QWidget()
        panel_layout = QVBoxLayout(self.panel_widget)
        panel_layout.setContentsMargins(0, 0, 0, 0)

        self.panel_tabs = QTabWidget()
        self.panel_tabs.setTabsClosable(False)
        self.panel_tabs.addTab(self.log_text, "终端")
        self.panel_tabs.addTab(QListWidget(), "问题")

        panel_layout.addWidget(self.panel_tabs)
        self.panel_tabs.setMaximumHeight(200)

        self.panel_dock.setWidget(self.panel_widget)

    def _setup_right_sidebar(self):
        """右侧属性面板"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("属性面板（待实现）"))
        layout.addStretch()
        self.right_sidebar.setWidget(widget)

    def _setup_statusbar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.branch_label = QLabel("  OFCC")
        self.case_label = QLabel("无 Case")
        self.solver_label = QLabel("求解器: -")
        self.pos_label = QLabel("Ln 1, Col 1")
        self.of_label = QLabel(f"OF: {self.of_env.get('version', 'unknown')}")

        for lbl in [self.branch_label, self.case_label, self.solver_label,
                    self.pos_label, self.of_label]:
            self.status_bar.addPermanentWidget(lbl)

        self.status_bar.addPermanentWidget(QLabel("  "))
        self.status_msg_label = QLabel("")
        self.status_bar.addWidget(self.status_msg_label, 1)

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

        solver_menu = menubar.addMenu("求解器")
        solver_menu.addAction("运行求解", self._on_run_solver)
        solver_menu.addAction("停止求解", self._on_stop_solver)

        tool_menu = menubar.addMenu("工具")
        tool_menu.addAction("环境诊断", self._on_diagnostics)

        help_menu = menubar.addMenu("帮助")
        help_menu.addAction("新手教程", self._on_show_tutorial)
        help_menu.addSeparator()
        help_menu.addAction("关于", self._on_about)

    # ────────────────────────────────────────────────────────────────
    # Activity Bar & Sidebar
    # ────────────────────────────────────────────────────────────────

    def _on_activity_click(self, key: str):
        for k, btn in self.activity_buttons.items():
            btn.setChecked(k == key)
        self.active_panel = key
        self._show_sidebar_panel(key)
        self._update_sidebar_visibility()

    def _show_sidebar_panel(self, key: str):
        if key == "explorer":
            self.sidebar.setWidget(self._create_explorer_panel())
        elif key == "search":
            self.sidebar.setWidget(self._create_search_panel())
        elif key == "simulation":
            self.sidebar.setWidget(self._create_simulation_panel())
        else:
            placeholder = QWidget()
            QVBoxLayout(placeholder).addWidget(QLabel(f"{key} 面板（待实现）"))
            self.sidebar.setWidget(placeholder)

    def _update_sidebar_visibility(self):
        # VS Code style: sidebar is always visible next to activity bar
        self.sidebar.show()

    # ────────────────────────────────────────────────────────────────
    # Project Tree
    # ────────────────────────────────────────────────────────────────

    def _refresh_project_tree(self):
        self.project_tree.clear()
        projects = self.project_manager.get_all()
        for project in projects:
            proj_item = QTreeWidgetItem([project.name])
            proj_item.setData(0, Qt.UserRole, {"type": "project", "id": project.id})
            cases = self.case_manager.get_by_project(project.id)
            for case in cases:
                case_item = QTreeWidgetItem([f"{case.name} [{case.status}]"])
                case_item.setData(0, Qt.UserRole, {"type": "case", "id": case.id, "project_id": project.id})
                proj_item.addChild(case_item)
            self.project_tree.addTopLevelItem(proj_item)
        self.project_tree.expandAll()

    def _on_tree_item_double_clicked(self, item, column):
        data = item.data(0, Qt.UserRole)
        if data and data["type"] == "case":
            case = self.case_manager.get_by_id(data["id"])
            if case:
                self.current_case = case
                self.current_project = self.project_manager.get_by_id(data["project_id"])
                self._update_status()
                self.log(f"选中 Case: {case.name}")
                self.solver_combo.setCurrentText(case.solver)
                self.editor_tabs.setCurrentIndex(1)  # 切换到求解运行页

    # ────────────────────────────────────────────────────────────────
    # Project / Case Actions
    # ────────────────────────────────────────────────────────────────

    def _on_new_project(self):
        dialog = NewProjectDialog(self)
        dialog.project_created.connect(self._create_project)
        dialog.exec()

    def _create_project(self, name: str):
        try:
            project = self.project_manager.create(name)
            self._refresh_project_tree()
            self.log(f"项目创建: {name}")
        except Exception as e:
            logger.error(f"创建项目失败: {e}")
            QMessageBox.critical(self, "错误", str(e))

    def _on_new_case(self):
        if not self.current_project:
            QMessageBox.warning(self, "提示", "请先在项目树中选择一个项目")
            return
        templates = self.template_manager.get_all()
        dialog = NewCaseDialog(templates, self)
        dialog.case_created.connect(lambda name, tpath: self._create_case(name, tpath))
        dialog.exec()

    def _create_case(self, name: str, template_path=None):
        try:
            case = self.case_manager.create(self.current_project.id, name, template_path)
            self._refresh_project_tree()
            self.log(f"Case 创建: {name}")
        except Exception as e:
            logger.error(f"创建 Case 失败: {e}")
            QMessageBox.critical(self, "错误", str(e))

    def _on_delete_project(self):
        if not self.current_project:
            QMessageBox.warning(self, "提示", "请先选择要删除的项目")
            return
        reply = QMessageBox.question(self, "确认", f"删除项目 '{self.current_project.name}'？不可恢复。")
        if reply == QMessageBox.Yes:
            try:
                self.project_manager.delete(self.current_project.id)
                self.current_project = None
                self.current_case = None
                self._refresh_project_tree()
                self._update_status()
                self.log("项目已删除")
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))

    def _on_refresh_projects(self):
        self._refresh_project_tree()

    # ────────────────────────────────────────────────────────────────
    # Task Execution
    # ────────────────────────────────────────────────────────────────

    def _on_run_solver(self):
        if not self.current_case:
            QMessageBox.warning(self, "提示", "请先在项目树中选择一个 Case")
            return

        solver = self.solver_combo.currentText()
        self.log(f"启动求解器: {solver}, Case: {self.current_case.name}")

        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        self.task_executor.start_task(self.current_case.id, solver, self.current_case.path)

    def _on_stop_solver(self):
        if self.current_case:
            self.task_executor.stop_task(self.current_case.id)
            self.log("请求停止任务...")

    def _on_task_started(self, case_id: str):
        self.log(f"[开始] case_id={case_id}")

    def _on_task_output(self, case_id: str, line: str):
        self.log_text.append(line)
        self.log_text.moveCursor(QTextCursor.End)

    def _on_task_error(self, case_id: str, line: str):
        self.log_text.append(f"<font color='red'>{line}</font>")
        self.log_text.moveCursor(QTextCursor.End)

    def _on_task_status_changed(self, case_id: str, status: str):
        if self.current_case and self.current_case.id == case_id:
            self.case_manager.update_status(case_id, status)
            self.solver_label.setText(f"求解器: {status}")

    def _on_task_finished(self, case_id: str, returncode: int, stdout: str, stderr: str):
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)

        if returncode == 0:
            self.log(f"[完成] case_id={case_id}")
        else:
            self.log(f"[失败] case_id={case_id}, returncode={returncode}")

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

    # ────────────────────────────────────────────────────────────────
    # Status & Tutorial
    # ────────────────────────────────────────────────────────────────

    def _update_status(self):
        if self.current_project:
            self.case_label.setText(f"项目: {self.current_project.name}")
        else:
            self.case_label.setText("无项目")

        if self.current_case:
            self.solver_label.setText(f"求解器: {self.current_case.solver}")

        if self.of_env.get("of_installed"):
            self.of_label.setText(f"OF: {self.of_env.get('version', 'unknown')}")
        else:
            self.of_label.setText("OF: 未检测到")

    def _show_tutorial_if_needed(self):
        if self.settings_manager.get("show_tutorial_on_startup", True):
            from PySide6.QtCore import QTimer
            QTimer.singleShot(500, self._on_show_tutorial)

    def _on_show_tutorial(self):
        dialog = TutorialDialog(self)
        dialog.closed_permanently.connect(
            lambda: self.settings_manager.update("show_tutorial_on_startup", False)
        )
        dialog.exec()

    def _on_diagnostics(self):
        QMessageBox.information(self, "环境诊断", f"OpenFOAM: {self.of_env.get('message', 'unknown')}")

    def _on_about(self):
        QMessageBox.about(self, "关于", "OFCC - OpenFOAM CFD Client\n版本 0.1.0\n基于 PySide6")

    def log(self, message: str):
        self.log_text.append(f"[INFO] {message}")
        self.log_text.moveCursor(QTextCursor.End)

    def _connect_task_signals(self):
        self.task_executor.task_started.connect(self._on_task_started)
        self.task_executor.task_output.connect(self._on_task_output)
        self.task_executor.task_error.connect(self._on_task_error)
        self.task_executor.task_status.connect(self._on_task_status_changed)
        self.task_executor.task_finished.connect(self._on_task_finished)

    def resizeEvent(self, event):
        """保持活动栏与窗口同步"""
        super().resizeEvent(event)
        if self.activity_bar:
            self.activity_bar.setFixedHeight(self.height() - self.status_bar.height() - 2)
