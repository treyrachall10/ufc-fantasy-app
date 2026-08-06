"""ROOT_URLCONF for ``SERVICE_TYPE=fight_stats`` (push only)."""

from django.urls import include, path

urlpatterns = [
    path(
        "pipeline/pubsub/fight-stats/",
        include("ufc_data_pipeline.fights.fight_stats.api.urls"),
    ),
]
