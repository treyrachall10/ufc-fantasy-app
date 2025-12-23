'''
    Contains views for API
'''
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .serializers import *
from fantasy.models import Fighters, Events, Fights, FighterCareerStats, FightStats

@api_view(['GET'])
def GetFighterProfileViewSet(request):
    fighters = Fighters.objects.all()
    serializer = FighterSerializer(fighters, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def GetEventViewSet(request):
    events = Events.objects.all()
    serializer = EventSerializer(events, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def getFightViewSet(request):
    fights = Fights.objects.all()
    serializer = FightSerializer(fights, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def getCareerStatsViewSet(request, id):
    stats = FighterCareerStats.objects.get(fighter_id=id)
    serializer = FighterCareerStatsSerializer(stats)
    return Response(serializer.data)

@api_view(['GET'])
def getFighterFightsViewSet(request, id):
    fights = Fights.objects.filter(fightstats__fighter_id=id).distinct()
    serializer = FightSerializer(fights, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def getLastThreeFantasyScoresViewSet(request, id):
    fighter = Fighters.objects.get(fighter_id=id)
    fightScore = FightScore.objects.filter(fighter=fighter).order_by('-fight__event__date')[:3]
    serializer = FantasyFightScoreSerializer(fightScore, many=True)
    return Response(serializer.data)