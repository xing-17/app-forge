from __future__ import annotations

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator

from ._abstract import AbstractSetting


class SystemSetting(AbstractSetting):
    """
    Forge system setting, loaded from settings/system.yml

    Attributes:
    ----------
        name (str):
            System name
        alias (str):
            System alias
        version (str):
            System version
        timezone (str | None):
            System timezone (IANA name, e.g. "Australia/Sydney")

    """

    name: str = Field(
        default="forge",
        description="[Optional] System name",
    )
    alias: str = Field(
        default="武穆",
        description="[Optional] System alias",
    )
    version: str = Field(
        default="0.0.1",
        description="[Optional] System version",
    )
    timezone: str | None = Field(
        default=None,
        description="[Optional] System timezone",
    )

    @field_validator("timezone")
    @classmethod
    def _check_timezone(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return value
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as e:
            _msg: str = f"unknown timezone: {value}"
            raise ValueError(_msg) from e
        return value
