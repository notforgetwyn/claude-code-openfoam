import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from PySide6.QtWidgets import QApplication, QMessageBox
from ofcc.ui.main_window import MainWindow
from ofcc.infra.logger import setup_logger
from ofcc.ofcc.environment import OFEnvironment


def main():
    setup_logger()
    of_env = OFEnvironment.check()
    app = QApplication(sys.argv)
    app.setApplicationName("OFCC")
    app.setOrganizationName("OFCC")

    if not of_env["of_installed"]:
        QMessageBox.warning(
            None,
            "警告",
            f"OpenFOAM 未检测到: {of_env['message']}\n"
            "请确保 OpenFOAM 已正确安装并 source 了环境脚本。",
        )

    window = MainWindow(of_env)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
