from urllib.parse import urljoin, urlsplit, urlunsplit

from django.db import migrations, models


def _normalize_url(value):
    raw = (value or "").strip()
    if not raw:
        return ""
    absolute = urljoin("http://ufcstats.com/", raw)
    parts = urlsplit(absolute)
    path = parts.path if parts.path == "/" else parts.path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, "", ""))


def normalize_and_validate_replay_keys(apps, schema_editor):
    Fights = apps.get_model("fantasy", "Fights")
    FightStats = apps.get_model("fantasy", "FightStats")
    RoundStats = apps.get_model("fantasy", "RoundStats")

    normalized_keys = {}
    updates = []
    for fight in Fights.objects.exclude(url__isnull=True).exclude(url="").iterator():
        normalized = _normalize_url(fight.url)
        key = (fight.event_id, normalized)
        if key in normalized_keys:
            raise RuntimeError(
                "Cannot add fight replay identity constraint; normalized collision "
                f"event_id={fight.event_id} url={normalized} "
                f"fight_ids={[normalized_keys[key], fight.fight_id]}"
            )
        normalized_keys[key] = fight.fight_id
        if fight.url != normalized:
            fight.url = normalized
            updates.append(fight)
    if updates:
        Fights.objects.bulk_update(updates, ["url"])

    fight_stats_duplicates = (
        FightStats.objects.values("fight_id", "fighter_id")
        .annotate(row_count=models.Count("id"))
        .filter(row_count__gt=1)
    )
    if fight_stats_duplicates.exists():
        raise RuntimeError(
            "Cannot add FightStats replay identity constraint; duplicates exist: "
            f"{list(fight_stats_duplicates[:20])}"
        )

    round_stats_duplicates = (
        RoundStats.objects.values("fight_stats_id", "round_number")
        .annotate(row_count=models.Count("id"))
        .filter(row_count__gt=1)
    )
    if round_stats_duplicates.exists():
        raise RuntimeError(
            "Cannot add RoundStats replay identity constraint; duplicates exist: "
            f"{list(round_stats_duplicates[:20])}"
        )


class Migration(migrations.Migration):
    dependencies = [
        ("fantasy", "0038_fights_fight_status"),
    ]

    operations = [
        migrations.RunPython(
            normalize_and_validate_replay_keys,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AddConstraint(
            model_name="fights",
            constraint=models.UniqueConstraint(
                fields=("event", "url"),
                condition=models.Q(url__isnull=False) & ~models.Q(url=""),
                name="unique_fight_event_url",
            ),
        ),
        migrations.AddConstraint(
            model_name="fightstats",
            constraint=models.UniqueConstraint(
                fields=("fight", "fighter"),
                name="unique_fight_stats_fight_fighter",
            ),
        ),
        migrations.AddConstraint(
            model_name="roundstats",
            constraint=models.UniqueConstraint(
                fields=("fight_stats", "round_number"),
                name="unique_round_stats_fight_round",
            ),
        ),
    ]
