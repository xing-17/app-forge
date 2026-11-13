from __future__ import annotations

from pathlib import Path
from typing import Any, Self

import yaml
from pydantic import BaseModel, ConfigDict


class AbstractSetting(BaseModel):
    """
    Abstract setting for forge, immutable and rejecting unknown fields

    Methods:
    ----------
        from_yaml(path: str | Path) -> AbstractSetting:
            Load the setting from a yaml file; an empty file is treated as an empty mapping
        export() -> dict[str, Any]:
            Export the setting as a json compatible dictionary

    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    @classmethod
    def from_yaml(
        cls,
        path: str | Path,
    ) -> Self:
        _path: Path = Path(path).expanduser().resolve()
        if not _path.is_file():
            _msg: str = f"YAML not found: {_path}"
            raise FileNotFoundError(_msg)

        _content: str = _path.read_text(encoding="utf-8")
        _loaded: dict[str, Any] = yaml.safe_load(_content) or {}
        return cls.model_validate(_loaded)

    def export(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
