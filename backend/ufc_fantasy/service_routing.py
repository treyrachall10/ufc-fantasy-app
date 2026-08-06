"""
Map ``SERVICE_TYPE`` to Django ``ROOT_URLCONF`` modules.

Each non-api role exposes only that worker's Pub/Sub push endpoint.
"""

from __future__ import annotations

# service_type -> dotted URLConf module path
SERVICE_TYPE_URLCONFS: dict[str, str] = {
    "api": "ufc_fantasy.public_urls",
    "fights_in_event": "ufc_fantasy.fights_in_event_urls",
    "fighter_profile": "ufc_fantasy.fighter_profile_urls",
    "fight_stats": "ufc_fantasy.fight_stats_urls",
    "career_stats": "ufc_fantasy.career_stats_urls",
    "score_fight": "ufc_fantasy.score_fight_urls",
}


def resolve_root_urlconf(service_type: str | None) -> str:
    """
    Return the ROOT_URLCONF for ``service_type``.

    Unset, empty, or whitespace-only values default to ``api``.
    Unsupported values raise ``ValueError``.
    """
    if service_type is None:
        key = "api"
    else:
        key = service_type.strip() or "api"

    try:
        return SERVICE_TYPE_URLCONFS[key]
    except KeyError as exc:
        supported = ", ".join(sorted(SERVICE_TYPE_URLCONFS))
        raise ValueError(
            f"Unsupported SERVICE_TYPE={service_type!r}. Supported values: {supported}"
        ) from exc
