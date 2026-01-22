'''
    Contains views for API
'''
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import IntegrityError
from django.db import transaction
from django.utils import timezone

from .serializers import *
from fantasy.models import (Fighters, Events, Fights, FighterCareerStats, 
                            FightStats, RoundStats, League, LeagueMember, 
                            Team, Roster, Draft)
from .utils import create_fantasy_for_fighter, generate_join_code, weight_to_slot, generate_draft_order

'''
    -   POST METHODS
'''
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def CreateLeague(request):
    # Attempt to create league 3 times
    for _ in range(3):
        join_key = generate_join_code()
        try:
            league = League.objects.create(
                name=request.data["name"],
                creator=request.user,
                status=League.Status.SETUP,
                end_date=request.data.get("end_date"),
                join_key=join_key,
            )
            # Create draft instance and set to not scheduled
            draft = Draft.objects.create(
                league=league,
                status=Draft.Status.NOT_SCHEDULED,
                scheduled_for=None
            )
            break # Successful league creation
        except IntegrityError: # Code exists in db
            continue
    else:
        return Response(
            {"detail": "Could not generate unique join code"},
            status=409
        )
    return Response(
        {
            "league_id": league.id,
            "join_key": league.join_key,
            "draft_id": draft.id,
            "draft_status": "NOT_SCHEDULED"
        },
        status=201
    )
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def CreateLeagueMember(request):
    try:
        league = League.objects.get(join_key=request.data['joinKey'])
    except League.DoesNotExist:
        return Response(
            {"detail": "Invalid join code"},
            status=404
        )
    # Check if user in league
    if LeagueMember.objects.filter(owner=request.user, league=league).exists():
        return Response(
            {"detail": "You are already a member of this league"},
            status=409
        ) 
    # Create league member with player role
    league_member = LeagueMember.objects.create(
        owner=request.user,
        league=league,
        role=LeagueMember.Role.PLAYER
    )
    return Response(
        { "member_id": league_member.id},
        status=201  
    )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def CreateTeam(request):
    # Checks if league exists
    try:
        league = League.objects.get(id=request.data['id'])
    except League.DoesNotExist:
        return Response({"detail": "League not found"}, status=404)
    # Checks if user is a member of the league
    try:
        league_member = LeagueMember.objects.get(owner=request.user, league=league)
    except LeagueMember.DoesNotExist:
        return Response({"detail": "You are not a member of this league"}, status=403)
    # If user already has team
    if Team.objects.filter(owner=league_member).exists():
       return Response(
            {"detail": "You already have a team in this league"},
            status=409
        )
    # If team name already taken
    if Team.objects.filter(owner__league=league, name=request.data["teamName"]).exists():
        return Response(
            {"detail": "Team name already taken in this league"},
            status=409
        )
    # Create Team
    try:
        team = Team.objects.create(
                            owner=league_member,
                            name=request.data['teamName'],
                            )
    except IntegrityError:
        return Response(
            {"detail": "You already have a team in this league"},
            status=409
        )
    return Response(
        {"team_id": team.id},
        status=201
    )

@transaction.atomic
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def AddRosterSlot(request):
    # Checks if team exists in league and get team plus league
    try:
        team = Team.objects.get(id=request.data['id'], owner=request.user)
        league = team.owner.league
    except Team.DoesNotExist:
        return Response(
            {"detail": "Team does not exist in this league"},
            status=404
        )
    # Checks if fighter exists
    try:
        fighter = Fighters.objects.get(fighter_id=request.data['fighter_id'])
    except Fighters.DoesNotExist:
        return Response(
            {"detail": "Couldn't find fighter in database"},
            status=404
        )
    if Roster.objects.filter(
        fighter=fighter,
        team__league=league
    ).exists():
        return Response(
            {"detail": "Fighter already been drafted"},
            status=409
        )
    slot_type = weight_to_slot(fighter.weight)
    slot_taken = Roster.objects.filter(team=team, slot_type=slot_type).exists()
    flex_taken = Roster.objects.filter(team=team, slot_type=Roster.SlotType.FLEX).exists()
    # If weight class slot is taken and flex is taken reject draft pick
    if slot_taken and flex_taken:
        return Response(
            {
                "detail": "You already have a fighter in this weight class and cannot assign this pick to FLEX"
            },
            status=409
        )
    # If weight class slot is taken and flex is not ask to draft to flex slot
    if slot_taken and not flex_taken:
                return Response(
            {
                "action_required": "confirm_flex",
                "detail": "This weight class is full. FLEX is available. Do you want to assign this fighter to Flex?"
            },
            status=200
        )
    Roster.objects.create(team=team, fighter=fighter, slot_type=slot_type)
    return Response(
        {
            "detail": f"Fighter has been drafted to {slot_type}"
        },
        status=200
    )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def SetDraftStatus(request):
    # Determine if league exist
    try:
        league = League.objects.get(id=request.data['id'])
    except League.DoesNotExist:
        return Response(
            {"detail": "League not found."},
            status=404
        )
    # Allow only league creator to set draft status
    if league.creator == request.user:
        try:
            draft = Draft.objects.get(league=league)
        except Draft.DoesNotExist:
            return Response(
            {"detail": "Draft not found."},
                status=404
            )
        draft_status = draft.status
        if draft_status == Draft.Status.NOT_SCHEDULED:
            try:
                draft.status = Draft.Status.SCHEDULED
                draft.date = timezone.now()
                generate_draft_order(league=league, draft=draft)
                draft.save()
            except ValueError as e:
                return Response(
                    {"detail": str(e)},
                    status=400
                )
        elif draft_status == Draft.Status.SCHEDULED:
            draft.status = Draft.Status.LIVE
        elif draft_status == Draft.Status.LIVE:
            draft.status = Draft.Status.COMPLETED
        else:
            return Response(
                {
                    "detail": "Draft is already completed and cannot be advanced.",   
                },
                status=409
            )
        draft.save()
        return Response(
            {
                "detail": f"Draft set to {draft.status}",
                "draft_status": draft.status
            },
            status=200 
            )
    return Response(
        {
            "detail": "You don't have correct permissions to change draft status",   
        },
        status=403
    )
            

'''
    -   GET METHODS
'''
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
    fights = Fights.objects.filter(fightstats__fighter_id=id).prefetch_related('fightstats_set').distinct() # Prefetch related gets fields related to fights and stores in memory
    serializer = FighterFightSerializer(fights, many=True, context={'fighter_id': id, 'request': request}) # Passing context allows for further logic in serializer
    return Response(serializer.data)

@api_view(['GET'])
def GetLastFiveFantasyScoresViewSet(request, id):
    fighter = Fighters.objects.get(fighter_id=id)
    fightScore = FightScore.objects.filter(fighter=fighter).order_by('-fight__event__date')[:5]
    fightScore = reversed(fightScore)
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