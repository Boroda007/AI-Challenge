import fnmatch
import json
import re
from pathlib import Path

_REGISTRY = json.loads(Path("models.json").read_text(encoding="utf-8"))["models"]


def _normalize(model: str) -> str:
    """Нормализует id модели до имени для поиска в реестре.

    "qwen3.5:9b"        → "qwen3.5"   (убирает тег после ":")
    "qwen/qwen3-32b"    → "qwen3"     (убирает провайдер и суффикс размера)
    "deepseek-v4-flash" → без изменений
    """
    base = model.split(":", 1)[0]
    base = base.rsplit("/", 1)[-1]
    base = re.sub(r"-\d+[a-z]*$", "", base, flags=re.IGNORECASE)
    return base


def _resolve(model: str) -> dict | None:
    """Ищет профиль: точное совпадение (id или нормализованное) → glob."""
    base = _normalize(model)
    spec = _REGISTRY.get(base) or _REGISTRY.get(model)
    if spec is None:
        for pattern, s in _REGISTRY.items():
            if fnmatch.fnmatch(base, pattern):
                spec = s
                break
    return spec


def effort_levels(model: str) -> list[str]:
    """
    Допустимые уровни reasoning_effort из models.json.
    Если модель не найдена или не поддерживает reasoning — [].
    """
    spec = _resolve(model)
    if spec is None or "reasoning" not in spec:
        return []
    r = spec["reasoning"]
    if r.get("mode", "unsupported") == "unsupported":
        return []
    return r.get("effort", {}).get("levels", [])


def reasoning_kwargs(
    model: str, enable: bool | None = None, effort: str | None = None
) -> dict:
    """
    Возвращает dict с kwargs для reasoning, который можно распаковать в create().
    Если модель не известна — возвращает {} (ничего не меняется).
    """
    spec = _resolve(model)
    if spec is None or "reasoning" not in spec:
        return {}

    r = spec["reasoning"]
    mode = r.get("mode", "unsupported")
    if mode == "unsupported":
        return {}

    out: dict = {}

    # Флаг включения
    if mode == "toggle" and enable is not None:
        e = r.get("enable", {})
        if e.get("location") != "none":
            _put(out, e["location"], e["key"], e["on"] if enable else e["off"])

    if enable is False:
        return out

    # Уровень усилия
    if (ef := r.get("effort")) and enable is not False:
        levels = ef.get("levels", [])
        value = effort if effort in levels else ef.get("default")
        if value is not None:
            _put(out, ef["location"], ef["param"], value)

    return out


def _put(d: dict, location: str, key: str, value):
    """Кладёт значение в нужное место, поддерживая вложенные ключи через точку."""
    if location == "top_level":
        d[key] = value
        return
    node = d.setdefault(location, {})
    parts = key.split(".")
    for p in parts[:-1]:
        node = node.setdefault(p, {})
    node[parts[-1]] = value
