# OFCC - OpenFOAM CFD Client

基于 Python + PySide6 的 OpenFOAM 流体力学仿真桌面客户端。

## 环境要求

- Python 3.10+
- PySide6 >= 6.6.0
- OpenFOAM（已安装并 source 环境脚本）
- WSL / Linux 图形环境

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行

```bash
python ofcc/main.py
```

## 项目结构

```
ofcc/
├── main.py              # 入口
├── ui/                  # UI 层
│   ├── main_window.py   # 主窗口
│   ├── dialogs/         # 对话框
│   ├── widgets/         # 自定义控件
│   └── pages/           # 页面
├── core/                # 核心业务层
├── ofcc/               # OpenFOAM 集成层
│   └── environment.py   # 环境检测
├── infra/               # 基础设施层
│   └── logger.py        # 日志模块
├── visualization/       # 可视化层
└── utils/               # 工具
```

## 功能进度

- [x] Sprint 0: 工程骨架搭建
- [ ] Sprint 1: 项目管理 + Case 管理 + 本地存储
- [ ] Sprint 2: OpenFOAM 命令调用 + 任务执行
- [ ] Sprint 3: 参数配置表单 + 配置文件生成
- [ ] Sprint 4: 日志面板 + 结果管理
- [ ] Sprint 5: 可视化 + 打包发布

## License

MIT
