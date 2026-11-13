from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.setting import S3SecretSetting, SecretsSetting


def _s3(**kwargs) -> S3SecretSetting:
    return S3SecretSetting(key_id="id-1", secret="sec-1", **kwargs)


class TestS3SecretSetting:
    def test_credentials_are_masked(self):
        setting = _s3()
        assert "id-1" not in repr(setting)
        assert "sec-1" not in repr(setting)
        assert "sec-1" not in str(setting.export())

    def test_credentials_are_required(self):
        with pytest.raises(ValidationError):
            S3SecretSetting(key_id="id-1")

    def test_only_s3_type_is_supported(self):
        with pytest.raises(ValidationError):
            _s3(type="gcs")

    def test_invalid_url_style_is_rejected(self):
        with pytest.raises(ValidationError):
            _s3(url_style="subdomain")

    def test_to_duckdb_reveals_credentials_and_omits_unset(self):
        assert _s3().to_duckdb() == {"type": "s3", "key_id": "id-1", "secret": "sec-1"}

    def test_to_duckdb_keeps_set_fields(self):
        setting = _s3(
            scope="s3://bucket/",
            region="cn-shanghai",
            endpoint="oss-cn-shanghai.aliyuncs.com",
            url_style="vhost",
        )
        assert setting.to_duckdb() == {
            "type": "s3",
            "key_id": "id-1",
            "secret": "sec-1",
            "scope": "s3://bucket/",
            "region": "cn-shanghai",
            "endpoint": "oss-cn-shanghai.aliyuncs.com",
            "url_style": "vhost",
        }


class TestSecretsSetting:
    def test_default_is_empty(self):
        assert SecretsSetting().secrets == []

    def test_none_secrets_become_empty(self):
        assert SecretsSetting(secrets=None).secrets == []

    def test_unknown_field_is_rejected(self):
        with pytest.raises(ValidationError):
            SecretsSetting(unknown=1)

    def test_secret_is_picked_by_type(self):
        setting = SecretsSetting(secrets=[{"type": "s3", "key_id": "id-1", "secret": "sec-1"}])
        assert isinstance(setting.secrets[0], S3SecretSetting)

    def test_missing_type_is_rejected(self):
        with pytest.raises(ValidationError, match="discriminator 'type'"):
            SecretsSetting(secrets=[{"key_id": "id-1", "secret": "sec-1"}])

    def test_unknown_type_is_rejected(self):
        with pytest.raises(ValidationError, match="does not match any of the expected tags"):
            SecretsSetting(secrets=[{"type": "gcs", "key_id": "id-1", "secret": "sec-1"}])

    def test_to_duckdb(self):
        setting = SecretsSetting(
            secrets=[{"type": "s3", "key_id": "id-1", "secret": "sec-1", "scope": "s3://a/"}],
        )
        assert setting.to_duckdb() == [{"type": "s3", "key_id": "id-1", "secret": "sec-1", "scope": "s3://a/"}]


class TestSecretsSettingFromYaml:
    def test_loads_yaml(self, tmp_path):
        file = tmp_path / "secrets.yml"
        file.write_text(
            "# comment\n"
            "secrets:\n"
            "  - type: s3\n"
            "    key_id: id-1\n"
            "    secret: sec-1\n"
            "    scope: s3://bucket/\n"
            "    region: cn-shanghai\n"
            "    url_style: vhost\n"
            "    endpoint: oss-cn-shanghai.aliyuncs.com\n",
            encoding="utf-8",
        )
        setting = SecretsSetting.from_yaml(file)
        assert len(setting.secrets) == 1
        assert setting.secrets[0].endpoint == "oss-cn-shanghai.aliyuncs.com"
        assert setting.to_duckdb()[0]["key_id"] == "id-1"

    def test_key_without_items_gives_empty(self, tmp_path):
        file = tmp_path / "secrets.yml"
        file.write_text("secrets:\n", encoding="utf-8")
        assert SecretsSetting.from_yaml(file).secrets == []

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="YAML not found"):
            SecretsSetting.from_yaml(tmp_path / "missing.yml")
