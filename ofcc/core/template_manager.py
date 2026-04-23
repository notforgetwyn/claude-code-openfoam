import shutil
from pathlib import Path
from typing import List, Dict, Optional
from ofcc.infra.logger import get_logger

logger = get_logger(__name__)


class CaseTemplate:
    def __init__(self, name: str, path: Path, description: str = ""):
        self.name = name
        self.path = path
        self.description = description

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "path": str(self.path),
            "description": self.description,
        }


class TemplateManager:
    def __init__(self):
        self.templates_root = Path.home() / "ofcc_workspace" / "templates"
        self.templates_root.mkdir(parents=True, exist_ok=True)
        self._ensure_default_templates()

    def _ensure_default_templates(self):
        default_templates = {
            "simpleFoam_pipe": "稳态不可压缩管流案例",
            "pisoFoam_channel": "瞬态不可压缩通道案例",
        }
        for name, desc in default_templates.items():
            template_path = self.templates_root / name
            if not template_path.exists():
                template_path.mkdir(parents=True, exist_ok=True)
                (template_path / "0.orig").mkdir(exist_ok=True)
                (template_path / "system").mkdir(exist_ok=True)
                (template_path / "constant").mkdir(exist_ok=True)
                logger.info(f"创建默认模板: {name}")

    def get_all(self) -> List[CaseTemplate]:
        templates = []
        if self.templates_root.exists():
            for item in self.templates_root.iterdir():
                if item.is_dir():
                    templates.append(CaseTemplate(item.name, item))
        return templates

    def get_by_name(self, name: str) -> Optional[CaseTemplate]:
        path = self.templates_root / name
        return CaseTemplate(name, path) if path.exists() else None

    def create_template(self, name: str, case_path: Path) -> CaseTemplate:
        template_path = self.templates_root / name
        if template_path.exists():
            raise ValueError(f"模板已存在: {name}")

        shutil.copytree(case_path, template_path)
        logger.info(f"模板创建: {name} from {case_path}")
        return CaseTemplate(name, template_path)

    def delete_template(self, name: str) -> None:
        template_path = self.templates_root / name
        if template_path.exists():
            shutil.rmtree(template_path)
            logger.info(f"模板删除: {name}")

    def get_template_path(self, name: str) -> Optional[Path]:
        path = self.templates_root / name
        return path if path.exists() else None
