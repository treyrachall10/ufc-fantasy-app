"""URL routes for fight-stats Pub/Sub push."""

from django.urls import path

from ufc_data_pipeline.fights.fight_stats.api import views

urlpatterns = [
    path("", views.fight_stats_push_view, name="fight_stats_push"),
]
