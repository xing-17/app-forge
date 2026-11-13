from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, tzinfo
from pathlib import Path

_COLORS = {
    "DEBUG": "\x1b[38;5;244m",
    "INFO": "\x1b[32m",
    "WARNING": "\x1b[38;5;208m",
    "ERROR": "\x1b[31m",
    "CRITICAL": "\x1b[35m",
}
_RESET = "\x1b[0m"
_CONSOLE_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_FILE_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"


class ColorTextFormat(logging.Formatter):
    """
    Colored single-line console formatter.

    Args:
    ----------
        timezone (tzinfo):
            Timezone for the `asctime` field.

    """

    def __init__(
        self,
        timezone: tzinfo,
    ) -> None:
        super().__init__(
            fmt="%(asctime)s [%(levelname)s]: %(message)s",
        )
        self._timezone = timezone

    def formatTime(
        self,
        record: logging.LogRecord,
        datefmt: str | None = None,
    ) -> str:
        _dt: datetime = datetime.fromtimestamp(
            timestamp=record.created,
            tz=self._timezone,
        )
        _fmt: str = datefmt or _CONSOLE_DATE_FORMAT
        return _dt.strftime(_fmt)

    def format(
        self,
        record: logging.LogRecord,
    ) -> str:
        _color = _COLORS.get(record.levelname, "")
        _res: str = super().format(record)
        return f"{_color}{_res}{_RESET}"


class ConsoleGroup(logging.StreamHandler):
    """
    Console handler writing colored text to stdout.

    Args:
    ----------
        timezone (tzinfo):
            Timezone for the `asctime` field.

    """

    def __init__(self, timezone: tzinfo) -> None:
        super().__init__(stream=sys.stdout)
        self.setFormatter(ColorTextFormat(timezone))


class FileGroup(logging.Handler):
    """
    JSON-lines file handler capped at `max_items` lines.

    Args:
    ----------
        path (str | Path):
            Directory holding `<name>.log`.
        name (str):
            Log file stem.
        timezone (tzinfo):
            Timezone of the `created_at` field.

    Raises:
    ----------
        ValueError: If `path` is an existing file.

    """

    max_items: int = 100_000

    def __init__(
        self,
        path: str | Path,
        name: str,
        timezone: tzinfo,
    ) -> None:
        super().__init__()
        _dir = Path(path).expanduser()
        if _dir.is_file():
            _msg: str = "path must be a directory, not a file."
            raise ValueError(_msg)
        _dir.mkdir(parents=True, exist_ok=True)

        self._path: Path = (_dir / f"{name}.log").resolve()
        self._timezone: tzinfo = timezone

        # compact only after 10% overflow to avoid rewriting on every emit
        self._threshold: int = int(self.max_items * 1.1)
        self._n_lines: int = len(self._tail())

    def _tail(
        self,
        limit: int | None = None,
    ) -> list[str]:
        if not self._path.exists():
            return []
        if limit is not None and limit <= 0:
            return []

        with self._path.open("r", encoding="utf-8") as f:
            lines = f.readlines()

        if limit is None:
            return lines
        else:
            return lines[-limit:]

    def _serialize(
        self,
        record: logging.LogRecord,
    ) -> str:
        _exc: dict[str, str] | None = None
        if record.exc_info and record.exc_info[0] is not None:
            _type, _value, _ = record.exc_info
            _exc = {
                "type": _type.__qualname__,
                "value": str(_value),
            }

        _created_at_dt: datetime = datetime.fromtimestamp(
            timestamp=record.created,
            tz=self._timezone,
        )
        _created_at: str = _created_at_dt.strftime(_FILE_DATE_FORMAT)
        return json.dumps(
            {
                "level": record.levelname,
                "created_at": _created_at,
                "msg": record.getMessage(),
                "exc_info": _exc,
            },
            sort_keys=True,
            ensure_ascii=False,
        )

    def emit(
        self,
        record: logging.LogRecord,
    ) -> None:
        try:
            with self._path.open("a", encoding="utf-8") as f:
                _serialized: str = self._serialize(record)
                f.write(_serialized + "\n")
            self._n_lines += 1
            if self._n_lines >= self._threshold:
                self._compact()
        except Exception:
            self.handleError(record)

    def _compact(self) -> None:
        _lines = self._tail(limit=self.max_items)
        _temp = self._path.with_suffix(f"{self._path.suffix}.tmp")
        _temp.write_text("".join(_lines), encoding="utf-8")
        _temp.replace(self._path)
        self._n_lines = len(_lines)

    def read(
        self,
        limit: int | None = None,
    ) -> list[dict]:
        _result: list[dict] = []
        for line in self._tail(limit=limit):
            try:
                _result.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        _result.reverse()
        return _result
