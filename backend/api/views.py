'''
    Contains views for API
'''
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .serializers import *
from fantasy.models import Fighters, Events, Fights, FighterCareerStats, FightStats, RoundStats, RoundScore
from .utils import create_fantasy_for_fighter, has_special_char

# Post Methods


# Get Methods
@api_view(['GET'])
def GetFighterProfileViewSet(request):
    fighters = FighterCareerStats.objects.all()
    serializer = FighterSerializer(fighters, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def GetEventViewSet(request):
    events = Events.objects.all()
    serializer = EventSerializer(events, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def GetFightViewSet(request):
    fights = Fights.objects.all()
    serializer = FightSerializer(fights, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def GetCareerStatsViewSet(request, id):
    stats = FighterCareerStats.objects.get(fighter_id=id)
    serializer = FighterCareerStatsSerializer(stats)
    return Response(serializer.data)

@api_view(['GET'])
def GetFighterFightsViewSet(request, id):
    fights = Fights.objects.filter(fightstats__fighter_id=id).distinct()
    serializer = FightSerializer(fights, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def GetLastThreeFantasyScoresViewSet(request, id):
    fighter = Fighters.objects.get(fighter_id=id)
    fightScore = FightScore.objects.filter(fighter=fighter).order_by('fight__event__date')[:3]
    serializer = FantasyFightScoreSerializer(fightScore, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def GetFightsFromEventViewSet(request, id):
    fights = Fights.objects.filter(event__event_id=id)
    serializer = FightSerializer(fights, many=True)
    return Response(serializer.data)


from django.forms.models import model_to_dict

@api_view(['GET'])
def GetHeadToHeadStatsViewSet(request, id):    

    fight = Fights.objects.get(fight_id=id)
    fightStats = FightStats.objects.filter(fight=fight)
    fighterAFightStats, fighterBFightStats = [stat for stat in fightStats]

    fighterA = fighterAFightStats.fighter
    fighterB = fighterBFightStats.fighter

    fighterACareerStats = FighterCareerStats.objects.get(fighter=fighterA)
    fighterBCareerStats = FighterCareerStats.objects.get(fighter=fighterB)

    fighterARoundStats = RoundStats.objects.filter(fight_stats=fighterAFightStats)
    fighterBRoundStats = RoundStats.objects.filter(fight_stats=fighterBFightStats)
    
    fighterAFantasy = create_fantasy_for_fighter(fight=fight, fighter=fighterA, round_stats=fighterARoundStats)
    fighterBFantasy = create_fantasy_for_fighter(fight=fight, fighter=fighterB, round_stats=fighterBRoundStats)

    event = fight.event
    object = {
        'fight': fight,
        'fighterAFightStats': fighterAFightStats,
        'fighterBFightStats': fighterBFightStats,
        'fighterA': fighterACareerStats,
        'fighterB': fighterBCareerStats,
        'event': event,
        'fighterAFantasy': fighterAFantasy,
        'fighterBFantasy': fighterBFantasy
    }
    serializer = HeadToHeadStatsSerializer(object, many=False)
    return Response(serializer.data)