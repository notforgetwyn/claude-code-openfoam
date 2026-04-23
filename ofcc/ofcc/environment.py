import subprocess
import shutil
from pathlib import Path
from typing import Dict
from ofcc.infra.logger import get_logger

logger = get_logger(__name__)


class OFEnvironment:
    OF_BASHRC_PATHS = [
        "/opt/openfoam10/etc/bashrc",
        "/opt/openfoam9/etc/bashrc",
        "/opt/openfoam8/etc/bashrc",
        "/usr/lib/openfoam/etc/bashrc",
        "$HOME/OpenFOAM/OpenFOAM-10/etc/bashrc",
        "/home/shihuayue/openfoam/OpenFOAM-dev/etc/bashrc",
    ]

    @classmethod
    def find_bashrc(cls) -> str | None:
        for path in cls.OF_BASHRC_PATHS:
            expanded = path.replace("$HOME", str(Path.home()))
            if Path(expanded).exists():
                return expanded
        return None

    @classmethod
    def check(cls) -> Dict:
        bashrc = cls.find_bashrc()
        if not bashrc:
            return {
                "of_installed": False,
                "message": "未找到 OpenFOAM bashrc 文件",
                "bashrc": None,
                "version": None,
            }

        try:
            result = subprocess.run(
                ["bash", "-lc", f"source {bashrc} && echo $WM_PROJECT_VERSION"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            version = result.stdout.strip() or "unknown"
            logger.info(f"OpenFOAM version: {version}, bashrc: {bashrc}")
            return {
                "of_installed": True,
                "message": f"OpenFOAM {version} 已就绪",
                "bashrc": bashrc,
                "version": version,
            }
        except Exception as e:
            logger.error(f"OpenFOAM 环境检测失败: {e}")
            return {
                "of_installed": False,
                "message": f"OpenFOAM 环境加载失败: {e}",
                "bashrc": bashrc,
                "version": None,
            }

    @classmethod
    def run_of_command(cls, command: str, case_path: str, bashrc: str) -> subprocess.CompletedProcess:
        full_cmd = f"source {bashrc} && cd {case_path} && {command}"
        return subprocess.run(
            ["bash", "-lc", full_cmd],
            capture_output=True,
            text=True,
            timeout=300,
        )
