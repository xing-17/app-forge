from __future__ import annotations

import logging
from pathlib import Path
from zoneinfo import ZoneInfo

from app.core.logstream.group import (
    ConsoleGroup,
    FileGroup,
)


class LogStream(logging.Logger):
    """
    Logger with a fixed console group (colored text) and file group (JSON lines).

    Args:
    ----------
        name (str):
            Logger name, also the log file stem.
        path (str | Path):
            Directory for the log file.
        level (str):
            Logging level name. Default is "INFO".
        timezone (str):
            IANA timezone name used for timestamps. Default is "UTC".

    Example:
    ----------
        >>> logger = LogStream("forge", path="~/logs", timezone="Asia/Shanghai")
        >>> logger.info("hello")
        >>> logger.read(limit=10)

    """

    def __init__(
        self,
        name: str,
        path: str | Path,
        level: str = "INFO",
        timezone: str = "UTC",
    ) -> None:
        super().__init__(
            name=name,
            level=level.upper(),
        )
        self._tz = self._resolve_timezone(timezone)

        # Add file handler
        self._file = FileGroup(
            path=path,
            name=name,
            timezone=self._tz,
        )
        self.addHandler(self._file)

        # Add console handler
        self._console = ConsoleGroup(timezone=self._tz)
        self.addHandler(self._console)

    def _resolve_timezone(
        self,
        timezone: str = "UTC",
    ) -> ZoneInfo:
        return ZoneInfo(timezone)

    def read(
        self,
        limit: int | None = None,
    ) -> list[dict]:
        return self._file.read(limit=limit)
