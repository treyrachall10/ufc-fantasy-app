'''
    Contains views for API
'''
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework import generics, filters
from django_filters.rest_framework import DjangoFilterBackend
from django.db import IntegrityError
from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.core.exceptions import ValidationError
from django.conf import settings
from django.db.models import Q
from rest_framework_api_key.permissions import HasAPIKey

from dateutil.parser import parse
from dateutil.parser import ParserError
from django.shortcuts import get_object_or_404
from zoneinfo import ZoneInfo
from datetime import timezone as datetime_timezone
from pathlib import Path

from services.supabase import supabase

from api.pagination_classes import FighterListPagination, UserLeaguesPagination

from .serializers import (
    DraftOrderSerializer,
    DraftPickHistorySerializer,
    DraftSerializer,
    EventSerializer,
    FantasyFightScoreSerializer,
    FightSerializer,
    FighterCareerStatsSerializer,
    FighterFightSerializer,
    FighterSerializer,
    HeadToHeadStatsSerializer,
    LeagueSerializer,
    TeamListFantasyScoreSerializer,
    TeamListFighterSerializer,
    TeamSerializer,
    UserLeaguesAndTeamsListSerializer,
    FighterImageCandidateSerializer,
    FighterProfileUpdateSerializer,
    FightResultMetadataUpdateSerializer,
    FightStatsTotalsUpdateSerializer,
)
from fantasy.models import (Fighters, Events, Fights, FighterCareerStats, 
                            FightStats, RoundStats, FightScore, League, LeagueMember, 
                            Team, Roster, Draft, DraftPick, DraftOrder)
from .utils import (create_fantasy_for_fighter, generate_join_code, get_draftable_fighters, get_or_create_user_from_token, 
                    weight_to_slot, generate_draft_order, execute_draft_pick,
                    is_user_in_league, autopick_fighter, get_drafted_fighter_ids, check_draft_completed,
                    get_league_standings, validate_image, upload_file
                    )

from accounts.models import User

from .permissions import IsAthleteImageService, IsUploaderService, IsPipelineService

from shared.utils import normalize_name

from authlib.integrations.django_oauth2 import ResourceProtector
from .auth0_validator import Auth0JWTBearerTokenValidator
require_auth = ResourceProtector()

validator = Auth0JWTBearerTokenValidator(
    "dev-kxp1v6beff35mbat.us.auth0.com",
    "https://ufc-fantasy-api"     # API Identifier
)

require_auth.register_token_validator(validator)

# Canonical timezone used for draft-day business rules across all users.
AMERICA_TIMEZONE = ZoneInfo("America/New_York")

