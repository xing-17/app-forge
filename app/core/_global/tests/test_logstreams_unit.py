from __future__ import annotations

import logging

from app.core._global import (
    GlobalLogStreams,
    GlobalSettings,
)
from app.core.logstream import LogStream
from app.core.setting import SystemSetting


class TestGlobalLogStreams:
    def test_get_builds_stream_from_system_setting(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            GlobalSettings,
            "system_setting",
            SystemSetting(level="warning", timezone="Australia/Sydney"),
        )
        stream = GlobalLogStreams.get("demo")
        assert isinstance(stream, LogStream)
        assert stream.name == "demo"
        assert stream.level == logging.WARNING
        stream.warning("hi")
        assert (tmp_path / "_logs" / "demo.log").exists()

    def test_get_falls_back_to_utc_without_timezone(self, monkeypatch):
        monkeypatch.setattr(GlobalSettings, "system_setting", SystemSetting())
        stream = GlobalLogStreams.get("demo")
        stream.error("boom")
        assert stream.read(limit=1)[0]["created_at"].endswith("+0000")

    def test_get_is_cached_per_name(self):
        assert GlobalLogStreams.get("a") is GlobalLogStreams.get("a")
        assert GlobalLogStreams.get("a") is not GlobalLogStreams.get("b")
        assert GlobalLogStreams.list_names() == ["a", "b"]

    def test_load_drops_cached_streams(self, tmp_path):
        first = GlobalLogStreams.get("a")
        GlobalLogStreams.load(tmp_path / "other")
        assert GlobalLogStreams.list_names() == []
        assert GlobalLogStreams.get("a") is not first
