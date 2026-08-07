from django.urls import path

from ufc_data_pipeline.fighters.career_stats.api.views import career_stats_pubsub_push

urlpatterns = [
    path("", career_stats_pubsub_push, name="career-stats-pubsub-push"),
]
