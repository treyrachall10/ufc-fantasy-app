from django.urls import path
from . import views

urlpatterns = [
    path('fighters', views.GetFighterProfileViewSet),
    path('events', views.GetEventViewSet),
    path('fights', views.getFightViewSet)
]