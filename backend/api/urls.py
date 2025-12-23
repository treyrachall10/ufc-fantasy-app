from django.urls import path
from . import views

urlpatterns = [
    path('fighters', views.GetFighterProfileViewSet),
    path('events', views.GetEventViewSet),
    path('fights', views.getFightViewSet),
    path('fighter/<int:id>', views.getCareerStatsViewSet),
    path('fights/<int:id>', views.getFighterFightsViewSet),
    path('fights/<int:id>/fantasy-scores/recent', views.getLastThreeFantasyScoresViewSet)
]