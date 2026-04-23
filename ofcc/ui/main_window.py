from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QDockWidget, QStatusBar, QToolBar, QMenuBar,
    QMessageBox, QTabWidget, QLabel, QTextEdit,
    QTreeWidget, QTreeWidgetItem, QPushButton, QProgressBar,
    QGroupBox, QComboBox, QListWidget, QSplitter,
    QFrame, QSizePolicy, QSpacerItem, QScrollArea,
    QAbstractItemView, QStyledItemDelegate, QStyleOption,
    QStyleFactory,
)
from PySide6.QtCore import Qt, Signal, QSize, QTimer, QEvent
from PySide6.QtGui import QAction, QFont, QColor, QPainter, QBrush, QPalette, QTextCursor

from ofcc.core.project_manager import ProjectManager, Project
from ofcc.core.case_manager import CaseManager, Case
from ofcc.core.template_manager import TemplateManager
from ofcc.core.task_executor import TaskExecutor, TaskStatus
from ofcc.core.settings_manager import SettingsManager
from ofcc.ui.dialogs.new_project_dialog import NewProjectDialog
from ofcc.ui.dialogs.new_case_dialog import NewCaseDialog
from ofcc.ui.dialogs.tutorial_dialog import TutorialDialog
from ofcc.ui.dialogs.settings_dialog import SettingsDialog
from ofcc.infra.logger import get_logger

logger = get_logger(__name__)


class ActivityBar(QFrame):
    """VS Code 风格活动栏"""
    clicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(48)
        self.setFrameShape(QFrame.NoFrame)
        self.buttons = {}
        self._active = "explorer"
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(8)

        icons = [
            ("explorer", "📁"),
            ("search", "🔍"),
            ("git", "🐙"),
            ("simulation", "▶"),
        ]

        for key, emoji in icons:
            btn = QPushButton(emoji)
            btn.setFixedSize(40, 40)
            btn.setFlat(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, k=key: self._on_click(k))
            self.buttons[key] = btn
            layout.addWidget(btn)

        layout.addStretch()

        # 设置按钮放底部
        settings_btn = QPushButton("⚙")
        settings_btn.setFixedSize(40, 40)
        settings_btn.setFlat(True)
        settings_btn.setCursor(Qt.PointingHandCursor)
        settings_btn.clicked.connect(lambda: self.clicked.emit("settings"))
        self.buttons["settings"] = settings_btn
        layout.addWidget(settings_btn)

        self._update_active("explorer")

    def _on_click(self, key: str):
        self._active = key
        self._update_active(key)
        self.clicked.emit(key)

    def _update_active(self, key: str):
        for k, btn in self.buttons.items():
            btn.setStyleSheet(
                "QPushButton { background-color: transparent; border: none; border-radius: 4px; }"
                "QPushButton:hover { background-color: rgba(255,255,255,0.1); }"
                f"QPushButton:checked, QPushButton[active=true] {{ background-color: rgba(255,255,255,0.15); border-left: 2px solid #0078D4; }}"
            ) if key == "dark" else btn.setStyleSheet("")
            btn.setProperty("active", k == key)
            btn.style().unpolish(btn)
            btn.style().polish(btn)


