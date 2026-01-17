from django.urls import path, include
from . import views

urlpatterns = [
    path('fighters', views.GetFighterProfileViewSet),
    path('events', views.GetEventViewSet),
    path('fights', views.GetFightViewSet),
    path('fighter/<int:id>', views.GetCareerStatsViewSet),
    path('fights/<int:id>', views.GetFighterFightsViewSet),
    path('fights/<int:id>/fantasy-scores/recent', views.GetLastThreeFantasyScoresViewSet),
    path('events/<int:id>', views.GetFightsFromEventViewSet),
    path('fight/<int:id>', views.GetHeadToHeadStatsViewSet),
    path('auth/signup/', views.createUser),
    path('dj-rest-auth/', include('dj_rest_auth.urls')),
    path('dj-rest-auth/registration/', include('dj_rest_auth.registration.urls')),
]