from __future__ import annotations

import hashlib
from pathlib import Path
from typing import ClassVar, Iterator

from app.core._global import GlobalLogStreams
from app.core._global.logstreams import LogStream
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
        logstream (logging.Logger):
            Project logstream, handed to the engine
        engine (ProjectEngine):
            Project engine instance
        models (list[Path]):
            Files under models, scanned on every access
        assets (list[Path]):
            Files under assets, scanned on every access
        fingerprint (str):
            Hash of project.yml, models and assets, scanned on every access; .engine is ignored

    Args:
    ----------
        path (str | Path):
            Project directory, its name must match the name in project.yml
        secrets (SecretsSetting | None):
            Shared secrets handed to the engine, loaded by the caller
        logstream (logging.Logger | None):
            Project logstream, defaults to the global LogStream named after the project

    Raises:
    ----------
        FileNotFoundError:
            If the project directory or project.yml does not exist
        ValueError:
            If the name in project.yml differs from the directory name

    """

    engine_dir: ClassVar[str] = ".engine"
    models_dir: ClassVar[str] = "models"
    models_suffix: ClassVar[str] = ".sql"
    models_pattern: ClassVar[str] = "*.sql"
    assets_dir: ClassVar[str] = "assets"
    assets_suffix: ClassVar[str] = ".parquet"
    assets_pattern: ClassVar[str] = "*.parquet"
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

        # Created after validation so an invalid project leaves no log file
        self.logstream_name: str = f"project/{self.name}"
        self.logstream: LogStream = GlobalLogStreams.get(self.logstream_name)

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
            logstream=self.logstream,
        )

        self.logstream.debug(f"proj({self.name}) set at {self.path}")
        self.logstream.info(f"proj({self.name}) status OK")

    @property
    def models(self) -> list[Path]:
        return self._list_files(
            folder=self.models_path,
            recursive=True,
            suffix=self.models_suffix,
        )

    @property
    def assets(self) -> list[Path]:
        return self._list_files(
            folder=self.assets_path,
            recursive=True,
            suffix=self.assets_suffix,
        )

    @property
    def fingerprint(self) -> str:
        return self.compute_fingerprint(self.path)

    @classmethod
    def compute_fingerprint(
        cls,
        path: Path | str,
    ) -> str:
        # classmethod so a folder that fails to
        # build a Project can still be fingerprinted
        _root: Path = Path(path)
        _hash = hashlib.sha256()
        _dests: list[Path] = [
            _root / cls.setting_file,
            *cls._list_files(
                folder=_root / cls.models_dir,
                recursive=True,
                suffix=cls.models_suffix,
            ),
            *cls._list_files(
                folder=_root / cls.assets_dir,
                recursive=True,
                suffix=cls.assets_suffix,
            ),
        ]
        for _file in _dests:
            try:
                _stat = _file.stat()
            except FileNotFoundError:
                continue
            _rel: str = _file.relative_to(_root).as_posix()
            _mtime_ns: int = _stat.st_mtime_ns
            _size: int = _stat.st_size
            _val: str = f"{_rel}\0{_mtime_ns}\0{_size}\n"
            _hash.update(_val.encode())
        return _hash.hexdigest()

    @staticmethod
    def _list_files(
        folder: Path,
        recursive: bool = True,
        suffix: str | None = None,
    ) -> list[Path]:
        _result: list[Path] = []
        if not folder.is_dir():
            return _result
        if recursive:
            _fgen: Iterator[Path] = folder.rglob("*")
        else:
            _fgen: Iterator[Path] = folder.glob("*")
        for _file in _fgen:
            if _file.is_file():
                if suffix and not _file.name.endswith(suffix):
                    continue
                else:
                    _result.append(_file)
        return sorted(_result)

    def _check_project_dir(self) -> None:
        if not self.path.is_dir():
            _msg: str = f"project folder not found: {self.path}"
            raise FileNotFoundError(_msg)

    def _check_setting_file(self) -> None:
        if not self.setting_path.is_file():
            _msg: str = f"project.yml not found: {self.setting_path}"
            raise FileNotFoundError(_msg)

    def _ensure_required_dirs(self) -> None:
        for _folder in self.required_dirs:
            (self.path / _folder).mkdir(parents=True, exist_ok=True)

    def _resolve_setting(self) -> ProjectSetting:
        return ProjectSetting.from_file(self.setting_path)

    def _check_setting_name(self) -> None:
        _setting_name: str = self.setting.name
        _dir_name: str = self.name
        if _setting_name != _dir_name:
            _msg: str = f"project.yml name '{_setting_name}' must be '{_dir_name}'"
            raise ValueError(_msg)
