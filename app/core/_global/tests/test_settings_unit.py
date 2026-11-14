from __future__ import annotations

import pytest

from app.core._global import GlobalSettings
from app.core.setting import SecretsSetting, SystemSetting


class TestGlobalSettings:
    def test_load_reads_system_yml(self, tmp_path):
        (tmp_path / "system.yml").write_text("level: warning\ntimezone: Australia/Sydney\n", encoding="utf-8")
        GlobalSettings.load(tmp_path)
        assert GlobalSettings.get_setting_path() == tmp_path.resolve()
        assert GlobalSettings.get_system().level == "WARNING"
        assert GlobalSettings.get_system().timezone == "Australia/Sydney"

    def test_load_reads_secrets_yml(self, tmp_path):
        (tmp_path / "system.yml").write_text("", encoding="utf-8")
        (tmp_path / "secrets.yml").write_text(
            "secrets:\n  - type: s3\n    key_id: id-1\n    secret: sec-1\n",
            encoding="utf-8",
        )
        GlobalSettings.load(tmp_path)
        assert GlobalSettings.get_secrets().to_duckdb() == [{"type": "s3", "key_id": "id-1", "secret": "sec-1"}]

    def test_missing_secrets_yml_gives_empty_secrets(self, tmp_path):
        (tmp_path / "system.yml").write_text("", encoding="utf-8")
        GlobalSettings.load(tmp_path)
        assert GlobalSettings.get_secrets() == SecretsSetting()

    def test_load_rejects_non_directory(self, tmp_path):
        with pytest.raises(NotADirectoryError):
            GlobalSettings.load(tmp_path / "missing")

    def test_load_missing_system_yml_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            GlobalSettings.load(tmp_path)

    def test_default_path_loads_repo_settings(self):
        GlobalSettings.reset()
        assert isinstance(GlobalSettings.get_system(), SystemSetting)
        assert isinstance(GlobalSettings.get_secrets(), SecretsSetting)
        assert GlobalSettings.get_setting_path().name == "settings"

    def test_reset_clears_state(self, tmp_path):
        (tmp_path / "system.yml").write_text("", encoding="utf-8")
        GlobalSettings.load(tmp_path)
        GlobalSettings.reset()
        assert GlobalSettings.system_setting is None
        assert GlobalSettings.secrets_setting is None
        assert GlobalSettings.setting_path is None
