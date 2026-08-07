"""URL routes for fighter profile Pub/Sub push."""

from django.urls import path

from .views import fighter_profile_pubsub_push

urlpatterns = [
    path("", fighter_profile_pubsub_push, name="fighter-profile-pubsub-push"),
]
