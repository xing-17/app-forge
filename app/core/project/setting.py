from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator


class _ImmutableSetting(BaseModel):
    """
    Internal base class for project settings, immutable and rejecting unknown fields

    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )


class TableSetting(_ImmutableSetting):
    """
    Typed view of a table in a source

    Attributes:
    ----------
        name (str):
            Table name

    """

    name: str = Field(
        ...,
        description="The name of the table.",
    )


class SourceSetting(_ImmutableSetting):
    """
    Typed view of a dbt source

    Attributes:
    ----------
        name (str):
            Source name
        meta (dict[str, Any]):
            Source metadata, passed to dbt as is
        tables (list[TableSetting]):
            Tables in the source

    """

    name: str = Field(
        ...,
        description="The name of the source.",
    )
    meta: dict[str, Any] = Field(
        default_factory=dict,
        description="The metadata of the source.",
    )
    tables: list[TableSetting] = Field(
        default_factory=list,
        description="The list of tables in the source.",
    )


class EngineSetting(_ImmutableSetting):
    """
    Typed view of the engine section in project.yml

    Attributes:
    ----------
        type (Literal["dbt"]):
            Engine type, only dbt is supported
        threads (int):
            Number of threads for the engine
        models (dict[str, Any]):
            Native dbt `models` config per folder, passed to dbt as is
        sources (list[SourceSetting]):
            Sources for the engine

    """

    type: Literal["dbt"] = "dbt"
    threads: int = Field(
        default=1,
        ge=1,
        description="The number of threads for the engine.",
    )
    models: dict[str, Any] = Field(
        default_factory=dict,
        description="Native dbt `models` config per folder, passed to dbt as is.",
    )
    sources: list[SourceSetting] = Field(
        default_factory=list,
        description="The list of sources for the engine.",
    )

    @field_validator("models", mode="before")
    @classmethod
    def _empty_models(cls, value: Any) -> Any:
        # An empty yaml key (`models:`) loads as None
        return {} if value is None else value

    @field_validator("sources", mode="before")
    @classmethod
    def _empty_sources(cls, value: Any) -> Any:
        return [] if value is None else value


class ProjectSetting(_ImmutableSetting):
    """
    Typed view of <project>/project.yml

    Attributes:
    ----------
        name (str):
            Project name, must match the project directory name
        version (str):
            Project version
        description (str):
            Project description
        extensions (list[str]):
            Duckdb extensions used in the project
        engine (EngineSetting):
            Engine setting for the project

    Methods:
    ----------
        from_file(path: str | Path) -> ProjectSetting:
            Load the project setting from a yaml file

    """

    name: str = Field(
        ...,
        description="The name of the project.",
    )
    version: str = Field(
        ...,
        description="The version of the project.",
    )
    description: str = Field(
        default="",
        description="The description of the project.",
    )
    extensions: list[str] = Field(
        default_factory=list,
        description="The list of extensions used in the project.",
    )
    engine: EngineSetting = Field(
        default_factory=EngineSetting,
        description="The engine settings for the project.",
    )

    @field_validator("engine", mode="before")
    @classmethod
    def _empty_engine(cls, value: Any) -> Any:
        return {} if value is None else value

    @classmethod
    def from_file(
        cls,
        path: str | Path,
    ) -> ProjectSetting:
        _path: Path = Path(path).expanduser().resolve()
        _content: str = _path.read_text(encoding="utf-8")
        _loaded: dict[str, Any] = yaml.safe_load(_content) or {}
        return cls.model_validate(_loaded)