'''
    -   POST METHODS
'''
@api_view(['POST'])
@require_auth(None)
def CreateLeague(request):
    user = get_or_create_user_from_token(request=request)
    # Attempt to create league 3 times
    for _ in range(3):
        join_key = generate_join_code()
        try:
            league = League.objects.create(
                name=request.data["leagueName"],
                capacity=request.data["teams"],
                creator=user,
                status=League.Status.SETUP,
                join_key=join_key,
            )
            # Create draft instance and set to not scheduled
            draft = Draft.objects.create(
                league=league,
                status=Draft.Status.NOT_SCHEDULED,
            )
            member = LeagueMember.objects.create(
                owner = user,
                league = league,
                role = LeagueMember.Role.CREATOR
            )
            team = Team.objects.create(
                owner=member,
                name = f"{user.username}'s Team"
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
@require_auth(None)
def CreateLeagueMember(request):
    league = get_object_or_404(League, join_key=request.data['join_key'])
    # Check if user in league
    user = get_or_create_user_from_token(request=request)
    if LeagueMember.objects.filter(owner=user, league=league).exists():
        return Response(
            {"detail": "You are already a member of this league"},
            status=409
        )
    # Create league member with player role
    league_member = LeagueMember.objects.create(
        owner=user,
        league=league,
        role=LeagueMember.Role.PLAYER
    )
    # Create Team
    try:
        team = Team.objects.create(
                            owner=league_member,
                            name=f"{user.username}'s Team",
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

@api_view(['POST'])
@require_auth(None)
def SetUsername(request):
    try:
        user = get_or_create_user_from_token(request=request)
    except AttributeError:
        return Response({"detail": "Invalid OAuth token"}, status=400)

    username = request.data.get("username", "")
    username = username.strip()

    if not username:
        return Response({"detail": "Username is required"}, status=400)

    if any(char.isspace() for char in username):
        return Response({"detail": "Username cannot contain spaces"}, status=400)
    # Check if username already exists for another user
    if User.objects.filter(username=username).exclude(id=user.id).exists():
        return Response({"detail": "This username already exists"}, status=409)

    user.username = username
    user.profile_complete = True
    user.save(update_fields=["username", "profile_complete"])

    return Response(
        {
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
            }
        },
        status=200
    )

@transaction.atomic
@api_view(['POST'])
@require_auth(None)
def AddRosterSlot(request, draft_id):
    user = get_or_create_user_from_token(request=request)
    # Verify draft has been created for league
    draft = get_object_or_404(Draft, id=draft_id)
    check_draft_completed(draft)
    # Gets League and team
    league = draft.league
    team = get_object_or_404(Team, id = request.data['team_id'], owner__owner__id=user.id)
    # Verify draft in drafting state
    if draft.status != Draft.Status.IN_PROGRESS:
        return Response(
            {"detail": "Draft has not yet started.",
             "code": "draft_not_live"
             },
            status=409,
        )
    current_pick = draft.current_pick
    team_to_pick = DraftOrder.objects.get(draft=draft, pick_num=current_pick).team
    # Check if users turn to draft
    if team != team_to_pick:
        return Response(
            {"detail": "It's not your turn to draft.",
             "code": "not_your_turn"
             },
            status=409
        )
    # Checks if fighter exists
    fighter = get_object_or_404(Fighters, fighter_id=request.data['fighter_id'])
    # Check if fighter already drafted in league
    if Roster.objects.filter(
        fighter=fighter,
        team__owner__league=league
    ).exists():
        return Response(
            {"detail": "Fighter already been drafted",
                "code": "fighter_already_drafted"
            },
            status=409
        )
    slot_type = weight_to_slot(fighter.weight)
    slot_taken = Roster.objects.filter(team=team, slot_type=slot_type).exists()
    flex_taken = Roster.objects.filter(team=team, slot_type=Roster.SlotType.FLEX).exists()
    # If weight class slot is taken and flex is taken reject draft pick
    if slot_taken and flex_taken:
        return Response(
            {
                "detail": "You already have a fighter in this weight class and cannot assign this pick to FLEX.",
                "code": "weight_class_and_flex_full"
            },
            status=409
        )
    # If weight class slot is taken and flex is not ask to draft to flex slot
    if slot_taken and not flex_taken:
                return Response(
            {
                "action_required": "confirm_flex",
                "detail": "This weight class is full. FLEX is available. Do you want to assign this fighter to Flex?",
                "code": "confirm_flex",
                "fighter_id": fighter.fighter_id
            },
            status=200
        )
    execute_draft_pick(team=team, 
                       fighter=fighter, 
                       slot_type=slot_type, 
                       draft=draft, 
                       pick_num=current_pick,
                       )
    # Check if draft is completed
    if draft.current_pick > DraftOrder.objects.filter(draft=draft).count():
        draft.status = Draft.Status.COMPLETED
        draft.save()
        return Response(
            {
                "detail": f"Fighter has been drafted to {slot_type}. Draft is now completed.",
                "code": "draft_completed",
                "draft_status": draft.status,
                "user_team_id": team.id,
            },
            status=200
        )
    return Response(
        {
            "detail": f"Fighter has been drafted to {slot_type}",
            "current_pick": draft.current_pick,
            "pick_start_time": draft.pick_start_time,
            "code": "pick_successful",
        },
        status=200
    )

@api_view(['POST'])
@require_auth(None)
def DraftFlexSlot(request, draft_id):
    user = get_or_create_user_from_token(request=request)
    # Verify draft has been created for league
    draft = get_object_or_404(Draft, id=draft_id)
    check_draft_completed(draft)
    # Get League and team
    league = draft.league
    team = get_object_or_404(Team, id=request.data['team_id'], owner__owner__id=user.id)
    # Verify draft in drafting state
    if draft.status != Draft.Status.IN_PROGRESS:
        return Response(
            {"detail": "Draft has not yet started.",
             "code": "draft_not_live"
             },
            status=409,
        )
    current_pick = draft.current_pick
    team_to_pick = DraftOrder.objects.get(draft=draft, pick_num=current_pick).team
    # Check if users turn to draft
    if team != team_to_pick:
        return Response(
            {"detail": "It's not your turn to draft.",
             "code": "not_your_turn"
             },
            status=409
        )
    # Checks if fighter exists
    fighter = get_object_or_404(Fighters, fighter_id=request.data['fighter_id'])
    # Check if fighter already drafted in league
    if Roster.objects.filter(
        fighter=fighter,
        team__owner__league=league
    ).exists():
        return Response(
            {"detail": "Fighter already been drafted",
             "code": "fighter_already_drafted"
            },
            status=409
        )
    slot_type = weight_to_slot(fighter.weight)
    flex_taken = Roster.objects.filter(team=team, slot_type=Roster.SlotType.FLEX).exists()
    # Verify flex slot is available and weight class slot is taken
    if not flex_taken and Roster.objects.filter(team=team, slot_type=slot_type).exists():
        execute_draft_pick(fighter=fighter, 
                           team=team, 
                           slot_type=Roster.SlotType.FLEX, 
                           draft=draft,
                           pick_num=current_pick
                           )
        # Check if draft is completed
        if draft.current_pick > DraftOrder.objects.filter(draft=draft).count():
            draft.status = Draft.Status.COMPLETED
            draft.save()
            return Response(
                {
                    "detail": "Fighter has been drafted to FLEX. Draft is now completed.",
                    "code": "draft_completed",
                    "draft_status": draft.status,
                    "user_team_id": team.id,
                },
                status=200
            )
        return Response(
            {
                "detail": "Fighter has been drafted to FLEX",
                "current_pick": draft.current_pick,
                "pick_start_time": draft.pick_start_time,
                "code": "pick_successful",
            },
            status=200
        )
    else:
        return Response(
            {"detail": "Flex slot is no longer available.",
             "code": "flex_not_available"
             },
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
@require_auth(None)
def SetDraftDate(request, league_id):
    user = get_or_create_user_from_token(request=request)
    # Determine if league exist
    league = get_object_or_404(League, id=league_id)
    # Ensure date is passed
    if not request.data.get("draft_date"):
        return Response(
            {"detail": "draft_date is required"},
            status=400
        )
    draft_date = request.data["draft_date"]
    # Validate date format and timezone info
    try:
        parsed_draft_date = parse(draft_date) # Parse date string to datetime object
    except (TypeError, ValueError, ParserError):
        return Response(
            {"detail": "draft_date must be a valid ISO datetime string"},
            status=400
        )
    # Check if datetime is timezone aware
    if timezone.is_naive(parsed_draft_date):
        return Response(
            {"detail": "draft_date must include timezone information"},
            status=400
        )

    # Normalize to UTC for storage and comparisons, then evaluate day-of-week in America.
    draft_date_utc = parsed_draft_date.astimezone(datetime_timezone.utc)
    if draft_date_utc <= timezone.now():
        return Response(
            {"detail": "Draft must be in the future"}, 
            status=400
        )
    # Check if draft date falls on Saturday in America, Which is fight day
    if draft_date_utc.astimezone(AMERICA_TIMEZONE).weekday() == 5:
        return Response(
            {"detail": "Drafts cannot be scheduled on fight days"},
            status=400
        )
    # Allow only league creator to set draft status
    if league.creator != user:
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
        draft.draft_date = draft_date_utc # Store draft date in UTC
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
class GetFighterProfileViewSet(generics.ListAPIView):
    '''
        API view to get fighter profiles with pagination
    '''
    queryset = FighterCareerStats.objects.all()
    serializer_class = FighterSerializer
    pagination_class = FighterListPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['fighter__nick_name', 'fighter__full_name', 'fighter__normalized_name']

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

@method_decorator(require_auth(None), name='dispatch')
class GetUserLeaguesAndTeams(generics.ListAPIView):
    serializer_class = UserLeaguesAndTeamsListSerializer
    pagination_class = UserLeaguesPagination

    @staticmethod
    def apply_league_standings(league_member_instance_set):
        """
        Adds dynamic standing attributes to teams in memory for each league.
        """
        for league_member in league_member_instance_set:
            league_teams = []
            # Get all teams in league
            for member in league_member.league.leaguemember_set.all():
                league_teams.extend(member.team_set.all())
            ranked_teams = get_league_standings(league_teams) # Ranks team by points
            # Creates a mapping for each team object using its id to its standing in the league
            standing_by_team_id = {team.id: team.standing for team in ranked_teams}

            # Applies standing to a user's team in memory for serializer to access
            user_team = getattr(league_member, 'user_team', None)
            if user_team is not None:
                user_team.standing = standing_by_team_id.get(user_team.id)

    def get_queryset(self):
        user = get_or_create_user_from_token(request=self.request)
        # Query league_member_instance_set -> league -> leaguemember_set -> team
        return (
            LeagueMember.objects.filter(owner=user)
            .select_related('league')
            .prefetch_related(
                'team_set',
                Prefetch(
                    'league__leaguemember_set',
                    queryset=LeagueMember.objects.select_related('owner').prefetch_related('team_set'),
                ),
            )
        )

    def list(self, request, *args, **kwargs):
        league_member_instance_set = self.get_queryset()
        user_league_members = list(league_member_instance_set)
        for league_member in user_league_members:
            league_member.user_team = league_member.team_set.all()[0] if league_member.team_set.exists() else None

        self.apply_league_standings(user_league_members)

        page = self.paginate_queryset(user_league_members)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(user_league_members, many=True)
        return Response(serializer.data)

@api_view(['GET'])
@require_auth(None)
def GetLeagueData(request, league_id):
    user = get_or_create_user_from_token(request=request)
    is_user_in_league(user, league_id)
    league = get_object_or_404(League, id=league_id)
    teams = Team.objects.filter(owner__league_id=league_id)
    draft = Draft.objects.get(league=league)
    return Response({
        "league": LeagueSerializer(league).data,
        "teams": TeamSerializer(teams, many=True).data,
        "draft": DraftSerializer(draft).data
    })

@api_view(['GET'])
@require_auth(None)
def GetTeamListData(request, team_id):
    """
    Gets team list data for a given team, including fighter info and fantasy scores.  
    Returns complete roster with None for empty slots and fantasy scores if available.

    :param team_id: Integer id for team
    :return: Response with team info, roster with fighter data or None, and fantasy scores
    """
    team = get_object_or_404(Team.objects.prefetch_related('owner__league__draft_set') , id=team_id)
    draft = team.owner.league.draft_set.first() # Get draft for league; One league should only have one draft
    draftStartTime = draft.draft_date.date() if draft.draft_date else None # Get draft start time for fantasy score calculations
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
    if team.img_url:
        img_url = supabase.storage.from_(settings.SUPABASE_TEAM_IMAGE_BUCKET).get_public_url(team.img_url)
    else:
        img_url = None
    if not roster_rows.exists():
        return Response(
            {
                "team": {
                    "id": team.id,
                    "name": team.name,
                    "owner": team.owner.owner.username,
                    "score": team.score,
                    "img_path": img_url
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
            average_points = (sum(score_values) / len(score_values)) if score_values else None
            points_since_draft = [score.fight_total_points for score in all_scores if score.fight and score.fight.event and draftStartTime and score.fight.event.date >= draftStartTime and score.fight_total_points is not None]
            total_points_since_draft = sum(points_since_draft) if points_since_draft else 0
            if latest_fantasy is not None:
                fantasy_payload = {
                    "last_fight_points": latest_fantasy.fight_total_points,
                    "average_points": average_points,
                    "total_points_since_draft": total_points_since_draft
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
                "owner": team.owner.owner.username,
                "score": team.score,
                "img_url": img_url
            },
            "roster": response_roster
        },
        status=200
    )

@api_view(['POST'])
@require_auth(None)
def ChangeTeamName(request, team_id):
    user = get_or_create_user_from_token(request=request)
    team = get_object_or_404(
        Team.objects.select_related('owner__league'),
        id=team_id,
        owner__owner=user,
    )

    new_name = request.data.get('name', '').strip()
    if not new_name:
        return Response(
            {"detail": "Team name is required"},
            status=400,
        )

    league = team.owner.league
    if Team.objects.filter(owner__league=league, name=new_name).exclude(id=team.id).exists():
        return Response(
            {"detail": "Team name already taken"},
            status=409,
        )

    team.name = new_name
    team.save(update_fields=['name'])

    return Response(
        {
            "detail": "Team name updated successfully",
            "team": {
                "id": team.id,
                "name": team.name,
            },
        },
        status=200,
    )

@api_view(['GET'])
@require_auth(None)
def GetDraftState(request, draft_id):
    draft=get_object_or_404(Draft, id=draft_id)
    league = draft.league
    user = get_or_create_user_from_token(request=request)
    is_user_in_league(user, league.id) # Determine if user in league; raises error if not
    team = Team.objects.get(owner__owner=user, owner__league=league)
    team_id = team.id
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
                "detail": "Draft is completed.",
                "user_team_id": team_id,
            },
            status=200
        )
    # Draft is live return draft status and current pick info 
    if draft.status == Draft.Status.IN_PROGRESS:
        draft_orders = list(
            DraftOrder.objects.filter(draft=draft)
            .select_related('team')
            .order_by('pick_num')
        )
        total_draft_orders = len(draft_orders)

        if draft.current_pick > total_draft_orders:
            draft.status = Draft.Status.COMPLETED
            draft.save(update_fields=['status'])
            return Response(
                {
                    "draft_status": draft.status,
                    "detail": "Draft is completed.",
                    "user_team_id": team_id,
                },
                status=200
            )

        draft_order = draft_orders[draft.current_pick - 1]
        team_to_pick = draft_order.team
        # Check time remaining for pick and if time has expired, auto pick for team to pick and advance draft
        time_elapsed = timezone.now() - draft.pick_start_time
        if time_elapsed >= timezone.timedelta(seconds=60): # 60 second pick timer
            fighter, slot_type = autopick_fighter(team=team_to_pick, draft=draft)
            if fighter and slot_type is not None:
                execute_draft_pick(team=team_to_pick, fighter=fighter, draft=draft, pick_num=draft.current_pick, slot_type=slot_type)
                if draft.current_pick > total_draft_orders:
                    draft.status = Draft.Status.COMPLETED
                    draft.save(update_fields=['status'])
        return Response(
            {
                "draft_status": draft.status,
                "current_pick": draft.current_pick,
                "pick_start_time": draft.pick_start_time,
                "team_to_pick_id": team_to_pick.id,
                "user_team_id": team_id,
            },
            status=200
        )
    
@api_view(['GET'])
@require_auth(None)
def GetDraftOrder(request, draft_id):
    user = get_or_create_user_from_token(request=request)
    draft = get_object_or_404(Draft, id=draft_id)
    league = draft.league
    is_user_in_league(user, league.id) # Determine if user in league; raises error if not
    check_draft_completed(draft)
    # Get draft order for league
    draft_order = DraftOrder.objects.filter(draft=draft).select_related('team').order_by('pick_num')
    serializer = DraftOrderSerializer(draft_order, many=True)
    return Response(
            serializer.data,
            status=200
        )

@method_decorator(require_auth(None), name='dispatch')
class GetDraftableFighters(generics.ListAPIView):
    pagination_class = FighterListPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['weight']
    search_fields = ['full_name', 'normalized_name']

    def get_queryset(self):
        user = get_or_create_user_from_token(request=self.request)
        draft = get_object_or_404(Draft, id=self.kwargs['draft_id'])
        league = draft.league
        is_user_in_league(user, league.id)
        check_draft_completed(draft)

        drafted_fighter_ids = get_drafted_fighter_ids(draft=draft)
        return get_draftable_fighters(
            drafted_fighter_ids=drafted_fighter_ids,
            prefetch_fight_scores=True,
        )

    def list(self, request, *args, **kwargs):
        draftable_fighters = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(draftable_fighters)
        fighters = page if page is not None else draftable_fighters

        serialized_data = []
        for fighter in fighters:
            fight_scores = fighter.fightscore_set.all()

            if fight_scores.exists():
                average_points = sum(fs.fight_total_points for fs in fight_scores) / len(fight_scores)
                last_points = fight_scores.first().fight_total_points
            else:
                average_points = 0
                last_points = 0

            slot_type = weight_to_slot(fighter.weight) if fighter.weight is not None else None

            fighter_data = TeamListFighterSerializer(fighter).data
            fighter_data['slot_type'] = slot_type

            serialized_data.append(
                {
                    'fighter': fighter_data,
                    'fantasy': TeamListFantasyScoreSerializer(
                        {
                            'last_fight_points': last_points,
                            'average_points': average_points,
                        }
                    ).data,
                }
            )

        if page is not None:
            return self.get_paginated_response(serialized_data)

        return Response(serialized_data, status=200)

@api_view(['GET'])
@require_auth(None)
def GetDraftPickHistory(request, draft_id):
    user = get_or_create_user_from_token(request=request)
    draft = get_object_or_404(Draft, id=draft_id)
    check_draft_completed(draft)
    league = draft.league
    is_user_in_league(user, league.id) # Determine if user in league; raises error if not
    draft_picks = DraftPick.objects.filter(draft=draft).select_related('fighter', 'team').order_by('-pick_num')
    serializer = DraftPickHistorySerializer(draft_picks, many=True)
    return Response(
        serializer.data,
        status=200
    )

@api_view(['GET'])
@require_auth(None)
def GetCurrentUserViewSet(request):
    try:
        auth0_id = request.oauth_token.get('sub')
        email = request.oauth_token.get("https://ufcfantasy.com/email")
        username = request.oauth_token.get("https://ufcfantasy.com/username")
    except AttributeError:
        return Response({"error": "Invalid OAuth token"}, status=400)
    user, created = User.objects.get_or_create(email=email, defaults={'email': email, 'auth0_id': auth0_id, 'username': username})
    # If user was created with username mark profile complete, otherwise keep profile incomplete
    if user.username is not None and user.username != '':
        user.profile_complete = True
        user.save(update_fields=['profile_complete'])
    return Response({
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
        },
        "profile_complete": user.profile_complete
    })

