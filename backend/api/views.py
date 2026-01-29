'''
    Contains views for API
'''
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import IntegrityError
from django.db import transaction
from django.utils import timezone
from dateutil.parser import parse

from .serializers import *
from fantasy.models import (Fighters, Events, Fights, FighterCareerStats, 
                            FightStats, RoundStats, League, LeagueMember, 
                            Team, Roster, Draft, DraftPick, DraftOrder)
from .utils import (create_fantasy_for_fighter, generate_join_code, 
                    weight_to_slot, generate_draft_order, execute_draft_pick,
                    get_current_pick
                    )

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
                name=request.data["leagueName"],
                capacity=request.data["teams"],
                creator=request.user,
                status=League.Status.SETUP,
                join_key=join_key,
            )
            # Create draft instance and set to not scheduled
            draft = Draft.objects.create(
                league=league,
                status=Draft.Status.NOT_SCHEDULED,
            )
            member = LeagueMember.objects.create(
                owner = request.user,
                league = league,
                role = LeagueMember.Role.CREATOR
            )
            team = Team.objects.create(
                owner=member,
                name = f"{request.user.username}'s Team"
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
            "member": {
                "id": member.id,
                "role": member.role,
            },
            "team": {
                "id": team.id,
                "name": team.name,
            },
            "draft_status": "NOT_SCHEDULED"
        },
        status=201
    )

