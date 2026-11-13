from __future__ import annotations

import pytest

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
