from __future__ import annotations

import threading
from pathlib import Path

from app.core._global.setting import GlobalSettings
from app.core.logstream import LogStream
from app.core.setting import SystemSetting


class GlobalLogStreams:
    """
    Global LogStream resource manager, one LogStream per name.

    Level and timezone are from global system setting and set to all LogStreams.

    Attributes:
    ----------
        path (Path):
            Directory holding the `<name>.log` files
        streams (dict[str, LogStream]):
            LogStreams created so far, keyed by name

    Methods:
    ----------
        load(log_path: Path | str | None = None) -> None:
            Set the log directory and drop the cached LogStreams
        get(name: str) -> LogStream:
            Get the LogStream with the given name, created on first use
        list_names() -> list[str]:
            List all LogStream names
        reset() -> None:
            Reset the global LogStream manager

    Example:
    ----------
        >>> from app.core._global import GlobalLogStreams
        >>> logger = GlobalLogStreams.get("demo")
        >>> logger.info("hello")

    """

    # default values
    _default_log_path: Path = Path(__file__).resolve().parents[3] / "logs"

    # Resetable attributes
    log_path: Path = _default_log_path
    streams: dict[str, LogStream] = {}

    # GlobalSettings.version the cached streams were built from
    _settings_version: int = -1

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
            _path: Path = cls._default_log_path

        # resetable attributes
        if not _path.is_dir():
            _path.mkdir(parents=True, exist_ok=True)

        with cls._lock:
            cls.log_path = _path
            cls.streams = {}

    @classmethod
    def get(
        cls,
        name: str,
    ) -> LogStream:
        with cls._lock:
            _system: SystemSetting = GlobalSettings.get_system()
            if cls._settings_version != GlobalSettings.version:
                # level and timezone come from the settings, rebuild after a reload
                cls.streams = {}
                cls._settings_version = GlobalSettings.version
            if name not in cls.streams:
                _stream: LogStream = LogStream(
                    name=name,
                    path=cls.log_path,
                    level=_system.level,
                    timezone=_system.timezone or "UTC",
                )
                cls.streams[name] = _stream
            return cls.streams[name]

    @classmethod
    def list_names(cls) -> list[str]:
        with cls._lock:
            return list(cls.streams)

    @classmethod
    def reset(cls) -> None:
        cls.load()
