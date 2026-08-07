"""ROOT_URLCONF for ``SERVICE_TYPE=career_stats`` (push only)."""

from django.urls import include, path

urlpatterns = [
    path(
        "pipeline/pubsub/career-stats/",
        include("ufc_data_pipeline.fighters.career_stats.api.urls"),
    ),
]
