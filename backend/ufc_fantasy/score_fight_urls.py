"""ROOT_URLCONF for ``SERVICE_TYPE=score_fight`` (push only)."""

from django.urls import include, path

urlpatterns = [
    path(
        "pipeline/pubsub/score-fight/",
        include("ufc_data_pipeline.fantasy.score_fight.api.urls"),
    ),
]
