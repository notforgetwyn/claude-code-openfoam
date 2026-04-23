from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QScrollArea, QWidget, QProgressBar
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class TutorialStep:
    def __init__(self, title: str, content: str, image_hint: str = ""):
        self.title = title
        self.content = content
        self.image_hint = image_hint


class TutorialDialog(QDialog):
    """
    新手教程引导对话框。

    流程：
    1. 显示欢迎页
    2. 分步骤引导（项目创建 → Case 创建 → 参数配置 → 运行求解 → 查看结果）
    3. 完成后显示总结

    用户可选择：
    - 永久关闭（写入设置，以后不再自动弹出）
    - 本次关闭（下次启动仍会弹出）
    - 随时从菜单"帮助 → 新手教程"重新打开
    """

    TUTORIAL_STEPS = [
        TutorialStep(
            "第一步：创建项目",
            "1. 点击工具栏「新建项目」或菜单「文件 → 新建项目」\n"
            "2. 输入项目名称（如 myCFD）\n"
            "3. 点击「创建」\n\n"
            "项目会创建在 ~/ofcc_workspace/projects/ 目录下。",
        ),
        TutorialStep(
            "第二步：创建 Case",
            "1. 在左侧项目树中双击选中刚创建的项目\n"
            "2. 点击菜单「项目 → 新建 Case」或工具栏「新建Case」\n"
            "3. 输入 Case 名称，选择求解器（如 simpleFoam）\n"
            "4. 可选择模板（推荐从模板创建）\n"
            "5. 点击「创建」\n\n"
            "Case 会创建在项目的 cases/ 子目录下。",
        ),
        TutorialStep(
            "第三步：配置参数",
            "1. 切换到「参数配置」标签页\n"
            "2. 选择求解器类型\n"
            "3. 配置物理模型（湍流模型、边界条件等）\n"
            "4. 配置时间控制（开始时间、结束时间、时间步）\n"
            "5. 保存配置\n\n"
            "配置文件会写入 Case 的 system/ 目录下。",
        ),
        TutorialStep(
            "第四步：生成网格",
            "1. 在「求解运行」标签页选择「blockMesh」\n"
            "2. 点击「▶ 运行」\n"
            "3. 观察右侧实时日志输出\n"
            "4. 等待「已完成」提示\n\n"
            "blockMesh 会生成基础结构网格。",
        ),
        TutorialStep(
            "第五步：运行求解",
            "1. 在「求解运行」标签页选择「simpleFoam」（或其他求解器）\n"
            "2. 点击「▶ 运行」\n"
            "3. 观察实时日志和收敛曲线\n"
            "4. 点击「■ 停止」可中止任务\n\n"
            "求解过程可能需要几分钟到几小时不等。",
        ),
        TutorialStep(
            "第六步：查看结果",
            "1. 切换到「结果」标签页\n"
            "2. 选择时间目录查看不同时刻的结果\n"
            "3. 可视化压力场、速度场等\n"
            "4. 导出图像或数据\n\n"
            "结果文件保存在 Case 的时间目录中。",
        ),
    ]

    closed_permanently = Signal()
    closed_temporarily = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新手教程 - OpenFOAM CFD Client")
        self.setModal(False)
        self.setMinimumSize(700, 500)
        self.current_step = -1  # -1 = 欢迎页
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # 标题
        self.title_label = QLabel()
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)

        # 进度条
        self.progress = QProgressBar()
        self.progress.setRange(0, len(self.TUTORIAL_STEPS))
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        # 内容区（可滚动）
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.content_text = QTextEdit()
        self.content_text.setReadOnly(True)
        self.content_text.setStyleSheet("border: none; background-color: transparent;")
        scroll.setWidget(self.content_text)
        layout.addWidget(scroll, 1)

        # 按钮区
        btn_layout = QHBoxLayout()

        self.prev_btn = QPushButton("← 上一步")
        self.prev_btn.clicked.connect(self._on_prev)
        self.prev_btn.setEnabled(False)
        btn_layout.addWidget(self.prev_btn)

        self.next_btn = QPushButton("下一步 →")
        self.next_btn.clicked.connect(self._on_next)
        btn_layout.addWidget(self.next_btn)

        btn_layout.addStretch()

        self.close_perm_btn = QPushButton("永久关闭")
        self.close_perm_btn.clicked.connect(self._on_close_permanent)
        btn_layout.addWidget(self.close_perm_btn)

        self.close_btn = QPushButton("本次关闭")
        self.close_btn.clicked.connect(self._on_close_temporary)
        btn_layout.addWidget(self.close_btn)

        layout.addLayout(btn_layout)

        self._show_welcome()

    def _show_welcome(self):
        self.title_label.setText("欢迎使用 OFCC - OpenFOAM CFD Client")
        self.progress.setValue(0)
        self.prev_btn.setEnabled(False)
        self.next_btn.setText("开始教程 →")
        self.content_text.setHtml(
            "<h2>👋 欢迎！</h2>"
            "<p>本教程将引导你完成第一个仿真案例，从创建项目到运行求解器。</p>"
            "<p>预计时间：<b>5-10 分钟</b></p>"
            "<hr>"
            "<p><b>教程内容：</b></p>"
            "<ol>"
            "<li>创建项目</li>"
            "<li>创建 Case</li>"
            "<li>配置仿真参数</li>"
            "<li>生成网格（blockMesh）</li>"
            "<li>运行求解（simpleFoam）</li>"
            "<li>查看结果</li>"
            "</ol>"
            "<hr>"
            "<p><i>提示：随时可以点击「永久关闭」关闭本教程，之后从菜单「帮助 → 新手教程」重新打开。</i></p>"
        )

    def _show_step(self, index: int):
        step = self.TUTORIAL_STEPS[index]
        self.title_label.setText(step.title)
        self.progress.setValue(index + 1)
        self.prev_btn.setEnabled(index > 0)
        self.next_btn.setText("下一步 →" if index < len(self.TUTORIAL_STEPS) - 1 else "完成 ✓")
        self.content_text.setHtml(f"<h3>{step.content}</h3>")

    def _show_complete(self):
        self.title_label.setText("教程完成！🎉")
        self.progress.setValue(len(self.TUTORIAL_STEPS))
        self.prev_btn.setEnabled(len(self.TUTORIAL_STEPS) > 0)
        self.next_btn.setText("重新开始")
        self.next_btn.clicked.disconnect()
        self.next_btn.clicked.connect(self._on_restart)
        self.content_text.setHtml(
            "<h2>✅ 恭喜你完成新手教程！</h2>"
            "<p>你现在已经掌握了 OFCC 的基本操作流程：</p>"
            "<ol>"
            "<li>✅ 创建项目</li>"
            "<li>✅ 创建 Case</li>"
            "<li>✅ 配置参数</li>"
            "<li>✅ 生成网格</li>"
            "<li>✅ 运行求解</li>"
            "<li>✅ 查看结果</li>"
            "</ol>"
            "<hr>"
            "<p><b>下一步：</b>尝试运行你自己的仿真案例！</p>"
            "<p>如需再次查看本教程，请点击菜单「帮助 → 新手教程」。</p>"
        )

    def _on_prev(self):
        if self.current_step > 0:
            self.current_step -= 1
            self._show_step(self.current_step)

    def _on_next(self):
        if self.current_step == -1:
            self.current_step = 0
            self._show_step(0)
        elif self.current_step < len(self.TUTORIAL_STEPS) - 1:
            self.current_step += 1
            self._show_step(self.current_step)
        else:
            self._show_complete()

    def _on_restart(self):
        self.current_step = -1
        self.next_btn.clicked.disconnect()
        self.next_btn.clicked.connect(self._on_next)
        self._show_welcome()

    def _on_close_permanent(self):
        self.closed_permanently.emit()
        self.accept()

    def _on_close_temporary(self):
        self.closed_temporarily.emit()
        self.accept()
