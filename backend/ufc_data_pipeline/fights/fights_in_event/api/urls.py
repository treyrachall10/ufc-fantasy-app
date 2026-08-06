from django.urls import path

from . import views

urlpatterns = [
    path("", views.pubsub_push),
]
