import yaml
from pathlib import Path
from typing import Dict, Any
from ofcc.infra.logger import get_logger

logger = get_logger(__name__)


class SettingsManager:
    DEFAULT_SETTINGS = {
        "theme": "light",
        "language": "zh_CN",
        "default_solver": "simpleFoam",
        "workspace_path": str(Path.home() / "ofcc_workspace"),
        "openfoam_bashrc": "/home/shihuayue/openfoam/OpenFOAM-dev/etc/bashrc",
        "log_level": "INFO",
        "auto_save": True,
        "expert_mode": False,
        "show_tutorial_on_startup": True,
    }

    def __init__(self):
        self.settings_path = Path.home() / ".ofcc" / "settings.yaml"
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        self._settings = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.settings_path.exists():
            try:
                return yaml.safe_load(self.settings_path.read_text()) or self.DEFAULT_SETTINGS.copy()
            except Exception as e:
                logger.warning(f"设置文件读取失败，使用默认设置: {e}")
                return self.DEFAULT_SETTINGS.copy()
        return self.DEFAULT_SETTINGS.copy()

    def save(self, **kwargs) -> None:
        self._settings.update(kwargs)
        self.settings_path.write_text(yaml.dump(self._settings))
        logger.info("设置已保存")

    def get(self, key: str, default: Any = None) -> Any:
        return self._settings.get(key, default)

    def get_all(self) -> Dict[str, Any]:
        return self._settings.copy()

    def reset(self) -> None:
        self._settings = self.DEFAULT_SETTINGS.copy()
        self.settings_path.write_text(yaml.dump(self._settings))
        logger.info("设置已重置为默认")

    def update(self, key: str, value: Any) -> None:
        self._settings[key] = value
        self.save(**self._settings)
