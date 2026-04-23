"""
参数配置管理器。
管理 OpenFOAM 仿真参数表单。
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from pathlib import Path


@dataclass
class ParameterGroup:
    """参数组"""
    name: str
    label: str
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Parameter:
    """单个参数"""
    key: str
    label: str
    value: Any
    dtype: str = "str"  # str, int, float, bool, list, choice
    options: List[Any] = field(default_factory=list)
    min_val: float = None
    max_val: float = None
    help_text: str = ""
    group: str = "General"


class ParameterManager:
    """
    管理仿真参数的默认值和验证。
    """

    # 预定义参数组
    DEFAULT_GROUPS = [
        ParameterGroup(
            name="time",
            label="时间控制",
            params={
                "startTime": 0.0,
                "endTime": 1000.0,
                "deltaT": 1.0,
                "writeInterval": 100,
            }
        ),
        ParameterGroup(
            name="solver",
            label="求解器设置",
            params={
                "solver": "simpleFoam",
            }
        ),
        ParameterGroup(
            name="turbulence",
            label="湍流模型",
            params={
                "turbulenceModel": "kEpsilon",
            }
        ),
    ]

    # 求解器选项
    SOLVERS = [
        ("simpleFoam", "simpleFoam - 稳态不可压缩"),
        ("pisoFoam", "pisoFoam - 瞬态不可压缩"),
        ("icoFoam", "icoFoam - 瞬态层流"),
        ("blockMesh", "blockMesh - 生成结构网格"),
        ("snappyHexMesh", "snappyHexMesh - 生成非结构网格"),
    ]

    # 湍流模型选项
    TURBULENCE_MODELS = [
        ("laminar", "层流（无湍流）"),
        ("kEpsilon", "k-ε 模型"),
        ("kOmega", "k-ω 模型"),
        ("SpalartAllmaras", "Spalart-Allmaras 模型"),
    ]

    def __init__(self):
        self.groups: List[ParameterGroup] = [g for g in self.DEFAULT_GROUPS]

    def get_params_dict(self) -> Dict[str, Any]:
        """获取所有参数的扁平字典"""
        result = {}
        for group in self.groups:
            result.update(group.params)
        return result

    def get_group(self, name: str) -> Optional[ParameterGroup]:
        for g in self.groups:
            if g.name == name:
                return g
        return None

    def update_group(self, name: str, params: Dict[str, Any]) -> None:
        for g in self.groups:
            if g.name == name:
                g.params.update(params)
                return
        self.groups.append(ParameterGroup(name=name, label=name, params=params))

    def validate(self) -> tuple[bool, List[str]]:
        """验证参数合法性"""
        errors = []

        time_g = self.get_group("time")
        if time_g:
            start = time_g.params.get("startTime", 0)
            end = time_g.params.get("endTime", 1000)
            dt = time_g.params.get("deltaT", 1)
            if start >= end:
                errors.append("开始时间必须小于结束时间")
            if dt <= 0:
                errors.append("时间步长必须大于 0")
            if end - start > 1e7:
                errors.append("仿真时间跨度过大，请检查参数")

        return len(errors) == 0, errors

    def to_openfoam_config(self) -> Dict[str, Dict[str, Any]]:
        """转换为 OpenFOAM 配置字典"""
        time_g = self.get_group("time")
        solver_g = self.get_group("solver")
        turb_g = self.get_group("turbulence")

        configs = {}

        if time_g and solver_g:
            configs["controlDict"] = {
                "startTime": time_g.params.get("startTime", 0),
                "endTime": time_g.params.get("endTime", 1000),
                "deltaT": time_g.params.get("deltaT", 1),
                "writeInterval": time_g.params.get("writeInterval", 100),
                "application": solver_g.params.get("solver", "simpleFoam"),
            }

        if turb_g:
            configs["transportProperties"] = {
                "simulationType": turb_g.params.get("turbulenceModel", "kEpsilon"),
            }

        return configs