class BreadcrumbBar(QFrame):
    """面包屑导航栏"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(28)
        self.setStyleSheet("background-color: rgba(0,0,0,0.05); border-bottom: 1px solid rgba(0,0,0,0.1);")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        self.label = QLabel("OFCC")
        self.label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.label)

    def set_path(self, project_name: str = None, case_name: str = None):
        if project_name and case_name:
            self.label.setText(f"OFCC › {project_name} › {case_name}")
        elif project_name:
            self.label.setText(f"OFCC › {project_name}")
        else:
            self.label.setText("OFCC")


class MainWindow(QMainWindow):

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

        self._connect_task_signals()
        self._apply_theme()
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
    # Theme
    # ───────────────────────────────────────────────────────────────

    def _apply_theme(self):
        theme = self.settings_manager.get("theme", "浅色")
        if theme == "深色":
            self.setStyleSheet(self._dark_stylesheet())
            self.setPalette(self._dark_palette())
        elif theme == "浅色":
            self.setStyleSheet(self._light_stylesheet())
            self.setPalette(self._light_palette())
        else:
            # 跟随系统，使用浅色
            self.setStyleSheet(self._light_stylesheet())

    def _light_palette(self) -> QPalette:
        p = self.palette()
        p.setColor(QPalette.Window, QColor("#FFFFFF"))
        p.setColor(QPalette.WindowText, QColor("#333333"))
        p.setColor(QPalette.Base, QColor("#FFFFFF"))
        p.setColor(QPalette.AlternateBase, QColor("#F5F5F5"))
        p.setColor(QPalette.ToolTipBase, QColor("#FFFFEC"))
        p.setColor(QPalette.Text, QColor("#333333"))
        p.setColor(QPalette.Button, QColor("#F0F0F0"))
        p.setColor(QPalette.ButtonText, QColor("#333333"))
        p.setColor(QPalette.BrightText, QColor("#FFFFFF"))
        p.setColor(QPalette.Highlight, QColor("#0078D4"))
        p.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
        return p

    def _dark_palette(self) -> QPalette:
        p = self.palette()
        p.setColor(QPalette.Window, QColor("#1E1E1E"))
        p.setColor(QPalette.WindowText, QColor("#CCCCCC"))
        p.setColor(QPalette.Base, QColor("#252526"))
        p.setColor(QPalette.AlternateBase, QColor("#2D2D30"))
        p.setColor(QPalette.ToolTipBase, QColor("#3E3E42"))
        p.setColor(QPalette.Text, QColor("#CCCCCC"))
        p.setColor(QPalette.Button, QColor("#3C3C3C"))
        p.setColor(QPalette.ButtonText, QColor("#CCCCCC"))
        p.setColor(QPalette.BrightText, QColor("#FFFFFF"))
        p.setColor(QPalette.Highlight, QColor("#0078D4"))
        p.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
        return p

    def _light_stylesheet(self) -> str:
        return """
            QMainWindow { background-color: #FFFFFF; }
            QWidget { font-family: "Microsoft YaHei", "Segoe UI", sans-serif; font-size: 10pt; }
            QLabel { color: #333333; }
            QPushButton {
                background-color: #F0F0F0; border: 1px solid #CCCCCC;
                border-radius: 4px; padding: 4px 12px; color: #333333;
            }
            QPushButton:hover { background-color: #E0E0E0; }
            QPushButton:pressed { background-color: #D0D0D0; }
            QPushButton:disabled { background-color: #F5F5F5; color: #AAAAAA; }
            QComboBox {
                background-color: #FFFFFF; border: 1px solid #CCCCCC;
                border-radius: 4px; padding: 2px 8px;
            }
            QComboBox:hover { border-color: #0078D4; }
            QGroupBox { border: 1px solid #DDDDDD; border-radius: 4px; margin-top: 8px; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; color: #333333; }
            QTabWidget::pane { border: 1px solid #DDDDDD; }
            QTabBar::tab {
                background-color: #F0F0F0; border: 1px solid #DDDDDD;
                padding: 6px 16px; margin-right: 2px;
            }
            QTabBar::tab:selected { background-color: #FFFFFF; border-bottom: 2px solid #0078D4; }
            QTabBar::tab:hover { background-color: #E8E8E8; }
            QProgressBar { border: 1px solid #CCCCCC; border-radius: 4px; text-align: center; }
            QProgressBar::chunk { background-color: #0078D4; border-radius: 3px; }
            QTreeWidget, QListWidget {
                background-color: #FFFFFF; border: 1px solid #DDDDDD;
                outline: none;
            }
            QTreeWidget::item:hover, QListWidget::item:hover { background-color: #F0F0F0; }
            QTreeWidget::item:selected, QListWidget::item:selected { background-color: #0078D4; color: white; }
            QDockWidget { border: 1px solid #DDDDDD; }
            QStatusBar { background-color: #F0F0F0; color: #666666; }
            QMenuBar { background-color: #F0F0F0; border-bottom: 1px solid #DDDDDD; }
            QMenuBar::item { padding: 4px 12px; }
            QMenuBar::item:selected { background-color: #E0E0E0; }
            QMenu { background-color: #FFFFFF; border: 1px solid #DDDDDD; }
            QMenu::item:selected { background-color: #0078D4; color: white; }
            QSplitter::handle { background-color: #DDDDDD; }
            QToolBar { background-color: #F5F5F5; border-bottom: 1px solid #DDDDDD; spacing: 4px; }
            QToolTip { background-color: #FFFFEC; border: 1px solid #DDDDDD; color: #333333; }
            QTextEdit { background-color: #FFFFFF; border: 1px solid #DDDDDD; color: #333333; }
            QScrollBar:vertical { width: 10px; background: #F0F0F0; }
            QScrollBar::handle:vertical { background: #C0C0C0; border-radius: 4px; }
            QScrollBar::handle:vertical:hover { background: #A0A0A0; }
        """

    def _dark_stylesheet(self) -> str:
        return """
            QMainWindow { background-color: #1E1E1E; color: #CCCCCC; }
            QWidget { font-family: "Microsoft YaHei", "Segoe UI", sans-serif; font-size: 10pt; color: #CCCCCC; }
            QPushButton {
                background-color: #3C3C3C; border: 1px solid #555555;
                border-radius: 4px; padding: 4px 12px; color: #CCCCCC;
            }
            QPushButton:hover { background-color: #4A4A4A; }
            QPushButton:pressed { background-color: #505050; }
            QPushButton:disabled { background-color: #2D2D2D; color: #666666; }
            QComboBox {
                background-color: #2D2D2D; border: 1px solid #555555;
                border-radius: 4px; padding: 2px 8px; color: #CCCCCC;
            }
            QComboBox:hover { border-color: #0078D4; }
            QGroupBox { border: 1px solid #555555; border-radius: 4px; margin-top: 8px; font-weight: bold; color: #CCCCCC; }
            QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; color: #CCCCCC; }
            QTabWidget::pane { border: 1px solid #3C3C3C; background-color: #1E1E1E; }
            QTabBar::tab {
                background-color: #2D2D2D; border: 1px solid #3C3C3C;
                padding: 6px 16px; margin-right: 2px; color: #AAAAAA;
            }
            QTabBar::tab:selected { background-color: #1E1E1E; border-bottom: 2px solid #0078D4; color: #FFFFFF; }
            QTabBar::tab:hover { background-color: #383838; }
            QProgressBar { border: 1px solid #555555; border-radius: 4px; text-align: center; background-color: #2D2D2D; }
            QProgressBar::chunk { background-color: #0078D4; border-radius: 3px; }
            QTreeWidget, QListWidget {
                background-color: #252526; border: 1px solid #3C3C3C;
                color: #CCCCCC; outline: none;
            }
            QTreeWidget::item:hover, QListWidget::item:hover { background-color: #2A2D2E; }
            QTreeWidget::item:selected, QListWidget::item:selected { background-color: #094771; color: white; }
            QDockWidget { border: 1px solid #3C3C3C; background-color: #252526; color: #CCCCCC; }
            QStatusBar { background-color: #007ACC; color: #FFFFFF; }
            QMenuBar { background-color: #2D2D30; border-bottom: 1px solid #3C3C3C; color: #CCCCCC; }
            QMenuBar::item { padding: 4px 12px; }
            QMenuBar::item:selected { background-color: #3E3E42; }
            QMenu { background-color: #2D2D2D; border: 1px solid #555555; color: #CCCCCC; }
            QMenu::item:selected { background-color: #094771; color: white; }
            QSplitter::handle { background-color: #3C3C3C; }
            QToolBar { background-color: #2D2D30; border-bottom: 1px solid #3C3C3C; spacing: 4px; }
            QToolTip { background-color: #3E3E42; border: 1px solid #555555; color: #CCCCCC; }
            QTextEdit { background-color: #1E1E1E; border: 1px solid #3C3C3C; color: #CCCCCC; }
            QScrollBar:vertical { width: 10px; background: #2D2D2D; }
            QScrollBar::handle:vertical { background: #424242; border-radius: 4px; }
            QScrollBar::handle:vertical:hover { background: #4F4F4F; }
        """

    def _get_font(self) -> QFont:
        family = self.settings_manager.get("font_family", "Microsoft YaHei")
        size = self.settings_manager.get("font_size", 10)
        font = QFont(family, size)
        return font

    # ────────────────────────────────────────────────────────────────
    # Setup
    # ───────────────────────────────────────────────────────────────

    def _setup_ui(self):
        self.setWindowTitle("OFCC - OpenFOAM CFD Client")
        self.setMinimumSize(1200, 800)
        self.setFont(self._get_font())

        central = QWidget()
        self.setCentralWidget(central)
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        # 主分割器（侧边栏 + 编辑器）
        self.main_splitter = QSplitter(Qt.Horizontal)

        # 侧边栏
        self.sidebar = QDockWidget()
        self.sidebar.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.sidebar.setTitleBarWidget(QWidget())
        self.main_splitter.addWidget(self.sidebar)

        # 编辑器容器
        self.editor_container = QWidget()
        editor_vbox = QVBoxLayout(self.editor_container)
        editor_vbox.setContentsMargins(0, 0, 0, 0)
        editor_vbox.setSpacing(0)

        # 面包屑
        self.breadcrumb = BreadcrumbBar()
        editor_vbox.addWidget(self.breadcrumb)

        # 选项卡
        self.editor_tabs = QTabWidget()
        self.editor_tabs.addTab(self._create_config_page(), "⚙ 参数配置")
        self.editor_tabs.addTab(self._create_run_page(), "▶ 求解运行")
        self.editor_tabs.addTab(self._create_log_page(), "📋 日志")
        self.editor_tabs.addTab(self._create_result_page(), "📊 结果")
        editor_vbox.addWidget(self.editor_tabs)

        self.main_splitter.addWidget(self.editor_container)

        # 右侧属性栏
        self.right_sidebar = QDockWidget()
        self.right_sidebar.setFeatures(QDockWidget.NoDockWidgetFeatures | QDockWidget.DockWidgetClosable)
        self.right_sidebar.setMaximumWidth(260)
        self._setup_right_sidebar()
        self.addDockWidget(Qt.RightDockWidgetArea, self.right_sidebar)

        # 底部面板
        self.panel_dock = QDockWidget()
        self.panel_dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.panel_dock.setTitleBarWidget(QWidget())
        self.addDockWidget(Qt.BottomDockWidgetArea, self.panel_dock)

        central_layout.addWidget(self.main_splitter)

        self.main_splitter.setSizes([240, 900])

    def _setup_activity_bar(self):
        self.activity_bar = ActivityBar()
        self.activity_bar.clicked.connect(self._on_activity_click)
        self.activity_bar.setParent(self)
        self.activity_bar.show()

    def _setup_sidebar(self):
        self.sidebar_stack = []
        self._show_sidebar_panel("explorer")

    def _on_activity_click(self, key: str):
        if key == "settings":
            self._on_settings()
            return
        self.active_panel = key
        self._show_sidebar_panel(key)

    def _show_sidebar_panel(self, key: str):
        for i in range(self.sidebar_stack.__len__()):
            w = self.sidebar_stack[i]
            if w:
                w.hide()
        if key == "explorer":
            panel = self._create_explorer_panel()
        elif key == "search":
            panel = self._create_search_panel()
        elif key == "git":
            panel = self._create_git_panel()
        elif key == "simulation":
            panel = self._create_simulation_panel()
        else:
            panel = QWidget()
            QVBoxLayout(panel).addWidget(QLabel(f"{key} 面板"))
        self.sidebar.setWidget(panel)
        self.sidebar.show()

    def _create_explorer_panel(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # 标题行
        title_row = QHBoxLayout()
        title = QLabel("项目浏览器")
        title.setStyleSheet("font-weight: bold; font-size: 11px; color: #666;")
        title_row.addWidget(title)
        title_row.addStretch()

        refresh_btn = QPushButton("↻")
        refresh_btn.setFixedSize(22, 22)
        refresh_btn.setFlat(True)
        refresh_btn.setToolTip("刷新")
        refresh_btn.clicked.connect(self._on_refresh_projects)
        title_row.addWidget(refresh_btn)
        layout.addLayout(title_row)

        # 操作按钮
        btn_row = QHBoxLayout()
        new_proj = QPushButton("新建项目")
        new_proj.setFixedHeight(24)
        new_proj.clicked.connect(self._on_new_project)
        new_case = QPushButton("新建Case")
        new_case.setFixedHeight(24)
        new_case.clicked.connect(self._on_new_case)
        btn_row.addWidget(new_proj)
        btn_row.addWidget(new_case)
        layout.addLayout(btn_row)

        # 项目树
        self.project_tree = QTreeWidget()
        self.project_tree.setHeaderLabel("")
        self.project_tree.setAlternatingRowColors(True)
        self.project_tree.itemDoubleClicked.connect(self._on_tree_item_double_clicked)
        self.project_tree.setIndentation(16)
        self.project_tree.setRootIsDecorated(True)
        layout.addWidget(self.project_tree)

        return widget

    def _create_search_panel(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        search_label = QLabel("搜索面板（Ctrl+Shift+F）")
        search_label.setAlignment(Qt.AlignCenter)
        search_label.setStyleSheet("color: #999; padding: 20px;")
        layout.addWidget(search_label)
        layout.addStretch()
        return widget

    def _create_git_panel(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        git_label = QLabel("Git 面板")
        git_label.setAlignment(Qt.AlignCenter)
        git_label.setStyleSheet("color: #999; padding: 20px;")
        layout.addWidget(git_label)
        layout.addStretch()
        return widget

    def _create_simulation_panel(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        sim_label = QLabel("仿真控制面板")
        sim_label.setAlignment(Qt.AlignCenter)
        sim_label.setStyleSheet("color: #999; padding: 20px;")
        layout.addWidget(sim_label)
        layout.addStretch()
        return widget

    def _setup_right_sidebar(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)

        title = QLabel("属性")
        title.setStyleSheet("font-weight: bold; font-size: 11px; color: #666; border-bottom: 1px solid #DDD; padding-bottom: 4px;")
        layout.addWidget(title)

        self.props_label = QLabel("选择 Case 查看属性")
        self.props_label.setStyleSheet("color: #999; font-size: 9pt;")
        layout.addWidget(self.props_label)
        layout.addStretch()

        self.right_sidebar.setWidget(widget)

    def _setup_editor_tabs(self):
        pass  # 已在上方 _setup_ui 中处理

    def _create_config_page(self) -> QWidget:
        from ofcc.core.parameter_manager import ParameterManager
        from ofcc.core.config_generator import ConfigGenerator
        self.param_manager = ParameterManager()

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ── 求解器 ──
        solver_group = QGroupBox("求解器设置")
        solver_layout = QGridLayout()

        self.solver_type_combo = QComboBox()
        self.solver_type_combo.addItems([s[0] for s in self.param_manager.SOLVERS])
        self.solver_type_combo.setCurrentText("simpleFoam")
        solver_layout.addWidget(QLabel("求解器:"), 0, 0)
        solver_layout.addWidget(self.solver_type_combo, 0, 1)

        self.turbulence_combo = QComboBox()
        self.turbulence_combo.addItems([t[0] for t in self.param_manager.TURBULENCE_MODELS])
        self.turbulence_combo.setCurrentText("kEpsilon")
        solver_layout.addWidget(QLabel("湍流模型:"), 1, 0)
        solver_layout.addWidget(self.turbulence_combo, 1, 1)
        solver_group.setLayout(solver_layout)
        layout.addWidget(solver_group)

        # ── 时间控制 ──
        time_group = QGroupBox("时间控制")
        time_layout = QGridLayout()

        self.start_time = self._make_spinbox(0, 1e6, 0)
        self.end_time = self._make_spinbox(1000, 1e8, 1)
        self.delta_t = self._make_spinbox(0.001, 100, 0.001)
        self.write_interval = self._make_spinbox(1, 1e6, 100)

        time_layout.addWidget(QLabel("开始时间 (s):"), 0, 0)
        time_layout.addWidget(self.start_time, 0, 1)
        time_layout.addWidget(QLabel("结束时间 (s):"), 0, 2)
        time_layout.addWidget(self.end_time, 0, 3)
        time_layout.addWidget(QLabel("时间步长 (s):"), 1, 0)
        time_layout.addWidget(self.delta_t, 1, 1)
        time_layout.addWidget(QLabel("输出间隔:"), 1, 2)
        time_layout.addWidget(self.write_interval, 1, 3)
        time_group.setLayout(time_layout)
        layout.addWidget(time_group)

        # ── 保存/加载 ──
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("💾 保存配置")
        save_btn.clicked.connect(self._on_save_config)
        load_btn = QPushButton("📂 加载配置")
        load_btn.clicked.connect(self._on_load_config)
        apply_btn = QPushButton("⚙ 应用到 Case")
        apply_btn.clicked.connect(self._on_apply_config)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(load_btn)
        btn_layout.addWidget(apply_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # ── 状态提示 ──
        self.config_status = QLabel("请先选择 Case，再配置参数")
        self.config_status.setStyleSheet("color: #999; padding: 4px;")
        layout.addWidget(self.config_status)

        layout.addStretch()
        return widget

    def _make_spinbox(self, min_val: float, max_val: float, default: float):
        from PySide6.QtWidgets import QDoubleSpinBox, QSpinBox
        if isinstance(default, int):
            sb = QSpinBox()
            sb.setRange(int(min_val), int(max_val))
            sb.setValue(int(default))
        else:
            sb = QDoubleSpinBox()
            sb.setRange(min_val, max_val)
            sb.setDecimals(6)
            sb.setValue(float(default))
            sb.setSingleStep(max(default * 0.1, 0.001))
        return sb

    def _on_save_config(self):
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "保存配置", "case_config.yaml", "YAML Files (*.yaml *.yml)")
        if path:
            import yaml
            params = {
                "solver": self.solver_type_combo.currentText(),
                "turbulence": self.turbulence_combo.currentText(),
                "startTime": self.start_time.value(),
                "endTime": self.end_time.value(),
                "deltaT": self.delta_t.value(),
                "writeInterval": self.write_interval.value(),
            }
            with open(path, "w") as f:
                yaml.dump(params, f)
            self.log(f"配置已保存: {path}")

    def _on_load_config(self):
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self, "加载配置", "", "YAML Files (*.yaml *.yml)")
        if path:
            import yaml
            with open(path) as f:
                params = yaml.safe_load(f)
            self.solver_type_combo.setCurrentText(params.get("solver", "simpleFoam"))
            self.turbulence_combo.setCurrentText(params.get("turbulence", "kEpsilon"))
            self.start_time.setValue(params.get("startTime", 0))
            self.end_time.setValue(params.get("endTime", 1000))
            self.delta_t.setValue(params.get("deltaT", 1))
            self.write_interval.setValue(params.get("writeInterval", 100))
            self.log(f"配置已加载: {path}")

    def _on_apply_config(self):
        if not self.current_case:
            QMessageBox.warning(self, "提示", "请先选择 Case")
            return
        try:
            gen = ConfigGenerator(self.current_case.path)
            gen.generate_all(
                solver=self.solver_type_combo.currentText(),
                turbulence=self.turbulence_combo.currentText(),
                start_time=self.start_time.value(),
                end_time=self.end_time.value(),
                delta_t=self.delta_t.value(),
                write_interval=self.write_interval.value(),
            )
            self.case_manager.update_solver(self.current_case.id, self.solver_type_combo.currentText())
            self.config_status.setText(f"✅ 配置已应用: {self.current_case.name}")
            self.log(f"配置已应用: solver={self.solver_type_combo.currentText()}, turbulence={self.turbulence_combo.currentText()}")
        except Exception as e:
            logger.error(e)
            QMessageBox.critical(self, "错误", str(e))

    def _load_case_config(self, case):
        """加载 Case 的现有配置到表单"""
        import re
        control = case.path / "system" / "controlDict"
        self.config_status.setText(f"当前 Case: {case.name}")
        if control.exists():
            content = control.read_text()
            # 解析关键参数
            def extract(key):
                m = re.search(rf'{key}\s+([^;]+);', content)
                return m.group(1).strip() if m else None

            solver = extract("application")
            start = extract("startTime")
            end = extract("endTime")
            dt = extract("deltaT")
            wi = extract("writeInterval")

            if solver:
                self.solver_type_combo.setCurrentText(solver)
            if start:
                try:
                    self.start_time.setValue(float(start))
                except: pass
            if end:
                try:
                    self.end_time.setValue(float(end))
                except: pass
            if dt:
                try:
                    self.delta_t.setValue(float(dt))
                except: pass
            if wi:
                try:
                    self.write_interval.setValue(int(float(wi)))
                except: pass
            self.log(f"已加载 Case 配置: {case.name}")

    def _create_run_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)

        # 控制条
        ctrl = QGroupBox("求解运行控制")
        ctrl_layout = QHBoxLayout()

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
        self.progress_bar.setVisible(False)

        ctrl_layout.addWidget(QLabel("求解器:"))
        ctrl_layout.addWidget(self.solver_combo)
        ctrl_layout.addWidget(self.run_btn)
        ctrl_layout.addWidget(self.stop_btn)
        ctrl_layout.addWidget(self.progress_bar)
        ctrl_layout.addStretch()
        ctrl.setLayout(ctrl_layout)
        layout.addWidget(ctrl)

        # 运行日志
        log_label = QLabel("运行日志")
        log_label.setStyleSheet("font-weight: bold; color: #666; padding: 4px 0;")
        layout.addWidget(log_label)
        self.run_log = QTextEdit()
        self.run_log.setReadOnly(True)
        self.run_log.setFont(QFont("Consolas", 9))
        layout.addWidget(self.run_log)
        return widget

    def _create_log_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)

        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("日志"))
        toolbar.addStretch()
        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(lambda: self.log_text.clear())
        export_btn = QPushButton("导出")
        export_btn.clicked.connect(self._on_export_log)
        toolbar.addWidget(clear_btn)
        toolbar.addWidget(export_btn)
        layout.addLayout(toolbar)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        layout.addWidget(self.log_text)
        return widget

    def _create_result_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        placeholder = QLabel("结果可视化")
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet("color: #999; font-size: 14pt; padding: 40px;")
        layout.addWidget(placeholder)
        layout.addStretch()
        return widget

    def _setup_panel(self):
        self.panel_widget = QWidget()
        panel_layout = QVBoxLayout(self.panel_widget)
        panel_layout.setContentsMargins(0, 0, 0, 0)

        self.panel_tabs = QTabWidget()
        self.panel_tabs.setTabsClosable(False)
        self.panel_tabs.addTab(self.log_text, "终端")
        self.panel_tabs.addTab(QListWidget(), "问题 (0)")
        self.panel_tabs.setMaximumHeight(180)
        panel_layout.addWidget(self.panel_tabs)

        self.panel_dock.setWidget(self.panel_widget)

    def _setup_statusbar(self):
        sb = QStatusBar()
        self.setStatusBar(sb)

        self.branch_label = QLabel("  OFCC")
        self.case_label = QLabel("未选择 Case")
        self.solver_label = QLabel("求解器: -")
        self.of_label = QLabel(f"OF: {self.of_env.get('version', '?')}")

        for lbl in [self.branch_label, self.case_label, self.solver_label, self.of_label]:
            sb.addPermanentWidget(lbl)

    def _setup_menu(self):
        mb = self.menuBar()

        file_menu = mb.addMenu("文件")
        file_menu.addAction("新建项目", self._on_new_project)
        file_menu.addAction("刷新项目", self._on_refresh_projects)
        file_menu.addSeparator()
        file_menu.addAction("退出", self.close)

        proj_menu = mb.addMenu("项目")
        proj_menu.addAction("新建 Case", self._on_new_case)
        proj_menu.addAction("删除项目", self._on_delete_project)

        solver_menu = mb.addMenu("求解器")
        solver_menu.addAction("运行求解", self._on_run_solver)
        solver_menu.addAction("停止求解", self._on_stop_solver)

        tool_menu = mb.addMenu("工具")
        tool_menu.addAction("设置...", self._on_settings)
        tool_menu.addAction("环境诊断", self._on_diagnostics)

        help_menu = mb.addMenu("帮助")
        help_menu.addAction("新手教程", self._on_show_tutorial)
        help_menu.addSeparator()
        help_menu.addAction("关于", self._on_about)

    # ────────────────────────────────────────────────────────────────
    # Project Tree
    # ────────────────────────────────────────────────────────────────

    def _refresh_project_tree(self):
        self.project_tree.clear()
        projects = self.project_manager.get_all()
        for proj in projects:
            proj_item = QTreeWidgetItem([f"📁 {proj.name}"])
            proj_item.setData(0, Qt.UserRole, {"type": "project", "id": proj.id})
            cases = self.case_manager.get_by_project(proj.id)
            for case in cases:
                status_icon = "✅" if case.status == "completed" else "⏳" if case.status == "running" else "⏸"
                case_item = QTreeWidgetItem([f"  {status_icon} {case.name}"])
                case_item.setData(0, Qt.UserRole, {"type": "case", "id": case.id, "project_id": proj.id})
                proj_item.addChild(case_item)
            self.project_tree.addTopLevelItem(proj_item)
        self.project_tree.expandAll()
        self.log(f"项目树已刷新 ({len(projects)} 个项目)")

    def _on_tree_item_double_clicked(self, item, column):
        data = item.data(0, Qt.UserRole)
        if data and data["type"] == "case":
            case = self.case_manager.get_by_id(data["id"])
            if case:
                self.current_case = case
                self.current_project = self.project_manager.get_by_id(data["project_id"])
                self._update_status()
                self._update_properties()
                self.solver_combo.setCurrentText(case.solver)
                self._load_case_config(case)
                self.editor_tabs.setCurrentIndex(0)  # 切换到参数配置页
                self.log(f"选中 Case: {case.name} ({case.solver})")

    def _update_properties(self):
        if self.current_case:
            self.props_label.setText(
                f"<b>{self.current_case.name}</b><br>"
                f"求解器: {self.current_case.solver}<br>"
                f"状态: {self.current_case.status}<br>"
                f"路径: {self.current_case.path}"
            )
        else:
            self.props_label.setText("选择 Case 查看属性")

    # ────────────────────────────────────────────────────────────────
    # Actions
    # ────────────────────────────────────────────────────────────────

    def _on_new_project(self):
        dialog = NewProjectDialog(self)
        dialog.project_created.connect(self._create_project)
        dialog.exec()

    def _create_project(self, name: str):
        try:
            self.project_manager.create(name)
            self._refresh_project_tree()
            self.log(f"项目已创建: {name}")
        except Exception as e:
            logger.error(e)
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
            self.case_manager.create(self.current_project.id, name, template_path)
            self._refresh_project_tree()
            self.log(f"Case 已创建: {name}")
        except Exception as e:
            logger.error(e)
            QMessageBox.critical(self, "错误", str(e))

    def _on_delete_project(self):
        if not self.current_project:
            QMessageBox.warning(self, "提示", "请先选择要删除的项目")
            return
        reply = QMessageBox.question(self, "确认", f"删除项目 '{self.current_project.name}'？不可恢复。")
        if reply == QMessageBox.Yes:
            self.project_manager.delete(self.current_project.id)
            self.current_project = None
            self.current_case = None
            self._refresh_project_tree()
            self._update_status()
            self.log("项目已删除")

    def _on_refresh_projects(self):
        self._refresh_project_tree()

    def _on_run_solver(self):
        if not self.current_case:
            QMessageBox.warning(self, "提示", "请先选择 Case")
            return
        solver = self.solver_combo.currentText()
        self.log(f"▶ 启动 {solver} (Case: {self.current_case.name})")
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(20)
        self.task_executor.start_task(self.current_case.id, solver, self.current_case.path)

    def _on_stop_solver(self):
        if self.current_case:
            self.task_executor.stop_task(self.current_case.id)
            self.log("■ 请求停止...")

    def _on_task_started(self, case_id: str):
        self.log(f"[任务开始] case={case_id}")

    def _on_task_output(self, case_id: str, line: str):
        self.run_log.append(line)
        self.log_text.append(line)
        self.run_log.moveCursor(QTextCursor.End)

    def _on_task_error(self, case_id: str, line: str):
        self.run_log.append(f"<font color='red'>{line}</font>")
        self.log_text.append(f"<font color='red'>{line}</font>")

    def _on_task_status_changed(self, case_id: str, status: str):
        if self.current_case and self.current_case.id == case_id:
            self.case_manager.update_status(case_id, status)
            self._refresh_project_tree()

    def _on_task_finished(self, case_id: str, rc: int, out: str, err: str):
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        if rc == 0:
            self.log(f"✅ 完成 case={case_id}")
        else:
            self.log(f"❌ 失败 case={case_id} rc={rc}")
        if self.current_case and self.current_case.id == case_id:
            self.case_manager.update_status(case_id, "completed" if rc == 0 else "failed")
            self._refresh_project_tree()

    def _on_export_log(self):
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "导出日志", "ofcc_log.txt", "Text Files (*.txt)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.log_text.toPlainText())
            self.log(f"日志已导出: {path}")

    def _on_settings(self):
        dialog = SettingsDialog(self.settings_manager.get_all(), self)
        dialog.settings_changed.connect(self._on_settings_applied)
        dialog.exec()

    def _on_settings_applied(self, settings: dict):
        for key, value in settings.items():
            self.settings_manager.update(key, value)
        self._apply_theme()
        self.setFont(self._get_font())
        self.log("设置已应用")

    def _update_status(self):
        if self.current_project:
            self.breadcrumb.set_path(self.current_project.name, self.current_case.name if self.current_case else None)
            self.case_label.setText(f"项目: {self.current_project.name}")
        else:
            self.breadcrumb.set_path()
            self.case_label.setText("未选择 Case")
        if self.current_case:
            self.solver_label.setText(f"求解器: {self.current_case.solver}")

    def _show_tutorial_if_needed(self):
        if self.settings_manager.get("show_tutorial_on_startup", True):
            QTimer.singleShot(500, self._on_show_tutorial)

    def _on_show_tutorial(self):
        dialog = TutorialDialog(self)
        dialog.closed_permanently.connect(
            lambda: self.settings_manager.update("show_tutorial_on_startup", False)
        )
        dialog.exec()

    def _on_diagnostics(self):
        QMessageBox.information(self, "环境诊断", f"OpenFOAM: {self.of_env.get('message', '')}")

    def _on_about(self):
        QMessageBox.about(self, "关于", "OFCC - OpenFOAM CFD Client\n版本 0.2.0\n基于 PySide6")

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
        super().resizeEvent(event)
        if self.activity_bar:
            self.activity_bar.setFixedHeight(self.height() - self.statusBar().height() - 2)
