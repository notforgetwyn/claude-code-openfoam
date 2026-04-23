import uuid
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from ofcc.infra.database import Database
from ofcc.infra.logger import get_logger

logger = get_logger(__name__)


class Case:
    def __init__(self, id: str, project_id: str, name: str, path: str, solver: str, status: str, created_at: str):
        self.id = id
        self.project_id = project_id
        self.name = name
        self.path = Path(path)
        self.solver = solver
        self.status = status
        self.created_at = created_at

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "name": self.name,
            "path": str(self.path),
            "solver": self.solver,
            "status": self.status,
            "created_at": self.created_at,
        }


class CaseManager:
    def __init__(self):
        self.db = Database.get_instance()

    def create(self, project_id: str, name: str, template_path: Optional[str] = None) -> Case:
        case_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()

        project_path = Path.home() / "ofcc_workspace" / "projects"
        case_path = project_path / f"{project_id}_*" / "cases" / f"{case_id}_{name}"

        for p in project_path.iterdir():
            if p.is_dir() and p.name.startswith(project_id):
                case_path = p / "cases" / f"{case_id}_{name}"
                break

        case_path.mkdir(parents=True, exist_ok=False)

        if template_path and Path(template_path).exists():
            for item in Path(template_path).iterdir():
                if item.is_dir():
                    shutil.copytree(item, case_path / item.name)
                else:
                    shutil.copy2(item, case_path / item.name)
            logger.info(f"从模板复制: {template_path} -> {case_path}")

        self.db.commit(
            "INSERT INTO cases (id, project_id, name, path, solver, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (case_id, project_id, name, str(case_path), "simpleFoam", "idle", now),
        )

        logger.info(f"Case 创建成功: {name} ({case_id})")
        return Case(case_id, project_id, name, str(case_path), "simpleFoam", "idle", now)

    def get_by_project(self, project_id: str) -> List[Case]:
        rows = self.db.fetchall(
            "SELECT id, project_id, name, path, solver, status, created_at FROM cases WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        )
        return [Case(*row) for row in rows]

    def get_by_id(self, case_id: str) -> Optional[Case]:
        row = self.db.fetchone(
            "SELECT id, project_id, name, path, solver, status, created_at FROM cases WHERE id = ?",
            (case_id,),
        )
        return Case(*row) if row else None

    def update_status(self, case_id: str, status: str) -> None:
        self.db.commit("UPDATE cases SET status = ? WHERE id = ?", (status, case_id))
        logger.info(f"Case {case_id} 状态更新: {status}")

    def update_solver(self, case_id: str, solver: str) -> None:
        self.db.commit("UPDATE cases SET solver = ? WHERE id = ?", (solver, case_id))
        logger.info(f"Case {case_id} 求解器更新: {solver}")

    def delete(self, case_id: str) -> None:
        case = self.get_by_id(case_id)
        if case:
            shutil.rmtree(case.path)
            self.db.commit("DELETE FROM cases WHERE id = ?", (case_id,))
            logger.info(f"Case 已删除: {case_id}")
