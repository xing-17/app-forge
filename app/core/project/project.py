from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from app.core.setting import SecretsSetting

from .engine import ProjectEngine
from .setting import ProjectSetting


class Project:
    """
    Project resource, a folder holding project.yml, models and assets

    Attributes:
    ----------
        path (Path):
            Project directory
        name (str):
            Project name, same as the directory name
        setting_path (Path):
            Path to the project.yml file
        setting (ProjectSetting):
            Project setting loaded from project.yml
        models_path (Path):
            Directory of the project dbt models
        assets_path (Path):
            Directory of the project assets
        engine_path (Path):
            Directory of the disposable engine (.engine)
        engine (ProjectEngine):
            Project engine instance

    Args:
    ----------
        path (str | Path):
            Project directory, its name must match the name in project.yml
        secrets (SecretsSetting | None):
            Shared secrets handed to the engine, loaded by the caller

    Raises:
    ----------
        FileNotFoundError:
            If the project directory or project.yml does not exist
        ValueError:
            If the name in project.yml differs from the directory name

    """

    engine_dir: ClassVar[str] = ".engine"
    models_dir: ClassVar[str] = "models"
    assets_dir: ClassVar[str] = "assets"
    required_dirs: ClassVar[tuple[str, ...]] = (
        engine_dir,
        models_dir,
        assets_dir,
    )
    setting_file: ClassVar[str] = "project.yml"

    def __init__(
        self,
        path: str | Path,
        secrets: SecretsSetting | None = None,
    ):
        self.path: Path = Path(path).expanduser().resolve()
        self.name: str = self.path.name
        self._check_project_dir()

        # Setting file path at project.yml
        self.setting_path: Path = self.path / self.setting_file
        self._check_setting_file()

        # Resolve project setting from the project.yml file
        self.setting: ProjectSetting = self._resolve_setting()
        self._check_setting_name()

        # Resolve paths for models, assets, and engine directories
        self.models_path: Path = self.path / self.models_dir
        self.assets_path: Path = self.path / self.assets_dir
        self.engine_path: Path = self.path / self.engine_dir
        self._ensure_required_dirs()

        # .engine is git-ignored and disposable
        # so it may be missing after a fresh clone
        self.engine: ProjectEngine = ProjectEngine(
            path=self.engine_path,
            project_setting=self.setting,
            assets_path=self.assets_path,
            secrets=secrets,
        )

    def _check_project_dir(self) -> None:
        """Project directory must exist."""
        if not self.path.is_dir():
            _msg: str = f"project folder not found: {self.path}"
            raise FileNotFoundError(_msg)

    def _check_setting_file(self) -> None:
        """project.yml must exist."""
        if not self.setting_path.is_file():
            _msg: str = f"project.yml not found: {self.setting_path}"
            raise FileNotFoundError(_msg)

    def _ensure_required_dirs(self) -> None:
        """Create the required directories within the project folder if missing."""
        for _folder in self.required_dirs:
            (self.path / _folder).mkdir(parents=True, exist_ok=True)

    def _resolve_setting(self) -> ProjectSetting:
        """Load the project setting from project.yml."""
        return ProjectSetting.from_file(self.setting_path)

    def _check_setting_name(self) -> None:
        """Name in project.yml must match the project directory name."""
        _setting_name: str = self.setting.name
        _dir_name: str = self.name
        if _setting_name != _dir_name:
            _msg: str = f"project.yml name '{_setting_name}' must be '{_dir_name}'"
            raise ValueError(_msg)
