from __future__ import annotations

import pytest

from app.core._global import GlobalLogStreams
from app.core.project import Project, ProjectEngine
from app.core.setting import SecretsSetting


def _make_project(root, name: str = "demo", setting_name: str | None = None):
    folder = root / name
    folder.mkdir(parents=True)
    (folder / "project.yml").write_text(
        f'name: {setting_name or name}\nversion: "0.0.1"\n',
        encoding="utf-8",
    )
    return folder


class TestProjectInit:
    def test_loads_setting_and_paths(self, tmp_path):
        folder = _make_project(tmp_path)
        project = Project(folder)
        assert project.name == "demo"
        assert project.setting.version == "0.0.1"
        assert project.setting_path == folder.resolve() / "project.yml"
        assert project.models_path == folder.resolve() / "models"
        assert project.assets_path == folder.resolve() / "assets"
        assert project.engine_path == folder.resolve() / ".engine"

    def test_accepts_str_path(self, tmp_path):
        folder = _make_project(tmp_path)
        assert Project(str(folder)).name == "demo"

    def test_creates_required_dirs(self, tmp_path):
        folder = _make_project(tmp_path)
        Project(folder)
        for name in (".engine", "models", "assets"):
            assert (folder / name).is_dir()

    def test_builds_engine(self, tmp_path):
        project = Project(_make_project(tmp_path))
        assert isinstance(project.engine, ProjectEngine)
        assert project.engine.path == project.engine_path
        assert project.engine.assets_path == project.assets_path

    def test_hands_secrets_to_engine(self, tmp_path):
        secrets = SecretsSetting(secrets=[{"type": "s3", "key_id": "id-1", "secret": "sec-1"}])
        project = Project(_make_project(tmp_path), secrets=secrets)
        assert project.engine.secrets == secrets

    def test_engine_has_no_secrets_by_default(self, tmp_path):
        project = Project(_make_project(tmp_path))
        assert project.engine.secrets == SecretsSetting()

    def test_logger_defaults_to_global_stream_named_after_project(self, tmp_path):
        project = Project(_make_project(tmp_path))
        assert project.logstream is GlobalLogStreams.get("project/demo")
        assert project.engine.logstream is project.logstream

    def test_invalid_project_creates_no_logger(self, tmp_path):
        with pytest.raises(ValueError):
            Project(_make_project(tmp_path, setting_name="other"))
        assert GlobalLogStreams.list_names() == []


class TestProjectFiles:
    def test_lists_nested_files_sorted(self, tmp_path):
        folder = _make_project(tmp_path)
        project = Project(folder)
        (folder / "models" / "sub").mkdir()
        (folder / "models" / "b.sql").write_text("b")
        (folder / "models" / "sub" / "a.sql").write_text("a")
        (folder / "assets" / "data.parquet").write_text("x")
        (folder / "assets" / "ignored.csv").write_text("x")
        root = folder.resolve()
        assert project.models == [root / "models" / "b.sql", root / "models" / "sub" / "a.sql"]
        assert project.assets == [root / "assets" / "data.parquet"]

    def test_empty_when_folders_are_removed(self, tmp_path):
        folder = _make_project(tmp_path)
        project = Project(folder)
        (folder / "models").rmdir()
        (folder / "assets").rmdir()
        assert project.models == []
        assert project.assets == []

    def test_fingerprint_is_stable(self, tmp_path):
        project = Project(_make_project(tmp_path))
        assert project.fingerprint == project.fingerprint

    @pytest.mark.parametrize("file_name", ["models/new.sql", "assets/new.parquet"])
    def test_fingerprint_changes_with_files(self, tmp_path, file_name):
        folder = _make_project(tmp_path)
        project = Project(folder)
        before = project.fingerprint
        (folder / file_name).write_text("x")
        assert project.fingerprint != before

    def test_fingerprint_changes_with_project_yml(self, tmp_path):
        folder = _make_project(tmp_path)
        project = Project(folder)
        before = project.fingerprint
        (folder / "project.yml").write_text('name: demo\nversion: "0.0.2"\n', encoding="utf-8")
        assert project.fingerprint != before

    def test_fingerprint_ignores_engine(self, tmp_path):
        folder = _make_project(tmp_path)
        project = Project(folder)
        before = project.fingerprint
        (folder / ".engine" / "profiles.yml").write_text("x")
        assert project.fingerprint == before


class TestProjectValidation:
    def test_missing_project_dir_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="project folder not found"):
            Project(tmp_path / "missing")

    def test_missing_setting_file_raises(self, tmp_path):
        folder = tmp_path / "demo"
        folder.mkdir()
        with pytest.raises(FileNotFoundError, match="project.yml not found"):
            Project(folder)

    def test_name_mismatch_raises(self, tmp_path):
        folder = _make_project(tmp_path, setting_name="other")
        with pytest.raises(ValueError, match="must be 'demo'"):
            Project(folder)
