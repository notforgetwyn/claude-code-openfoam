import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from ofcc.infra.database import Database
from ofcc.infra.logger import get_logger

logger = get_logger(__name__)


class Project:
    def __init__(self, id: str, name: str, path: str, created_at: str, updated_at: str):
        self.id = id
        self.name = name
        self.path = Path(path)
        self.created_at = created_at
        self.updated_at = updated_at

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "path": str(self.path),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class ProjectManager:
    def __init__(self):
        self.db = Database.get_instance()
        self.workspace_root = Path.home() / "ofcc_workspace" / "projects"
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def create(self, name: str) -> Project:
        project_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()
        project_path = self.workspace_root / f"{project_id}_{name}"

        if project_path.exists():
            raise ValueError(f"项目路径已存在: {project_path}")

        project_path.mkdir(parents=True, exist_ok=False)
        (project_path / "cases").mkdir(exist_ok=True)
        (project_path / "results").mkdir(exist_ok=True)
        (project_path / "project.yaml").write_text(f"name: {name}\nid: {project_id}\n")

        self.db.commit(
            "INSERT INTO projects (id, name, path, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (project_id, name, str(project_path), now, now),
        )

        logger.info(f"项目创建成功: {name} ({project_id})")
        return Project(project_id, name, str(project_path), now, now)

    def get_all(self) -> List[Project]:
        rows = self.db.fetchall("SELECT id, name, path, created_at, updated_at FROM projects ORDER BY updated_at DESC")
        return [Project(*row) for row in rows]

    def get_by_id(self, project_id: str) -> Optional[Project]:
        row = self.db.fetchone("SELECT id, name, path, created_at, updated_at FROM projects WHERE id = ?", (project_id,))
        return Project(*row) if row else None

    def update(self, project_id: str, **kwargs) -> None:
        now = datetime.now().isoformat()
        if "name" in kwargs:
            self.db.commit("UPDATE projects SET name = ?, updated_at = ? WHERE id = ?", (kwargs["name"], now, project_id))
        logger.info(f"项目更新: {project_id}")

    def delete(self, project_id: str) -> None:
        project = self.get_by_id(project_id)
        if project:
            import shutil
            shutil.rmtree(project.path)
            self.db.commit("DELETE FROM projects WHERE id = ?", (project_id,))
            logger.info(f"项目已删除: {project_id}")

    def exists(self, name: str) -> bool:
        row = self.db.fetchone("SELECT id FROM projects WHERE name = ?", (name,))
        return row is not None