@api_view(['POST'])
@require_auth(None)
def PreviewLeagueByJoinKey(request):
    '''
        Endpoint to preview league details before joining.
    '''
    user = get_or_create_user_from_token(request=request)
    league = get_object_or_404(
        League.objects.select_related('creator').prefetch_related('leaguemember_set'),
        join_key=request.data['join_key']
    )

    if len(league.leaguemember_set.all()) >= league.capacity:
        return Response(
            {"detail": "League is full"},
            status=409
        )

    return Response(
        {
            "league_name": league.name,
            "creator_username": league.creator.username,
        },
        status=200
    )

@method_decorator(require_auth(None), name='dispatch')
class SetTeamImage(generics.UpdateAPIView):
    def patch(self, request, team_id):
        # Resolve the authenticated user from the OAuth token; fail fast on bad token payload.
        try:
            user = get_or_create_user_from_token(request=request)
        except AttributeError:
            return Response({"detail": "Invalid OAuth token"}, status=400)

        # Allow team id from route or request body for flexible callers.
        team_id = team_id or request.data.get("id")
        if not team_id:
            return Response({"detail": "Team id is required"}, status=400)

        # Restrict lookup to the caller's own team within the target league.
        team = get_object_or_404(
            Team,
            owner__owner=user,
            id=team_id,
        )

        # Require an uploaded image file under the expected multipart key.
        image_file = request.FILES.get("image")
        if image_file is None:
            return Response({"detail": "image file is required"}, status=400)

        # Validate extension, max size, and actual image bytes before persisting path metadata.
        try:
            validate_image(image_file=image_file)
        except ValidationError as exc:
            # Pull structured validation code to map known failures to clear API responses.
            error_code = exc.code
            if getattr(exc, "error_list", None):
                error_code = exc.error_list[0].code

            # Return an explicit payload-too-large status for file size violations.
            if error_code == "too_large":
                return Response(
                    {"detail": "Image file is too large. Max size is 2MB."},
                    status=413,
                )

            # Group unsupported extensions and unreadable image content into one invalid-image response.
            return Response(
                {"detail": "Image format is invalid or file is not a valid image."},
                status=400,
            )

        # Build the canonical storage path with the uploaded filename and persist it on the team record.
        filename = Path(image_file.name).name or "image.png"
        image_path = f"{team.id}/{filename}"
        # Upload to Supabase Storage first; only persist DB path when upload succeeds.
        try:
            upload_file(
                uploaded_file=image_file,
                bucket_name=settings.SUPABASE_TEAM_IMAGE_BUCKET,
                path=image_path,
            )
        except Exception:
            return Response(
                {"detail": "Failed to upload team image."},
                status=502,
            )

        team.img_url = image_path
        team.save(update_fields=["img_url"])

        # Return the updated team id and resolved image path for client follow-up actions.
        return Response(
            {
                "team_id": team.id,
                "image_path": image_path,
                "detail": "Team image updated successfully.",
            },
            status=200,
        )

