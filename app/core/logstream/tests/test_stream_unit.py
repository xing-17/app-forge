from __future__ import annotations

import logging

import pytest

from app.core.logstream import LogStream
from app.core.logstream.group import ConsoleGroup, FileGroup


class TestLogStream:
    def test_has_fixed_console_and_file_handlers(self, tmp_path):
        stream = LogStream("forge", path=tmp_path)
        kinds = {type(h) for h in stream.handlers}
        assert kinds == {ConsoleGroup, FileGroup}

    def test_level_is_case_insensitive(self, tmp_path):
        assert LogStream("forge", path=tmp_path, level="debug").level == logging.DEBUG

    def test_invalid_timezone_raises(self, tmp_path):
        with pytest.raises(Exception):
            LogStream("forge", path=tmp_path, timezone="Not/AZone")

    def test_info_is_written_and_readable(self, tmp_path):
        stream = LogStream("forge", path=tmp_path, timezone="Asia/Shanghai")
        stream.info("hello %s", "world")
        events = stream.read()
        assert events[0]["msg"] == "hello world"
        assert events[0]["created_at"].endswith("+0800")

    def test_below_level_is_dropped(self, tmp_path):
        stream = LogStream("forge", path=tmp_path, level="WARNING")
        stream.info("skip")
        assert stream.read() == []