@transaction.atomic
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def CreateLeagueMember(request):
    try:
        league = League.objects.get(join_key=request.data['join_key'])
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
    # Create Team
    try:
        team = Team.objects.create(
                            owner=league_member,
                            name=f"{request.user.username}'s Team",
                            )
    except IntegrityError:
        return Response(
            {"detail": "You already have a team in this league"},
            status=409
        )
    draft = Draft.objects.get(league=league)
    return Response(
        {
            "league_id": league.id,
            "join_key": league.join_key,
            "draft_id": draft.id,
            "member": {
                "id": league_member.id,
                "role": league_member.role,
            },
            "team": {
                "id": team.id,
                "name": team.name,
            },
            "draft_status": draft.status,
        },
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
            {"detail": "Team does not exist in this league."},
            status=404
        )
    # Verify draft has been created for league
    try:
        draft = Draft.objects.get(league=league)
    except Draft.DoesNotExist:
        return Response(
            {"detail": "Draft hasn't been created for this league."},
            status=500
        )
    # Verify draft in drafting state
    if draft.Status != Draft.Status.IN_PROGRESS:
        return Response(
            {"detail": "Draft has not yet started."},
            status=409,
        )
    current_pick = get_current_pick(draft=draft)
    current_pick_team = current_pick.team
    # Check if users turn to draft
    if team != current_pick_team:
        return Response(
            {"detail": "It's not your turn to draft."},
            status=409
        )
    # Checks if fighter exists
    try:
        fighter = Fighters.objects.get(fighter_id=request.data['fighter_id'])
    except Fighters.DoesNotExist:
        return Response(
            {"detail": "Couldn't find fighter in database."},
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
    pick_num = current_pick.pick_num
    execute_draft_pick(team=team, 
                       fighter=fighter, 
                       slot_type=slot_type, 
                       draft=draft, 
                       pick_num=pick_num,
                       current_pick=current_pick
                       )
    return Response(
        {
            "detail": f"Fighter has been drafted to {slot_type}"
        },
        status=200
    )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def DraftFlexSlot(request):
    # Checks if team exists in league and get team plus league
    try:
        team = Team.objects.get(id=request.data['id'], owner=request.user)
        league = team.owner.league
    except Team.DoesNotExist:
        return Response(
            {"detail": "Team does not exist in this league."},
            status=404
        )
    # Verify draft has been created for league
    try:
        draft = Draft.objects.get(league=league)
    except Draft.DoesNotExist:
        return Response(
            {"detail": "Draft hasn't been created for this league."},
            status=500
        )
    # Verify draft in drafting state
    if draft.Status != Draft.Status.IN_PROGRESS:
        return Response(
            {"detail": "Draft has not yet started."},
            status=409,
        )
    current_pick = get_current_pick(draft=draft)
    current_pick_team = current_pick.team
    # Check if users turn to draft
    if team != current_pick_team:
        return Response(
            {"detail": "It's not your turn to draft."},
            status=409
        )
    # Checks if fighter exists
    try:
        fighter = Fighters.objects.get(fighter_id=request.data['fighter_id'])
    except Fighters.DoesNotExist:
        return Response(
            {"detail": "Couldn't find fighter in database."},
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
    flex_taken = Roster.objects.filter(team=team, slot_type=Roster.SlotType.FLEX).exists()
    if not flex_taken and Roster.objects.filter(team=team, slot_type=slot_type).exists():
        pick_num = current_pick.pick_num
        execute_draft_pick(fighter=fighter, 
                           team=team, 
                           slot_type=Roster.SlotType.FLEX, 
                           draft=draft,
                           pick_num=pick_num,
                           current_pick=current_pick
                           )
        return Response(
            {'detail': f'{fighter.full_name} drafted to FLEX'},
            status=200
        )
    else:
        return Response(
            {"detail": "Flex slot is no longer available."},
            status=409
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
            # Only let user set draft with full league
            if league.leaguemember_set.count() != league.capacity:
                return Response(
                    {"detail": "League is not full"},
                    status=409
                )
            try:
                draft.status = Draft.Status.PENDING
                draft.date = request.data['date']
                generate_draft_order(league=league, draft=draft)
                draft.save()
            except ValueError as e:
                return Response(
                    {"detail": str(e)},
                    status=400
                )
        elif draft_status == Draft.Status.SCHEDULED:
            if timezone.now() >= draft.date:
                draft.status = Draft.Status.LIVE
            else:
                return Response(
                    {
                        'detail': 'Draft has not reached its scheduled start time yet.'
                    },
                    status=409
                )
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

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def SetDraftDate(request, league_id):
    # Determine if league exist
    try:
        league = League.objects.get(id=league_id)
    except League.DoesNotExist:
        return Response(
            {"detail": "League not found."},
            status=404
        )
    # Ensure date is passed
    if not request.data.get("draft_date"):
        return Response(
            {"detail": "draft_date is required"},
            status=400
        )
    draft_date = request.data["draft_date"]
    if parse(draft_date) <= timezone.now():
        return Response(
            {"detail": "Draft must be in the future"}, 
            status=400
        )
    # Allow only league creator to set draft status
    if league.creator != request.user:
        return Response(
            {
                "detail": "You don't have correct permissions to change draft status",   
            },
            status=403
        )
    try:
        draft = Draft.objects.get(league=league)
    except Draft.DoesNotExist:
        return Response(
        {"detail": "Draft not found."},
            status=404
        )
    draft_status = draft.status
    if draft_status != Draft.Status.NOT_SCHEDULED:
        return Response(
            {"detail": "Draft has already been scheduled"},
            status=409
        )
    # Only let user set draft with full league
    if league.leaguemember_set.count() != league.capacity:
        return Response(
            {"detail": "League is not full"},
            status=409
        )
    try:
        draft.status = Draft.Status.PENDING
        draft.draft_date = request.data['draft_date']
        generate_draft_order(league=league, draft=draft)
        draft.save()
    except ValueError as e:
        return Response(
            {"detail": str(e)},
            status=400
        )
    return Response(
        {
            "detail": f"Draft set to {draft.status}",
            "draft_status": draft.status
        },
        status=200 
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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def GetUserLeaguesAndTeams(request):
    league_member_instance_set = LeagueMember.objects.filter(owner=request.user).select_related('league').prefetch_related('team_set')
    serializer = UserLeaguesAndTeamsListSerializer(league_member_instance_set, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def GetLeagueData(request, league_id):
    if not LeagueMember.objects.filter(owner=request.user, league_id=league_id).exists():
        return Response(
            {"detail": "You are not apart of this league"},
            status=403
        )
    league = League.objects.get(id=league_id)
    teams = Team.objects.filter(owner__league_id=league_id)
    draft = Draft.objects.get(league=league)
    return Response({
        "league": LeagueSerializer(league).data,
        "teams": TeamSerializer(teams, many=True).data,
        "draft": DraftSerializer(draft).data
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def GetTeamListData(request, team_id):
    try:
        team = Team.objects.get(id=team_id)
    except Team.DoesNotExist:
        return Response(
            {"detail": "Team does not exist." },
            status=404
        )
    # League may not have drafted. Let continue if haven't
    roster_rows = Roster.objects.filter(team=team)
    if not roster_rows.exists():
        return Response(
            {
                "team": {
                    "id": team.id,
                    "name": team.name,
                    "owner": team.owner.owner.username
                },
                "roster": [
                    { "slot": "STRAWWEIGHT", "fighter": None },
                    { "slot": "FLYWEIGHT", "fighter": None },
                    { "slot": "BANTAMWEIGHT", "fighter": None },
                    { "slot": "FEATHERWEIGHT", "fighter": None },
                    { "slot": "LIGHTWEIGHT", "fighter": None },
                    { "slot": "WELTERWEIGHT", "fighter": None },
                    { "slot": "MIDDLEWEIGHT", "fighter": None },
                    { "slot": "LIGHT_HEAVYWEIGHT", "fighter": None },
                    { "slot": "HEAVYWEIGHT", "fighter": None },
                    { "slot": "FLEX", "fighter": None }
                ]
            },
            status=200
        )
    # Creates clean dict, fighter is None if empty, fetches incomplete teams
    slot_to_fighter = {
        row.slot_type: row.fighter
        for row in roster_rows
    }
    response_roster = []
    for slot in Roster.SlotType.values:
        fighter = slot_to_fighter.get(slot)
        response_roster.append(
        {
            "slot": slot,
            "fighter": (TeamListFighterSerializer(fighter) if fighter is not None else None) # Returns none if empty 
        })
    # Iterate over slots in roster rows
    return Response(
        {
            "team": {
                "id": team.id,
                "name": team.name,
                "owner": team.owner.owner.username
            },
            "roster": response_roster
        },
        status=200
    )