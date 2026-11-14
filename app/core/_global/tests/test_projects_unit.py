from __future__ import annotations

import os

import pytest

from app.core._global import GlobalSettings
from app.core._global.projects import GlobalProjects
from app.core.project import Project
from app.core.setting import SecretsSetting


@pytest.fixture(autouse=True)
def _projects_dir(tmp_path):
    root = tmp_path / "projects"
    root.mkdir()
    GlobalProjects.load(root)
    yield root
    GlobalProjects.reset()


def _write(root, name: str, version: str = "0.0.1", setting_name: str | None = None) -> None:
    folder = root / name
    folder.mkdir(exist_ok=True)
    file = folder / "project.yml"
    file.write_text(f'name: {setting_name or name}\nversion: "{version}"\n', encoding="utf-8")
    # Force a distinct mtime so a rewrite within the clock resolution is still seen
    stat = file.stat()
    os.utime(file, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))


class TestDiscovery:
    def test_registers_projects_by_folder_name(self, _projects_dir):
        _write(_projects_dir, "alpha")
        _write(_projects_dir, "beta")
        assert GlobalProjects.list_project_names() == ["alpha", "beta"]
        assert all(isinstance(p, Project) for p in GlobalProjects.list_projects())
        assert GlobalProjects.get_project("alpha").name == "alpha"

    def test_skips_hidden_folders_and_folders_without_project_yml(self, _projects_dir):
        _write(_projects_dir, ".hidden")
        (_projects_dir / "plain").mkdir()
        (_projects_dir / "file.txt").write_text("x", encoding="utf-8")
        _write(_projects_dir, "alpha")
        assert GlobalProjects.list_project_names() == ["alpha"]

    def test_load_rejects_non_directory(self, tmp_path):
        with pytest.raises(NotADirectoryError):
            GlobalProjects.load(tmp_path / "missing")

    def test_hands_global_secrets_to_projects(self, _projects_dir, monkeypatch):
        secrets = SecretsSetting(secrets=[{"type": "s3", "key_id": "id-1", "secret": "sec-1"}])
        monkeypatch.setattr(GlobalSettings, "secrets_setting", secrets)
        _write(_projects_dir, "alpha")
        assert GlobalProjects.get_project("alpha").engine.secrets == secrets


class TestHotReload:
    def test_picks_up_added_project(self, _projects_dir):
        _write(_projects_dir, "alpha")
        assert GlobalProjects.list_project_names() == ["alpha"]
        _write(_projects_dir, "beta")
        assert GlobalProjects.list_project_names() == ["alpha", "beta"]

    def test_drops_removed_project(self, _projects_dir):
        _write(_projects_dir, "alpha")
        _write(_projects_dir, "beta")
        assert GlobalProjects.get_project("beta") is not None
        (_projects_dir / "beta" / "project.yml").unlink()
        assert GlobalProjects.list_project_names() == ["alpha"]
        assert GlobalProjects.get_project("beta") is None

    def test_unchanged_project_keeps_instance(self, _projects_dir):
        _write(_projects_dir, "alpha")
        first = GlobalProjects.get_project("alpha")
        assert GlobalProjects.get_project("alpha") is first

    def test_edited_project_is_rebuilt(self, _projects_dir):
        _write(_projects_dir, "alpha", version="0.0.1")
        first = GlobalProjects.get_project("alpha")
        _write(_projects_dir, "alpha", version="0.0.2")
        second = GlobalProjects.get_project("alpha")
        assert second is not first
        assert second.setting.version == "0.0.2"

    def test_changed_model_rebuilds_project(self, _projects_dir):
        _write(_projects_dir, "alpha")
        first = GlobalProjects.get_project("alpha")
        (_projects_dir / "alpha" / "models" / "m.sql").write_text("select 1", encoding="utf-8")
        assert GlobalProjects.get_project("alpha") is not first

    def test_engine_output_does_not_rebuild_project(self, _projects_dir):
        _write(_projects_dir, "alpha")
        first = GlobalProjects.get_project("alpha")
        (_projects_dir / "alpha" / ".engine" / "out.txt").write_text("x", encoding="utf-8")
        assert GlobalProjects.get_project("alpha") is first

    def test_broken_project_recovers_once_fixed(self, _projects_dir):
        _write(_projects_dir, "alpha", setting_name="other")
        assert GlobalProjects.get_project("alpha") is None
        _write(_projects_dir, "alpha")
        assert GlobalProjects.get_project("alpha").name == "alpha"
        assert "alpha" not in GlobalProjects.errors


class TestBrokenProject:
    def test_error_is_recorded_and_others_still_load(self, _projects_dir):
        _write(_projects_dir, "alpha")
        _write(_projects_dir, "bad", setting_name="other")
        assert GlobalProjects.list_project_names() == ["alpha"]
        assert "must be 'bad'" in GlobalProjects.errors["bad"]

    def test_strict_get_reports_the_load_error(self, _projects_dir):
        _write(_projects_dir, "bad", setting_name="other")
        with pytest.raises(ValueError, match="failed to load"):
            GlobalProjects.get_project("bad", strict=True)


class TestGetProject:
    def test_missing_returns_none(self):
        assert GlobalProjects.get_project("nope") is None

    def test_missing_strict_raises(self):
        with pytest.raises(ValueError, match="not found"):
            GlobalProjects.get_project("nope", strict=True)

    def test_reset_clears_state(self, _projects_dir):
        _write(_projects_dir, "alpha")
        GlobalProjects.refresh()
        GlobalProjects.reset()
        assert GlobalProjects.projects == {}
        assert GlobalProjects.errors == {}
        assert GlobalProjects.projects_path == GlobalProjects._default_projects_path
