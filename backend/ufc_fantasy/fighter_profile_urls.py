"""ROOT_URLCONF for ``SERVICE_TYPE=fighter_profile`` (push only)."""

from django.urls import include, path

urlpatterns = [
    path(
        "pipeline/pubsub/fighter-profile/",
        include("ufc_data_pipeline.fighters.fighter_profile.api.urls"),
    ),
]
