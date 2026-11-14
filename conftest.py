from __future__ import annotations

import pytest

from app.core._global import GlobalLogStreams, GlobalSettings
from app.core.setting import SecretsSetting, SystemSetting


@pytest.fixture(autouse=True)
def _isolated_globals(tmp_path, monkeypatch):
    # Keep tests off the real settings and the real logs directory
    monkeypatch.setattr(
        GlobalSettings, 
        "system_setting", 
        SystemSetting(level="DEBUG", timezone="UTC"),
    )
    monkeypatch.setattr(
        GlobalSettings, 
        "secrets_setting", 
        SecretsSetting(),
    )
    GlobalLogStreams.load(tmp_path / "_logs")
    yield
    GlobalLogStreams.reset()
