"""
Map ``SERVICE_TYPE`` to Django ``ROOT_URLCONF`` modules.

Worker roles are registered by later slices; this module starts with ``api`` only.
"""

from __future__ import annotations

# service_type -> dotted URLConf module path
SERVICE_TYPE_URLCONFS: dict[str, str] = {
    "api": "ufc_fantasy.public_urls",
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
