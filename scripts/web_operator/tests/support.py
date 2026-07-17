from __future__ import annotations

import json
import tempfile
from pathlib import Path

from scripts.web_operator.config import default_config_dict


def write_temp_config(**overrides) -> Path:
    data = default_config_dict()
    for key, value in overrides.items():
        if key in data and isinstance(data[key], dict) and isinstance(value, dict):
            data[key].update(value)
        else:
            data[key] = value
    fd, name = tempfile.mkstemp(suffix=".json")
    path = Path(name)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path
