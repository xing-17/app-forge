from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.setting import SystemSetting


class TestSystemSetting:
    def test_defaults(self):
        setting = SystemSetting()
        assert setting.name == "forge"
        assert setting.alias == "武穆"
        assert setting.version == "0.0.1"
        assert setting.timezone is None

    def test_unknown_field_is_rejected(self):
        with pytest.raises(ValidationError):
            SystemSetting(unknown=1)

    def test_is_frozen(self):
        setting = SystemSetting()
        with pytest.raises(ValidationError):
            setting.name = "other"

    def test_valid_timezone(self):
        assert SystemSetting(timezone="Australia/Sydney").timezone == "Australia/Sydney"

    def test_unknown_timezone_is_rejected(self):
        with pytest.raises(ValidationError, match="unknown timezone"):
            SystemSetting(timezone="Mars/Olympus")

    def test_export(self):
        assert SystemSetting(timezone="UTC").export() == {
            "name": "forge",
            "alias": "武穆",
            "version": "0.0.1",
            "timezone": "UTC",
        }


class TestSystemSettingFromYaml:
    def test_loads_yaml(self, tmp_path):
        file = tmp_path / "system.yml"
        file.write_text(
            "# comment\nalias: 武穆\nversion: 0.1.0\ntimezone: Australia/Sydney\n",
            encoding="utf-8",
        )
        setting = SystemSetting.from_yaml(file)
        assert setting.version == "0.1.0"
        assert setting.timezone == "Australia/Sydney"

    def test_empty_file_gives_defaults(self, tmp_path):
        file = tmp_path / "system.yml"
        file.write_text("", encoding="utf-8")
        assert SystemSetting.from_yaml(file) == SystemSetting()

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="YAML not found"):
            SystemSetting.from_yaml(tmp_path / "missing.yml")
