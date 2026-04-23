# OFCC - OpenFOAM CFD Client

基于 Python + PySide6 的 OpenFOAM 流体力学仿真桌面客户端。

## 环境要求

- Python 3.10+
- PySide6 >= 6.6.0
- OpenFOAM（已安装并 source 环境脚本）
- WSL / Linux 图形环境

## 安装依赖

```bash
cd /home/shihuayue/claude_project
pip install -r requirements.txt --break-system-packages
```

## 启动

```bash
OPEN_openfoam
```

或手动启动：

```bash
cd /home/shihuayue && PYTHONPATH=/home/shihuayue/claude_project DISPLAY=:0 python3 claude_project/ofcc/main.py
```

## 项目结构

```
ofcc/
├── main.py              # 入口
├── ui/                  # UI 层
│   ├── main_window.py   # 主窗口
│   ├── dialogs/         # 对话框
│   │   ├── new_project_dialog.py
│   │   └── new_case_dialog.py
│   └── pages/           # 页面
├── core/                # 核心业务层
│   ├── project_manager.py    # 项目管理
│   ├── case_manager.py       # Case 管理
│   ├── template_manager.py   # 模板管理
│   └── settings_manager.py  # 设置管理
├── ofcc/               # OpenFOAM 集成层
│   ├── environment.py   # 环境检测
│   └── command_runner.py # 命令执行
├── core/               # 核心业务层
│   ├── task_executor.py  # 任务执行器
├── infra/               # 基础设施层
│   ├── logger.py        # 日志模块
│   └── database.py       # SQLite 数据库
└── requirements.txt

~/.ofcc/                 # 用户配置（自动创建）
├── database.db          # SQLite 数据库
└── settings.yaml        # 用户设置

~/ofcc_workspace/       # 工作空间（自动创建）
├── projects/            # 项目目录
└── templates/           # Case 模板
```

## 功能进度

- [x] Sprint 0: 工程骨架搭建 - 主窗口、菜单、工具栏、状态栏、OpenFOAM 环境检测
- [x] Sprint 1: 项目管理 + Case 管理 + 本地存储 - 项目增删改查、Case 生命周期、SQLite 数据库、模板管理
- [x] Sprint 2: OpenFOAM 命令调用 + 任务执行 - SubprocessRunner、QThread 任务执行器、实时日志
- [ ] Sprint 3: 参数配置表单 + 配置文件生成
- [ ] Sprint 4: 日志面板 + 结果管理
- [ ] Sprint 5: 可视化 + 打包发布

## 技术栈

- **GUI**: PySide6 (Qt for Python)
- **数据库**: SQLite
- **配置**: YAML
- **可视化**: pyvista + VTK
- **测试**: pytest + pytest-qt
- **代码质量**: ruff

## Git

```bash
git add -A
git commit -m "your message"
git push
```

## License

MIT