class GetFighterImageCandidates(generics.ListAPIView):
    '''
        API view to get fighters without images for athlete image service to consume and update with images.
    '''
    permission_classes = [HasAPIKey, IsAthleteImageService]
    serializer_class = FighterImageCandidateSerializer

    def get_queryset(self):
        return Fighters.objects.filter(Q(img_url__isnull=True) | Q(img_url=""))
    
class AddFighterImageURL(generics.UpdateAPIView):
    '''
        API view to allow athlete image service to update fighter record with image url after processing.
    '''
    permission_classes = [HasAPIKey, IsUploaderService]

    def patch(self, request, fighter_id):
        '''
            Expects img_url in request data, updates fighter record with image url for frontend to consume.
        '''
        fighter = get_object_or_404(Fighters, fighter_id=fighter_id)
        image_url = request.data.get("img_url") # Expecting full URL from athlete image service

        if not image_url:
            return Response({"detail": "img_url is required"}, status=400)
        
        fighter.img_url = image_url
        fighter.save(update_fields=["img_url"])

        return Response(
            {
                "detail": "Fighter image URL updated successfully.",
            },
            status=200,
        )


class SetFighterProfile(generics.UpdateAPIView):
    '''
        API view to allow the UFC data pipeline to update fighter profile metadata.
    '''
    permission_classes = [HasAPIKey, IsPipelineService]
    serializer_class = FighterProfileUpdateSerializer

    def patch(self, request, fighter_id):
        '''
            Expects fighter profile fields in request data and updates the fighter record.
        '''
        fighter = get_object_or_404(Fighters, fighter_id=fighter_id)
        serializer = self.serializer_class(fighter, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "detail": "Fighter profile updated successfully.",
            },
            status=200,
        )


