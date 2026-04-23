import sys
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
