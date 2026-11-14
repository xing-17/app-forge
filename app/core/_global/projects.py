from __future__ import annotations

import threading
from pathlib import Path

from app.core._global.setting import GlobalSettings
from app.core.project import Project
from app.core.setting.secret import SecretsSetting

# Not exported from app.core._global:
#   app.core.project imports app.core._global (GlobalLogStreams), a circular import.


class GlobalProjects:
    """
    Global Project collections, hot reloaded from the projects directory.

    Every sub folder holding a project.yml is a project, named after the folder.
    A broken project is recorded in `errors` to unblock the others.

    Attributes:
    ----------
        projects_path (Path):
            Directory holding the project folders
        projects (dict[str, Project]):
            Registered projects, keyed by project name
        errors (dict[str, str]):
            Reason a project failed to load, keyed by project name

    Methods:
    ----------
        load(path: Path | str | None = None) -> None:
            Set the projects directory, drop everything and scan
        refresh() -> None:
            Rescan the projects directory
        get_project(name: str, strict: bool = False) -> Project | None:
            Get the project with the given name; raises if missing or broken and strict is True
        list_project_names() -> list[str]:
            List all project names
        list_projects() -> list[Project]:
            List all projects
        reset() -> None:
            Reset the global project manager

    Raises:
    ----------
        NotADirectoryError:
            If the projects path is not a directory (from load)

    Example:
    ----------
        >>> from app.core._global.projects import GlobalProjects
        >>> project = GlobalProjects.get_project("housing_au", strict=True)
        >>> names = GlobalProjects.list_project_names()

    """

    # default values
    _default_projects_path: Path = Path(__file__).resolve().parents[3] / "projects"

    # Resetable attributes
    projects_path: Path = _default_projects_path
    projects: dict[str, Project] = {}
    errors: dict[str, str] = {}

    # Project.fingerprint seen per folder, an unchanged value skips the rebuild
    _fingerprints: dict[str, str] = {}

    # thread safe lock for concurrent access
    _lock: threading.RLock = threading.RLock()

    @classmethod
    def load(
        cls,
        path: Path | str | None = None,
    ) -> None:
        # Optionally pass path to class setup
        if path:
            _path: Path = Path(path).expanduser().resolve()
        else:
            _path: Path = cls._default_projects_path

        # resetable attributes
        if not _path.is_dir():
            _msg: str = f"projects path must be a directory: {_path}"
            raise NotADirectoryError(_msg)

        with cls._lock:
            cls._clear()
            cls.projects_path = _path
            cls.refresh()

    @classmethod
    def refresh(cls) -> None:
        with cls._lock:
            _found: dict[str, str] = cls._discover()

            # remove projects that are no longer found
            for _name in set(cls._fingerprints) - set(_found):
                cls.projects.pop(_name, None)
                cls.errors.pop(_name, None)
                cls._fingerprints.pop(_name)

            # register new or updated projects
            for _name, _fingerprint in _found.items():
                if cls._fingerprints.get(_name) == _fingerprint:
                    # project is unchanged, skip the rebuild
                    continue
                else:
                    # project is new or updated, rebuild
                    cls._register(_name)
                    cls._fingerprints[_name] = _fingerprint

    @classmethod
    def _discover(cls) -> dict[str, str]:
        _found: dict[str, str] = {}
        if not cls.projects_path.is_dir():
            return _found

        # iterate over all subdirectories in the projects path
        for _dir in sorted(cls.projects_path.iterdir()):
            _file: Path = _dir / Project.setting_file
            if _dir.name.startswith("."):
                # skip hidden directories
                continue
            if not _file.is_file():
                # skip if the project setting file does not exist
                continue

            _fp: str = Project.compute_fingerprint(_dir)
            _found[_dir.name] = _fp

        return _found

    @classmethod
    def _register(
        cls,
        name: str,
    ) -> None:
        try:
            _project_path: Path = cls.projects_path / name
            _secrets_setting: SecretsSetting = GlobalSettings.get_secrets()
            _project = Project(
                path=_project_path,
                secrets=_secrets_setting,
            )
        except Exception as e:
            cls.projects.pop(name, None)
            cls.errors[name] = str(e)
        else:
            cls.projects[name] = _project
            cls.errors.pop(name, None)

    @classmethod
    def get_project(
        cls,
        name: str,
        strict: bool = False,
    ) -> Project | None:
        with cls._lock:
            cls.refresh()
            if name in cls.projects:
                return cls.projects[name]
            if strict and name in cls.errors:
                _msg: str = f"Project '{name}' failed to load: {cls.errors[name]}"
                raise ValueError(_msg)
            if strict:
                _msg = f"Project '{name}' not found"
                raise ValueError(_msg)
            return None

    @classmethod
    def list_project_names(cls) -> list[str]:
        with cls._lock:
            cls.refresh()
            return sorted(cls.projects)

    @classmethod
    def list_projects(cls) -> list[Project]:
        with cls._lock:
            cls.refresh()
            _res: list[Project] = []
            for _name in sorted(cls.projects):
                _res.append(cls.projects[_name])
            return _res

    @classmethod
    def _clear(cls) -> None:
        cls.projects = {}
        cls.errors = {}
        cls._fingerprints = {}

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            cls._clear()
            cls.projects_path = cls._default_projects_path