class SetFightResultMetadata(generics.GenericAPIView):
    """
    API view to allow the UFC data pipeline to update fight result metadata.
    """

    permission_classes = [HasAPIKey, IsPipelineService]
    serializer_class = FightResultMetadataUpdateSerializer

    def patch(self, request, fight_id: int):
        """
        Expects fight result fields in request data and updates the fight record.
        """
        fight = get_object_or_404(Fights, fight_id=fight_id)
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)

        winner_name = data.pop("winner_name", None)
        data.pop("fighter_a_name", None)
        data.pop("fighter_b_name", None)

        for field, value in data.items():
            setattr(fight, field, value)

        if winner_name:
            normalized = normalize_name(winner_name)
            winner = Fighters.objects.filter(normalized_name=normalized).first()
            if winner is None:
                return Response(
                    {"detail": f"Fighter not found for winner_name: {winner_name}"},
                    status=400,
                )
            fight.winner = winner

        fight.save()

        return Response(
            {"detail": "Fight result metadata updated successfully."},
            status=200,
        )


class SetFightStatsTotals(generics.GenericAPIView):
    """
    API view to allow the UFC data pipeline to upsert fight-total FightStats rows.
    """

    permission_classes = [HasAPIKey, IsPipelineService]
    serializer_class = FightStatsTotalsUpdateSerializer

    def patch(self, request, fight_id: int):
        """
        Expects two fighter stat bundles and upserts FightStats by fight + fighter.
        """
        fight = get_object_or_404(Fights, fight_id=fight_id)
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        resolved: list[tuple] = []
        for fighter_payload in serializer.validated_data["fighters"]:
            fighter_name = fighter_payload["fighter_name"]
            normalized = normalize_name(fighter_name)
            fighter = Fighters.objects.filter(normalized_name=normalized).first()
            if fighter is None:
                return Response(
                    {"detail": f"Fighter not found for fighter_name: {fighter_name}"},
                    status=400,
                )
            resolved.append((fighter, fighter_payload))

        updated_ids: list[int] = []
        with transaction.atomic():
            for fighter, fighter_payload in resolved:
                defaults = {
                    key: value
                    for key, value in fighter_payload.items()
                    if key != "fighter_name"
                }
                fight_stats, _created = FightStats.objects.update_or_create(
                    fight=fight,
                    fighter=fighter,
                    defaults=defaults,
                )
                updated_ids.append(fight_stats.pk)

        return Response(
            {
                "detail": "Fight stats totals upserted successfully.",
                "fight_stats_ids": updated_ids,
            },
            status=200,
        )