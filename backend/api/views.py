'''
    Contains views for API
'''
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.contrib.auth.models import User

from .serializers import *
from fantasy.models import Fighters, Events, Fights, FighterCareerStats, FightStats, RoundStats, RoundScore
from .utils import create_fantasy_for_fighter, has_special_char

# Post Methods
@api_view(['POST'])
def createUser(request):
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')

    # Check if user provided a username
    if not username:
        return Response(
            {"error": "Username is required"},
            status=400
        )
    # Check if user provided available username
    if User.objects.filter(username=username).exists():
        return Response(
            {"error": "Username already taken"},
            status=400
        )

    # Check if user provided an email
    if not email:
        return Response(
            {"error": "Email is required"},
            status=400
        )
    # Check if user provided email that hasn't been used
    if User.objects.filter(email=email).exists():
        return Response(
            {"error": "Email already taken"},
            status=400
        )
    
    # Password check
    if not password:
        return Response(
            {"error": "Password is requred"},
            status=400
        )
    # Password length check
    if len(password) < 8:
        return Response(
            {"error": "Password must be at least 8 characters"},
            status=400
        )
    # Password special character check
    if not has_special_char(text=password):
        return Response(
            {"error": "Password must contain at least 1 special character"},
            status=400
        )
    
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password
    )

    return Response({"message": "User created"})

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