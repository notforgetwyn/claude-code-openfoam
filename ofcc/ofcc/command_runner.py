import subprocess
from pathlib import Path
from typing import Optional, Callable
from ofcc.infra.logger import get_logger

logger = get_logger(__name__)


class CommandResult:
    def __init__(self, returncode: int, stdout: str, stderr: str):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.success = returncode == 0


class SubprocessRunner:
    def __init__(self, bashrc: str):
        self.bashrc = bashrc

    def run(
        self,
        command: str,
        case_path: str,
        timeout: int = 300,
        on_output: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ) -> CommandResult:
        """
        在指定 case 目录下执行 OpenFOAM 命令。

        Args:
            command: OpenFOAM 命令（如 blockMesh, simpleFoam）
            case_path: case 目录路径
            timeout: 超时秒数
            on_output: stdout 每行回调
            on_error: stderr 每行回调
        """
        full_cmd = f"source {self.bashrc} && cd {case_path} && {command}"
        logger.info(f"执行命令: {command} (case: {case_path})")

        process = subprocess.Popen(
            ["bash", "-lc", full_cmd],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        stdout_lines = []
        stderr_lines = []

        while True:
            if process.stdout:
                line = process.stdout.readline()
                if line:
                    stdout_lines.append(line)
                    if on_output:
                        on_output(line.rstrip())
            if process.stderr:
                err_line = process.stderr.readline()
                if err_line:
                    stderr_lines.append(err_line)
                    if on_error:
                        on_error(err_line.rstrip())

            if process.poll() is not None:
                break

        process.wait(timeout=timeout)

        stdout_text = "".join(stdout_lines)
        stderr_text = "".join(stderr_lines)

        result = CommandResult(process.returncode, stdout_text, stderr_text)

        if result.success:
            logger.info(f"命令执行成功: {command}")
        else:
            logger.error(f"命令执行失败: {command}, returncode={process.returncode}")

        return result

    def run_blocking(
        self,
        command: str,
        case_path: str,
        timeout: int = 300,
    ) -> CommandResult:
        """同步执行命令，不实时回调"""
        full_cmd = f"source {self.bashrc} && cd {case_path} && {command}"
        logger.info(f"执行命令（同步）: {command}")

        result = subprocess.run(
            ["bash", "-lc", full_cmd],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        return CommandResult(result.returncode, result.stdout, result.stderr)
