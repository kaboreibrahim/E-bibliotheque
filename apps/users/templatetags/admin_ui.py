from __future__ import annotations

from collections.abc import Iterable

from django import template

register = template.Library()


APP_ICONS = {
    "users": "US",
    "documents": "DC",
    "history": "HS",
    "consultations": "CS",
    "filiere": "FL",
    "niveau": "NV",
    "ue": "UE",
    "specialites": "SP",
    "favoris": "FV",
}


def _lookup(item: object, key: str, default: object = None) -> object:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _to_iterable(value: object) -> list[object]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, dict)):
        return list(value)
    return [value]


@register.filter
def admin_app_icon(app_label: object) -> str:
    key = str(app_label or "").strip().lower()
    if key in APP_ICONS:
        return APP_ICONS[key]

    fallback = "".join(character for character in key if character.isalnum()).upper()[:2]
    return fallback or "AD"


@register.filter
def admin_initials(value: object) -> str:
    words = [word for word in str(value or "").replace("-", " ").split() if word]
    if not words:
        return "AD"
    return "".join(word[0] for word in words[:2]).upper()


@register.filter
def admin_total_models(app_list: object) -> int:
    total = 0
    for app in _to_iterable(app_list):
        total += len(_lookup(app, "models", []) or [])
    return total


@register.filter
def admin_total_add_links(app_list: object) -> int:
    total = 0
    for app in _to_iterable(app_list):
        for model in _lookup(app, "models", []) or []:
            if _lookup(model, "add_url"):
                total += 1
    return total
