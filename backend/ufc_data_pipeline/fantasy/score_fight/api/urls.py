from django.urls import path

from ufc_data_pipeline.fantasy.score_fight.api.views import score_fight_pubsub_push

urlpatterns = [
    path("", score_fight_pubsub_push, name="score-fight-pubsub-push"),
]
