from __future__ import annotations

import threading
from pathlib import Path

from app.core.setting import (
    SecretsSetting,
    SystemSetting,
)


class GlobalSettings:
    """
    Global setting collections.

    Attributes:
    ----------
        setting_path (Path | None):
            Global setting directory
        system_file_name (str):
            System setting file name
        system_setting (SystemSetting | None):
            System setting instance
        secrets_file_name (str):
            Secrets setting file name
        secrets_setting (SecretsSetting | None):
            Secrets setting instance, empty when the file does not exist

    Methods:
    ----------
        load(path: Path | str | None = None) -> None:
            Load global setting, defaults to <app-forge>/settings
        get_system() -> SystemSetting:
            Get the system setting, lazy loaded
        get_secrets() -> SecretsSetting:
            Get the secrets setting, lazy loaded
        get_setting_path() -> Path:
            Get the setting directory, lazy loaded
        reset() -> None:
            Reset the global setting manager

    Raises:
    ----------
        NotADirectoryError:
            If the setting path is not a directory (from load)
        FileNotFoundError:
            If system.yml does not exist (from load)

    Example:
    ----------
        >>> from app.core._global import GlobalSettings
        >>> system_setting = GlobalSettings.get_system()
        >>> secrets_setting = GlobalSettings.get_secrets()

    """

    # default values
    _default_setting_path: Path = Path(__file__).resolve().parents[3] / "settings"

    # resetable attributes
    setting_path: Path | None = None
    system_file_name: str = "system.yml"
    system_setting: SystemSetting | None = None
    secrets_file_name: str = "secrets.yml"
    secrets_setting: SecretsSetting | None = None

    # bumped on every load/reset, dependents compare it to spot stale objects
    version: int = 0

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
            _path: Path = cls._default_setting_path

        # Ensure the path is absolute and resolved
        if not _path.is_dir():
            _msg: str = f"setting path must be a directory: {_path}"
            raise NotADirectoryError(_msg)

        # load system setting from system.yml
        # required at any time
        _system_file_path: Path = _path / cls.system_file_name
        if not _system_file_path.is_file():
            _msg: str = f"system setting file not found: {_system_file_path}"
            raise FileNotFoundError(_msg)
        else:
            _system: SystemSetting = SystemSetting.from_yaml(_system_file_path)

        # secrets.yml is git-ignored may missing after fresh clone
        # assign empty if missing
        _secrets_file: Path = _path / cls.secrets_file_name
        if _secrets_file.exists():
            _secrets: SecretsSetting = SecretsSetting.from_yaml(_secrets_file)
        else:
            _secrets = SecretsSetting()

        with cls._lock:
            cls.setting_path = _path
            cls.system_setting = _system
            cls.secrets_setting = _secrets
            cls.version += 1

    @classmethod
    def _ensure_loaded(cls) -> None:
        _indices: list[bool] = [
            cls.system_setting is None,
            cls.secrets_setting is None,
        ]
        if any(_indices):
            cls.load()

    @classmethod
    def get_system(cls) -> SystemSetting:
        with cls._lock:
            cls._ensure_loaded()
            return cls.system_setting

    @classmethod
    def get_secrets(cls) -> SecretsSetting:
        with cls._lock:
            cls._ensure_loaded()
            return cls.secrets_setting

    @classmethod
    def get_setting_path(cls) -> Path:
        with cls._lock:
            cls._ensure_loaded()
            return cls.setting_path

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            cls.setting_path = None
            cls.system_setting = None
            cls.secrets_setting = None
            cls.version += 1
