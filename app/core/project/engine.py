from pathlib import Path
from typing import Any, ClassVar

import yaml
from dbt.cli.main import dbtRunner

from .setting import (
    EngineSetting,
    ProjectSetting,
)


class ProjectEngine:
    """
    Disposable project dbt engine generated from project.yml into <project>/.engine

    Attributes:
    ----------
        path (Path):
            Project engine directory (<project>/.engine)
        project_setting (ProjectSetting):
            Project setting used to generate the engine
        engine_setting (EngineSetting):
            Engine part of the project setting
        project_name (str):
            Project name, also used as dbt project and profile name
        assets_path (Path):
            Project assets directory, used as duckdb external root
        duckdb_file_path (Path):
            Path to the duckdb database file inside the engine directory
        macro_path (Path):
            Path to the shared dbt macros (<app-forge>/engine/macros)

    Args:
    ----------
        path (Path):
            Project engine directory (<project>/.engine)
        project_setting (ProjectSetting):
            Project setting used to generate the engine
        assets_path (Path):
            Project assets directory

    Methods:
    ----------
        render() -> Path:
            (Re)generate dbt config files under the engine directory
        run(*args: str) -> None:
            Render, then invoke dbt with the given arguments

    """

    dbt_source_version: ClassVar[int] = 2
    dbt_config_version: ClassVar[int] = 2
    dbt_target: ClassVar[str] = "database"

    def __init__(
        self,
        path: Path,
        project_setting: ProjectSetting,
        assets_path: Path,
    ):
        self.path: Path = path
        self.project_setting: ProjectSetting = project_setting
        self.engine_setting: EngineSetting = self.project_setting.engine
        self.project_name: str = self.project_setting.name
        self.assets_path: Path = assets_path
        self.duckdb_file: str = f"{self.project_name}.duckdb"
        self.duckdb_file_path: Path = self.path / self.duckdb_file
        self.macro_path: Path = self.path.parents[2] / "engine" / "macros"

    def _build_dbt_project(self) -> dict[str, Any]:
        """Content of dbt_project.yml"""
        _name: str = self.project_name
        _models: dict[str, Any] = self.engine_setting.models
        _content: dict[str, Any] = {
            "name": self.project_name,
            "version": self.project_setting.version,
            "config-version": self.dbt_config_version,
            "profile": self.project_name,
            "model-paths": ["../models", "models"],
            "macro-paths": [str(self.macro_path)],
            "target-path": "target",
            "log-path": "logs",
            "models": {_name: _models},
        }
        return _content

    def _build_dbt_profile(self) -> dict[str, Any]:
        """Content of profiles.yml"""
        _name: str = self.project_setting.name
        _engine: EngineSetting = self.engine_setting
        _profile: dict[str, Any] = {
            _name: {
                "target": self.dbt_target,
                "outputs": {
                    self.dbt_target: {
                        "type": "duckdb",
                        "path": str(self.duckdb_file_path),
                        "external_root": str(self.assets_path),
                        "threads": _engine.threads,
                        "extensions": self.project_setting.extensions,
                    }
                },
            },
        }
        return _profile

    def _build_dbt_sources(self) -> dict[str, Any]:
        """Content of models/sources.yml"""
        _engine: EngineSetting = self.engine_setting
        _sources: list[dict[str, Any]] = []
        for _source in _engine.sources:
            _dumped: dict[str, Any] = _source.model_dump(mode="json")
            _sources.append(_dumped)
        return {"version": self.dbt_source_version, "sources": _sources}

    def render(self) -> Path:
        """(Re)generate dbt config; the duckdb file and other engine data are left intact."""
        _engine: EngineSetting = self.engine_setting

        # Render dbt_project.yml
        _dbt_project: dict[str, Any] = self._build_dbt_project()
        self._write_file(
            file="dbt_project.yml",
            content=_dbt_project,
        )

        # Render profile.yml
        _profile: dict[str, Any] = self._build_dbt_profile()
        self._write_file(
            file="profiles.yml",
            content=_profile,
        )

        # Render sources.yml if there are any sources defined in the engine setting
        # If no sources are defined, the sources.yml file will be removed if it exists.
        if _engine.sources:
            _sources: dict[str, Any] = self._build_dbt_sources()
            self._write_file(
                file="models/sources.yml",
                content=_sources,
            )
        else:
            _sources_file: Path = self.path / "models" / "sources.yml"
            _sources_file.unlink(missing_ok=True)
        return self.path

    def run(
        self,
        *args: str,
    ) -> None:
        """Render, then invoke dbt with `args` (e.g. "run", "test"); raise on failure."""
        self.render()
        _cmd: list[str] = [
            *args,
            "--project-dir",
            str(self.path),
            "--profiles-dir",
            str(self.path),
        ]
        _result = dbtRunner().invoke(_cmd)
        if not _result.success:
            _args_expr: str = " ".join(args)
            _msg: str = f"dbt {_args_expr} failed"
            if _result.exception is not None:
                _msg = f"{_msg}: {_result.exception}"
            raise RuntimeError(_msg) from _result.exception

    def _write_file(
        self,
        file: str,
        content: dict[str, Any],
    ) -> None:
        """Dump `content` as yaml to `file` relative to the engine directory."""
        _target: Path = self.path / file
        _target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        _content: str = yaml.safe_dump(
            content,
            sort_keys=False,
            allow_unicode=True,
        )
        _target.write_text(_content, encoding="utf-8")
