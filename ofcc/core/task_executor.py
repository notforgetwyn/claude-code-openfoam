from enum import Enum
from PySide6.QtCore import QThread, Signal, QObject
from typing import Optional, Dict
from ofcc.ofcc.command_runner import SubprocessRunner, CommandResult
from ofcc.ofcc.environment import OFEnvironment
from ofcc.infra.logger import get_logger

logger = get_logger(__name__)


class TaskStatus(Enum):
    IDLE = "idle"
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


class SimulationTask(QThread):
    output_signal = Signal(str)
    error_signal = Signal(str)
    status_signal = Signal(str)
    finished_signal = Signal(int, str, str)  # returncode, stdout, stderr

    def __init__(self, case_id: str, command: str, case_path: str, parent=None):
        super().__init__(parent)
        self.case_id = case_id
        self.command = command
        self.case_path = case_path
        self.status = TaskStatus.IDLE
        self._process = None
        self._should_stop = False

        of_env = OFEnvironment.check()
        self.bashrc = of_env.get("bashrc", "")
        self.runner = SubprocessRunner(self.bashrc)

    def run(self):
        self.status = TaskStatus.RUNNING
        self.status_signal.emit(f"运行中: {self.command}")

        result = self.runner.run(
            command=self.command,
            case_path=self.case_path,
            timeout=3600,
            on_output=self.output_signal.emit,
            on_error=self.error_signal.emit,
        )

        if self._should_stop:
            self.status = TaskStatus.ABORTED
            self.status_signal.emit("已中止")
        elif result.success:
            self.status = TaskStatus.COMPLETED
            self.status_signal.emit("已完成")
        else:
            self.status = TaskStatus.FAILED
            self.status_signal.emit(f"失败 (returncode={result.returncode})")

        self.finished_signal.emit(result.returncode, result.stdout, result.stderr)

    def stop(self):
        self._should_stop = True
        if self._process:
            self._process.terminate()
            self._process.kill()
        self.status = TaskStatus.ABORTED


class TaskExecutor(QObject):
    """
    任务执行器，管理多个并发任务。
    """

    task_started = Signal(str)       # task_id
    task_output = Signal(str, str)   # task_id, output
    task_error = Signal(str, str)    # task_id, error
    task_status = Signal(str, str)   # task_id, status
    task_finished = Signal(str, int, str, str)  # task_id, returncode, stdout, stderr

    def __init__(self):
        super().__init__()
        self._tasks: Dict[str, SimulationTask] = {}
        self.bashrc = OFEnvironment.check().get("bashrc", "")

    def start_task(self, case_id: str, command: str, case_path: str) -> SimulationTask:
        """启动一个新任务"""
        task = SimulationTask(case_id, command, case_path)

        task.output_signal.connect(lambda line: self.task_output.emit(case_id, line))
        task.error_signal.connect(lambda line: self.task_error.emit(case_id, line))
        task.status_signal.connect(lambda status: self.task_status.emit(case_id, status))
        task.finished_signal.connect(
            lambda rc, out, err: self._on_task_finished(case_id, rc, out, err)
        )

        self._tasks[case_id] = task
        self.task_started.emit(case_id)
        task.start()

        logger.info(f"任务已启动: case={case_id}, command={command}")
        return task

    def stop_task(self, case_id: str):
        """中止指定任务"""
        task = self._tasks.get(case_id)
        if task and task.status == TaskStatus.RUNNING:
            task.stop()
            logger.info(f"任务已请求中止: case={case_id}")

    def stop_all(self):
        """中止所有任务"""
        for case_id, task in self._tasks.items():
            if task.status == TaskStatus.RUNNING:
                task.stop()
        logger.info("所有任务已请求中止")

    def get_task_status(self, case_id: str) -> TaskStatus:
        """获取任务状态"""
        task = self._tasks.get(case_id)
        return task.status if task else TaskStatus.IDLE

    def _on_task_finished(self, case_id: str, returncode: int, stdout: str, stderr: str):
        logger.info(f"任务完成: case={case_id}, returncode={returncode}")
        self.task_finished.emit(case_id, returncode, stdout, stderr)
