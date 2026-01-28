from django.urls import path, include
from . import views
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('fighters', views.GetFighterProfileViewSet),
    path('events', views.GetEventViewSet),
    path('fights', views.GetFightViewSet),
    path('fighter/<int:id>', views.GetCareerStatsViewSet),
    path('fights/<int:id>', views.GetFighterFightsViewSet),
    path('fights/<int:id>/fantasy-scores/recent', views.GetLastFiveFantasyScoresViewSet),
    path('events/<int:id>', views.GetFightsFromEventViewSet),
    path('fight/<int:id>', views.GetHeadToHeadStatsViewSet),
    path('dj-rest-auth/', include('dj_rest_auth.urls')),
    path('dj-rest-auth/registration/', include('dj_rest_auth.registration.urls')),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('create-league', views.CreateLeague),
    path('leagues', views.GetUserLeaguesAndTeams),
    path('league/<int:league_id>', views.GetLeagueData),
    path('league/<league_id>/draft/schedule', views.SetDraftDate),
    path('league/join', views.CreateLeagueMember),
    path('team/<int:team_id>', views.GetTeamListData),
]