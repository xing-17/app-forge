from __future__ import annotations

import logging
from zoneinfo import ZoneInfo

import pytest

from app.core.logstream.group import ColorTextFormat, FileGroup

_UTC = ZoneInfo("UTC")


def _record(msg: str = "hello", level: int = logging.INFO, **kwargs) -> logging.LogRecord:
    return logging.LogRecord("t", level, "/p.py", 1, msg, (), kwargs.get("exc_info"))


class TestColorTextFormat:
    def test_wraps_line_in_level_color(self):
        out = ColorTextFormat(_UTC).format(_record())
        assert out.startswith("\x1b[32m")
        assert out.endswith("\x1b[0m")
        assert "[INFO]: hello" in out


class TestFileGroup:
    def test_creates_directory_and_log_path(self, tmp_path):
        group = FileGroup(tmp_path / "a" / "b", "app", _UTC)
        assert group._path == (tmp_path / "a" / "b" / "app.log").resolve()

    def test_raises_when_path_is_file(self, tmp_path):
        target = tmp_path / "x.log"
        target.write_text("")
        with pytest.raises(ValueError):
            FileGroup(target, "app", _UTC)

    def test_emit_and_read_newest_first(self, tmp_path):
        group = FileGroup(tmp_path, "app", _UTC)
        for i in range(3):
            group.emit(_record(f"m{i}"))
        assert [e["msg"] for e in group.read()] == ["m2", "m1", "m0"]
        assert [e["msg"] for e in group.read(limit=1)] == ["m2"]

    def test_serializes_exception(self, tmp_path):
        group = FileGroup(tmp_path, "app", _UTC)
        try:
            raise ValueError("boom")
        except ValueError:
            import sys

            group.emit(_record("err", logging.ERROR, exc_info=sys.exc_info()))
        assert group.read()[0]["exc_info"] == {"type": "ValueError", "value": "boom"}

    def test_compacts_beyond_threshold(self, tmp_path, monkeypatch):
        monkeypatch.setattr(FileGroup, "max_items", 10)
        group = FileGroup(tmp_path, "app", _UTC)
        for i in range(20):
            group.emit(_record(f"m{i}"))
        assert len(group.read()) <= group._threshold
        assert group.read()[0]["msg"] == "m19"

    def test_skips_malformed_lines(self, tmp_path):
        group = FileGroup(tmp_path, "app", _UTC)
        group.emit(_record("ok"))
        with group._path.open("a", encoding="utf-8") as f:
            f.write("not json\n")
        assert [e["msg"] for e in group.read()] == ["ok"]
