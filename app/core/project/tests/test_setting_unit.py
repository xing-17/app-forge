from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.project.setting import (
    EngineSetting,
    ProjectSetting,
    SourceSetting,
    TableSetting,
)


class TestEngineSetting:
    def test_defaults(self):
        setting = EngineSetting()
        assert setting.type == "dbt"
        assert setting.threads == 1
        assert setting.models == {}
        assert setting.sources == []

    def test_none_models_and_sources_become_empty(self):
        setting = EngineSetting(models=None, sources=None)
        assert setting.models == {}
        assert setting.sources == []

    def test_threads_must_be_positive(self):
        with pytest.raises(ValidationError):
            EngineSetting(threads=0)

    def test_unsupported_type_is_rejected(self):
        with pytest.raises(ValidationError):
            EngineSetting(type="spark")


class TestSourceSetting:
    def test_parses_tables(self):
        setting = SourceSetting(name="tushare", tables=[{"name": "tradedates"}])
        assert setting.tables == [TableSetting(name="tradedates")]

    def test_unknown_field_is_rejected(self):
        with pytest.raises(ValidationError):
            SourceSetting(name="tushare", unknown=1)


class TestProjectSetting:
    def test_missing_required_fields_raise(self):
        with pytest.raises(ValidationError):
            ProjectSetting(name="demo")

    def test_none_engine_becomes_default(self):
        setting = ProjectSetting(name="demo", version="0.0.1", engine=None)
        assert setting.engine == EngineSetting()

    def test_is_frozen(self):
        setting = ProjectSetting(name="demo", version="0.0.1")
        with pytest.raises(ValidationError):
            setting.name = "other"


class TestProjectSettingFromFile:
    def test_loads_yaml(self, tmp_path):
        file = tmp_path / "project.yml"
        file.write_text(
            "name: demo\n"
            'version: "0.0.1"\n'
            "extensions: [httpfs]\n"
            "engine:\n"
            "  threads: 2\n"
            "  sources:\n"
            "    - name: tushare\n"
            "      tables:\n"
            "        - name: tradedates\n",
            encoding="utf-8",
        )
        setting = ProjectSetting.from_file(file)
        assert setting.name == "demo"
        assert setting.extensions == ["httpfs"]
        assert setting.engine.threads == 2
        assert setting.engine.sources[0].tables[0].name == "tradedates"

    def test_empty_file_raises_validation_error(self, tmp_path):
        file = tmp_path / "project.yml"
        file.write_text("", encoding="utf-8")
        with pytest.raises(ValidationError):
            ProjectSetting.from_file(file)

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            ProjectSetting.from_file(tmp_path / "missing.yml")
