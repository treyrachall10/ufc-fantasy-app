"""ROOT_URLCONF for ``SERVICE_TYPE=fights_in_event`` (push only)."""

from django.urls import include, path

urlpatterns = [
    path(
        "pipeline/pubsub/fights-in-event/",
        include("ufc_data_pipeline.fights.fights_in_event.api.urls"),
    ),
]
