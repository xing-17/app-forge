from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import Field, SecretStr, field_validator

from ._abstract import AbstractSetting


class S3SecretSetting(AbstractSetting):
    """
    DuckDB s3 secret, also covers s3 compatible storage such as aliyun oss

    Attributes:
    ----------
        type (Literal["s3"]):
            Secret type, fixed as "s3"
        key_id (SecretStr):
            Access key id
        secret (SecretStr):
            Access key secret
        scope (str | None):
            Path prefix this secret applies to (e.g. "s3://bucket/")
        region (str | None):
            Storage region
        endpoint (str | None):
            Storage endpoint, required for s3 compatible storage
        url_style (Literal["vhost", "path"] | None):
            Url style used to address buckets

    Methods:
    ----------
        to_duckdb() -> dict[str, Any]:
            Export as a duckdb secret with plain credentials, unset fields omitted

    """

    type: Literal["s3"] = "s3"
    key_id: SecretStr = Field(
        ...,
        description="Access key id",
    )
    secret: SecretStr = Field(
        ...,
        description="Access key secret",
    )
    scope: str | None = Field(
        default=None,
        description="[Optional] Path prefix this secret applies to",
    )
    region: str | None = Field(
        default=None,
        description="[Optional] Storage region",
    )
    endpoint: str | None = Field(
        default=None,
        description="[Optional] Storage endpoint",
    )
    url_style: Literal["vhost", "path"] | None = Field(
        default=None,
        description="[Optional] Url style used to address buckets",
    )

    def to_duckdb(self) -> dict[str, Any]:
        _res: dict[str, Any] = self.model_dump(exclude_none=True)
        _res["key_id"] = self.key_id.get_secret_value()
        _res["secret"] = self.secret.get_secret_value()
        return _res


# Every member must have a `type` literal and implement `to_duckdb()`
UnionSecretSetting = Annotated[
    Union[S3SecretSetting,],
    Field(discriminator="type"),
]


class SecretsSetting(AbstractSetting):
    """
    Secrets shared by all projects, loaded from settings/secrets.yml

    Attributes:
    ----------
        secrets (list[UnionSecretSetting]):
            Secrets handed to every project engine, each picked by its `type`

    Methods:
    ----------
        to_duckdb() -> list[dict[str, Any]]:
            Export all secrets as duckdb secrets with plain credentials

    """

    secrets: list[UnionSecretSetting] = Field(
        default_factory=list,
        description="[Optional] Secrets shared by all projects",
    )

    @field_validator("secrets", mode="before")
    @classmethod
    def _empty_secrets(
        cls,
        value: Any,
    ) -> Any:
        # An empty yaml key (`secrets:`) loads as None
        if value is None:
            return []
        return value

    def to_duckdb(self) -> list[dict[str, Any]]:
        _res: list[dict[str, Any]] = []
        for _secret in self.secrets:
            _res.append(_secret.to_duckdb())
        return _res
