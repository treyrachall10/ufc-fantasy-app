'''
    Contains views for API
'''
from random import random
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import IntegrityError
from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone
from dateutil.parser import parse
from django.db.models import Max
from django.shortcuts import get_object_or_404

from .serializers import *
from fantasy.models import (Fighters, Events, Fights, FighterCareerStats, 
                            FightStats, RoundStats, FightScore, League, LeagueMember, 
                            Team, Roster, Draft, DraftPick, DraftOrder)
from .utils import (create_fantasy_for_fighter, generate_join_code, 
                    weight_to_slot, generate_draft_order, execute_draft_pick,
                    is_user_in_league
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
    league = get_object_or_404(League, join_key=request.data['join_key'])
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
def AddRosterSlot(request, draft_id):
    # Verify draft has been created for league
    draft = get_object_or_404(Draft, id=draft_id)
    # Gets League and team
    league = draft.league
    team = get_object_or_404(Team, id = request.data['team_id'], owner=request.user)
    # Verify draft in drafting state
    if draft.status != Draft.Status.IN_PROGRESS:
        return Response(
            {"detail": "Draft has not yet started."},
            status=409,
        )
    current_pick = draft.current_pick
    team_to_pick = DraftOrder.objects.get(draft=draft, pick_num=current_pick).team
    # Check if users turn to draft
    if team != team_to_pick:
        return Response(
            {"detail": "It's not your turn to draft."},
            status=409
        )
    # Check if autopick is true, draft random fighter from available fighters and for a slot not filled
    if request.data.get('autopick', False):
        # Get roster slots already filled for team as a set for O(1) lookups
        filled_slots = set(Roster.objects.filter(team=team).values_list('slot_type', flat=True))
        
        # Get drafted fighter ids in league
        drafted_fighter_ids = set(DraftPick.objects.filter(draft=draft).values_list('fighter__fighter_id', flat=True))
        
        # If FLEX is available, all undrafted fighters are eligible
        if Roster.SlotType.FLEX not in filled_slots:
            available_fighters = list(FighterCareerStats.objects.exclude(fighter_id__in=drafted_fighter_ids))
            if not available_fighters:
                return Response(
                    {"detail": "No available fighters to draft."},
                    status=409
                )
            fighter = random.choice(available_fighters)
        else:
            # FLEX is taken, only fighters matching open weight class slots are eligible
            all_slots = {
                Roster.SlotType.STRAWWEIGHT, Roster.SlotType.FLYWEIGHT, 
                Roster.SlotType.BANTAMWEIGHT, Roster.SlotType.FEATHERWEIGHT,
                Roster.SlotType.LIGHTWEIGHT, Roster.SlotType.WELTERWEIGHT,
                Roster.SlotType.MIDDLEWEIGHT, Roster.SlotType.LIGHT_HEAVYWEIGHT,
                Roster.SlotType.HEAVYWEIGHT
            }
            open_slots = all_slots - filled_slots
            
            # Filter to fighters whose weight class slot is open
            eligible_fighters = []
            for fighter in FighterCareerStats.objects.exclude(fighter_id__in=drafted_fighter_ids):
                slot_type = weight_to_slot(fighter.weight)
                if slot_type in open_slots:
                    eligible_fighters.append(fighter)
            
            if not eligible_fighters:
                return Response(
                    {"detail": "No available fighters to draft."},
                    status=409
                )
            
            fighter = random.choice(eligible_fighters)
    else:
        # Checks if fighter exists
        fighter = get_object_or_404(Fighters, fighter_id=request.data['fighter_id'])
        # Check if fighter already drafted in league
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
    execute_draft_pick(team=team, 
                       fighter=fighter, 
                       slot_type=slot_type, 
                       draft=draft, 
                       pick_num=current_pick,
                       )
    if draft.current_pick >= DraftOrder.objects.filter(draft=draft).count():
        draft.status = Draft.Status.COMPLETED
        draft.save()
        return Response(
            {
                "detail": f"Fighter has been drafted to {slot_type}. Draft is now completed.",
                "draft_status": draft.status
            },
            status=200
        )
    return Response(
        {
            "detail": f"Fighter has been drafted to {slot_type}",
            "current_pick": draft.current_pick,
            "pick_start_time": draft.pick_start_time
        },
        status=200
    )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def DraftFlexSlot(request):
    # Checks if team exists in league and get team plus league
    team = get_object_or_404(Team, id=request.data['id'], owner=request.user)
    league = team.owner.league
    # Verify draft has been created for league
    draft = get_object_or_404(Draft, league=league)
    # Verify draft in drafting state
    if draft.Status != Draft.Status.IN_PROGRESS:
        return Response(
            {"detail": "Draft has not yet started."},
            status=409,
        )
    current_pick = draft.current_pick
    current_pick_team = DraftOrder.objects.get(draft=draft, pick_num=current_pick).team
    # Check if users turn to draft
    if team != current_pick_team:
        return Response(
            {"detail": "It's not your turn to draft."},
            status=409
        )
    # Checks if fighter exists
    fighter = get_object_or_404(Fighters, fighter_id=request.data['fighter_id'])
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
    league = get_object_or_404(League, id=request.data['id'])
    # Allow only league creator to set draft status
    if league.creator == request.user:
        draft = Draft.objects.get(league=league)
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
    league = get_object_or_404(League, id=league_id)
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
    draft = get_object_or_404(Draft, league=league)
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

@transaction.atomic
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def DraftFighter(request, draft_id):
    pass

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
    stats = get_object_or_404(FighterCareerStats, fighter_id=id)
    serializer = FighterCareerStatsSerializer(stats)
    return Response(serializer.data)

@api_view(['GET'])
def GetFighterFightsViewSet(request, id):
    fights = Fights.objects.filter(fightstats__fighter_id=id).prefetch_related('fightstats_set').distinct().order_by('-event__date') # Prefetch related gets fields related to fights and stores in memory
    serializer = FighterFightSerializer(fights, many=True, context={'fighter_id': id, 'request': request}) # Passing context allows for further logic in serializer
    return Response(serializer.data)

@api_view(['GET'])
def GetLastFiveFantasyScoresViewSet(request, id):
    fighter = get_object_or_404(Fighters, fighter_id=id)
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

    fight = get_object_or_404(Fights, fight_id=id)
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
    is_user_in_league(request.user, league_id)
    league = get_object_or_404(League, id=league_id)
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
    team = get_object_or_404(Team, id=team_id)
    # Load roster rows with fighters and their fight scores; uses select/prefetch related for efficiency
    roster_rows = (
        Roster.objects.filter(team=team)
        .select_related('fighter')
        .prefetch_related(
            Prefetch(
                'fighter__fightscore_set',
                queryset=(
                    FightScore.objects.select_related('fight__event')
                    .order_by('-fight__event__date')
                ),
                to_attr='all_fight_scores'
            )
        )
    )
    if not roster_rows.exists():
        return Response(
            {
                "team": {
                    "id": team.id,
                    "name": team.name,
                    "owner": team.owner.owner.username
                },
                "roster": [
                    { "slot": "SW", "fighter": None, "fantasy": None}, 
                    { "slot": "FLW", "fighter": None, "fantasy": None},
                    { "slot": "BW", "fighter": None, "fantasy": None },
                    { "slot": "FW", "fighter": None, "fantasy": None },
                    { "slot": "LW", "fighter": None, "fantasy": None },
                    { "slot": "WW", "fighter": None, "fantasy": None },
                    { "slot": "MW", "fighter": None, "fantasy": None },
                    { "slot": "LHW", "fighter": None, "fantasy": None },
                    { "slot": "HW", "fighter": None, "fantasy": None },
                    { "slot": "FLEX", "fighter": None, "fantasy": None }
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
    # Iterate over all possible slots, build fighter data or None
    for slot in Roster.SlotType.values:
        fighter = slot_to_fighter.get(slot)
        fantasy_payload = None
        # Build fantasy payload if fighter has fight scores
        if fighter is not None and getattr(fighter, 'all_fight_scores', None):
            all_scores = fighter.all_fight_scores
            latest_fantasy = all_scores[0] if all_scores else None
            score_values = [score.fight_total_points for score in all_scores if score.fight_total_points is not None]
            average_fight_points = (sum(score_values) / len(score_values)) if score_values else None
            if latest_fantasy is not None:
                fantasy_payload = {
                    "last_fight_points": latest_fantasy.fight_total_points,
                    "average_fight_points": average_fight_points
                }
        response_roster.append(
        {
            "slot": slot,
            "fighter": TeamListFighterSerializer(fighter).data if fighter is not None else None, # Returns none if empty
            "fantasy": TeamListFantasyScoreSerializer(fantasy_payload).data if fantasy_payload is not None else None # Returns none if no fights yet
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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def GetDraftState(request, draft_id):
    draft=get_object_or_404(Draft, id=draft_id)
    league = draft.league
    is_user_in_league(request.user, league.id) # Determine if user in league; raises error if not
    # check if draft status is pending and if date has passed set to live
    if draft.status == Draft.Status.PENDING and timezone.now() >= draft.draft_date:
        draft.status = Draft.Status.IN_PROGRESS
        draft.current_pick = 1
        draft.pick_start_time = timezone.now()
        draft.save()
     # if draft is pending and date not passed return pending
    if draft.status == Draft.Status.PENDING:
        return Response(
            {
                "draft_status": draft.status,
                "detail": "Draft is scheduled but has not yet started."
            },
            status=200
        )
    # if draft is completed return completed
    if draft.status == Draft.Status.COMPLETED:
        return Response(
            {
                "draft_status": draft.status,
                "detail": "Draft is completed."
            },
            status=200
        )
    # Draft is live return draft status and current pick info 
    if draft.status == Draft.Status.IN_PROGRESS:
        team_to_pick = DraftOrder.objects.get(draft=draft, pick_num=draft.current_pick).team
        return Response(
            {
                "draft_status": draft.status,
                "current_pick": draft.current_pick,
                "pick_start_time": draft.pick_start_time,
                "team_to_pick_id": team_to_pick.id,
            },
            status=200
        )
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def GetDraftOrder(request, draft_id):
    draft = get_object_or_404(Draft, id=draft_id)
    league = draft.league
    is_user_in_league(request.user, league.id) # Determine if user in league; raises error if not
    # Get draft order for league
    draft_order = DraftOrder.objects.filter(league=league).select_related('team').order_by('pick_num')
    serializer = DraftOrderSerializer(draft_order, many=True)
    return Response(
            serializer.data,
            status=200
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def GetDraftableFighters(request, draft_id):
    cutoff = timezone.now() - timezone.timedelta(days=365*2) # 2 year cutoff for fighter activity, can adjust as needed
    
    draft = get_object_or_404(Draft, id=draft_id)
    league = draft.league
    is_user_in_league(request.user, league.id) # Determine if user in league; raises error if not
    # use DraftPick to get drafted fighters in league using draft as lookup
    drafted_fighter_ids = DraftPick.objects.filter(draft=draft).values_list('fighter__fighter_id', flat=True)
    
    # get fighters that haven't been drafted, have fought in last 2 yeard, and prefetch fightscores for fantasy calculations
    draftable_fighters = FighterCareerStats.objects.annotate(last_fight=Max('fighter__fightscore__fight__event__date')).exclude(
        fighter_id__in=drafted_fighter_ids).exclude(last_fight__lt=cutoff).prefetch_related(
        Prefetch(
            'fighter__fightscore_set',
            queryset=FightScore.objects.select_related('fight__event').order_by('-fight__event__date')
        )
    )
    # Build list of objects with fighter info and fantasy info
    draftable_fighters_list = []
    for fighter_stats in draftable_fighters:
        fight_scores = fighter_stats.fighter.fightscore_set.all()
        
        # Calculate average and last fight points
        if fight_scores.exists():
            average_points = sum(fs.fight_total_points for fs in fight_scores) / len(fight_scores)
            last_points = fight_scores.first().fight_total_points  # First because already ordered by date desc
        else:
            average_points = 0
            last_points = 0
        
        # Convert fighter weight to roster slot type
        slot_type = weight_to_slot(fighter_stats.fighter.weight) if fighter_stats.fighter.weight is not None else None
        
        # Create object with fighter, fantasy data, and slot type
        fighter_obj = fighter_stats.fighter
        draftable_fighters_list.append({
            'fighter': fighter_obj,
            'fantasy': {
                    'last_fight_points': last_points,
                    'average_points': average_points,
                },
            'slot_type': slot_type,
        })
    
    # Serialize each with fighter, fantasy score, and slot type
    serialized_data = []
    for item in draftable_fighters_list:
        fighter_serializer = TeamListFighterSerializer(item['fighter'])
        fantasy_serializer = TeamListFantasyScoreSerializer(item['fantasy'])
        
        # Add slot_type to fighter serialized data since it's part of fighter identity
        fighter_data = fighter_serializer.data
        fighter_data['slot_type'] = item['slot_type']
        
        serialized_data.append({
            'fighter': fighter_data,
            'fantasy': fantasy_serializer.data,
        })
    
    return Response(
        serialized_data,
        status=200
    )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def GetDraftPickHistory(request, draft_id):
    draft = get_object_or_404(Draft, id=draft_id)
    league = draft.league
    is_user_in_league(request.user, league.id) # Determine if user in league; raises error if not
    draft_picks = DraftPick.objects.filter(draft=draft).select_related('fighter', 'team').order_by('pick_num')
    serializer = DraftPickHistorySerializer(draft_picks, many=True)
    return Response(
        serializer.data,
        status=200
    )