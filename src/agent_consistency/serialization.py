import base64
import dataclasses
import json
from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Any


def to_jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return {"__bytes__": base64.b64encode(value).decode("ascii")}
    if isinstance(value, Path):
        return str(value)
    if dataclasses.is_dataclass(value):
        return to_jsonable(dataclasses.asdict(value))  # type: ignore[arg-type]
    if hasattr(value, "model_dump") and callable(value.model_dump):
        return to_jsonable(value.model_dump())
    if isinstance(value, Mapping):
        return {
            str(key): to_jsonable(value[key])
            for key in sorted(value, key=lambda item: str(item))
        }
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted(
            (to_jsonable(item) for item in value),
            key=lambda item: json.dumps(item, sort_keys=True),
        )
    return repr(value)


def stable_json(value: Any) -> str:
    return json.dumps(
        to_jsonable(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def stable_digest(value: Any) -> str:
    return sha256(stable_json(value).encode("utf-8")).hexdigest()
