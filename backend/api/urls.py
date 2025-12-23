from django.urls import path
from . import views

urlpatterns = [
    path('fighters', views.GetFighterProfileViewSet),
    path('events', views.GetEventViewSet),
    path('fights', views.GetFightViewSet),
    path('fighter/<int:id>', views.GetCareerStatsViewSet),
    path('fights/<int:id>', views.GetFighterFightsViewSet),
    path('fights/<int:id>/fantasy-scores/recent', views.GetLastThreeFantasyScoresViewSet),
    path('events/<int:id>', views.GetFightsFromEventViewSet),
]