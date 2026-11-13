from __future__ import annotations

from types import SimpleNamespace

import pytest
import yaml

from app.core.project import engine as engine_module
from app.core.project.engine import ProjectEngine
from app.core.project.setting import ProjectSetting
from app.core.setting import SecretsSetting


def _setting(**engine) -> ProjectSetting:
    return ProjectSetting(
        name="demo",
        version="0.0.1",
        extensions=["httpfs"],
        engine=engine,
    )


@pytest.fixture
def engine_path(tmp_path):
    # <root>/projects/demo/.engine, so that macro_path resolves to <root>/engine/macros
    return tmp_path / "projects" / "demo" / ".engine"


def _engine(engine_path, secrets=None, **engine_setting) -> ProjectEngine:
    return ProjectEngine(
        path=engine_path,
        project_setting=_setting(**engine_setting),
        assets_path=engine_path.parent / "assets",
        secrets=secrets,
    )


_SECRETS = SecretsSetting(
    secrets=[
        {
            "type": "s3",
            "key_id": "id-1",
            "secret": "sec-1",
            "scope": "s3://bucket/",
            "endpoint": "oss-cn-shanghai.aliyuncs.com",
        }
    ]
)


def _load(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


class TestProjectEngineInit:
    def test_derived_paths(self, engine_path):
        engine = _engine(engine_path)
        assert engine.project_name == "demo"
        assert engine.duckdb_file_path == engine_path / "demo.duckdb"
        assert engine.macro_path == engine_path.parents[2] / "engine" / "macros"


class TestProjectEngineRender:
    def test_writes_dbt_project(self, engine_path):
        engine = _engine(engine_path, models={"marts": {"+materialized": "table"}})
        engine.render()
        content = _load(engine_path / "dbt_project.yml")
        assert content["name"] == "demo"
        assert content["profile"] == "demo"
        assert content["macro-paths"] == [str(engine.macro_path)]
        assert content["models"] == {"demo": {"marts": {"+materialized": "table"}}}

    def test_writes_profile(self, engine_path):
        engine = _engine(engine_path, threads=4)
        engine.render()
        output = _load(engine_path / "profiles.yml")["demo"]["outputs"]["database"]
        assert output["type"] == "duckdb"
        assert output["path"] == str(engine.duckdb_file_path)
        assert output["external_root"] == str(engine.assets_path)
        assert output["threads"] == 4
        assert output["extensions"] == ["httpfs"]

    def test_profile_has_no_secrets_by_default(self, engine_path):
        _engine(engine_path).render()
        output = _load(engine_path / "profiles.yml")["demo"]["outputs"]["database"]
        assert "secrets" not in output

    def test_profile_carries_secrets_with_plain_credentials(self, engine_path):
        _engine(engine_path, secrets=_SECRETS).render()
        output = _load(engine_path / "profiles.yml")["demo"]["outputs"]["database"]
        assert output["secrets"] == [
            {
                "type": "s3",
                "key_id": "id-1",
                "secret": "sec-1",
                "scope": "s3://bucket/",
                "endpoint": "oss-cn-shanghai.aliyuncs.com",
            }
        ]

    def test_profile_is_owner_only(self, engine_path):
        engine_path.mkdir(parents=True)
        (engine_path / "profiles.yml").write_text("old", encoding="utf-8")
        (engine_path / "profiles.yml").chmod(0o644)
        _engine(engine_path, secrets=_SECRETS).render()
        assert (engine_path / "profiles.yml").stat().st_mode & 0o777 == 0o600

    def test_writes_sources_when_defined(self, engine_path):
        engine = _engine(engine_path, sources=[{"name": "tushare", "tables": [{"name": "tradedates"}]}])
        engine.render()
        content = _load(engine_path / "models" / "sources.yml")
        assert content["version"] == 2
        assert content["sources"][0]["name"] == "tushare"
        assert content["sources"][0]["tables"] == [{"name": "tradedates"}]

    def test_removes_stale_sources_when_none_defined(self, engine_path):
        stale = engine_path / "models" / "sources.yml"
        stale.parent.mkdir(parents=True)
        stale.write_text("stale", encoding="utf-8")
        _engine(engine_path).render()
        assert not stale.exists()

    def test_returns_engine_path(self, engine_path):
        assert _engine(engine_path).render() == engine_path

    def test_keeps_existing_duckdb_file(self, engine_path):
        engine = _engine(engine_path)
        engine_path.mkdir(parents=True)
        engine.duckdb_file_path.write_bytes(b"data")
        engine.render()
        assert engine.duckdb_file_path.read_bytes() == b"data"


class TestProjectEngineRun:
    @staticmethod
    def _fake_runner(monkeypatch, result):
        calls: list[list[str]] = []

        class _Runner:
            def invoke(self, cmd):
                calls.append(cmd)
                return result

        monkeypatch.setattr(engine_module, "dbtRunner", _Runner)
        return calls

    def test_invokes_dbt_with_project_and_profiles_dir(self, engine_path, monkeypatch):
        calls = self._fake_runner(monkeypatch, SimpleNamespace(success=True, exception=None))
        _engine(engine_path).run("run", "--select", "mart")
        assert calls == [
            ["run", "--select", "mart", "--project-dir", str(engine_path), "--profiles-dir", str(engine_path)]
        ]
        assert (engine_path / "dbt_project.yml").is_file()

    def test_failure_raises_with_cause(self, engine_path, monkeypatch):
        cause = ValueError("bad model")
        self._fake_runner(monkeypatch, SimpleNamespace(success=False, exception=cause))
        with pytest.raises(RuntimeError, match="dbt run failed: bad model") as info:
            _engine(engine_path).run("run")
        assert info.value.__cause__ is cause

    def test_failure_without_exception_raises(self, engine_path, monkeypatch):
        self._fake_runner(monkeypatch, SimpleNamespace(success=False, exception=None))
        with pytest.raises(RuntimeError, match="^dbt test failed$"):
            _engine(engine_path).run("test")
