"""
    - Utility functions for api file
"""
from django.utils import timezone
from fantasy.models import Draft, Fighters, RoundScore, FightScore, Roster, Team, DraftOrder, DraftPick, LeagueMember, FighterCareerStats
from accounts.models import User
import secrets
import string
import random
from django.db.models import Max, Prefetch

def create_fantasy_for_fighter(fight, fighter,  round_stats):
    """
        -   Creates the fantasy dict for a fighter
    
    :param fight: Django model object from database
    :param fighter: Django model object from database
    :param round_stats: Django series of Django model objects
    """
    fantasy = {'round': {}, 'fight': {}, 'breakdown': {}, 'total': 0.0}
    round_scores = [] # Holds fantasy round scores

    # Iterate through every round in round_stats; get score for round; store in fantasy; append to round_scores
    for round in round_stats:
        round_score = RoundScore.objects.get(round_stats=round)
        fantasy['round'][round.round_number] = round_score
        round_scores.append(round_score)

    # Sum every value in round_scores to store in breakdown
    fantasy['breakdown'] = {
        "points_knockdowns": sum(round.points_knockdowns for round in round_scores),
        "points_sig_str_landed": sum(round.points_sig_str_landed for round in round_scores),
        "points_td_landed": sum(round.points_td_landed for round in round_scores),
        "points_sub_att": sum(round.points_sub_att for round in round_scores),
        "points_ctrl_time": sum(round.points_ctrl_time for round in round_scores),
        "points_reversals": sum(round.points_reversals for round in round_scores),
        "round_total_points": sum(round.round_total_points for round in round_scores),
    }

    fantasy['fight'] = FightScore.objects.get(fighter=fighter, fight=fight)
    fantasy['total'] = fantasy['fight'].fight_total_points

    return fantasy

def has_special_char(text):
    """
        -   Checks if text contains a special character
    
    :param text: String
    """

    return any(not character.isalnum() for character in text)

def generate_join_code(length=8):
    """
        -   Generates random join code
    """
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def weight_to_slot(weight):
    """
    - Maps a fighter's weight (lbs) to a roster slot type

    :param weight: Integer (fighter weight in lbs)
    :return: Roster.SlotType
    """
    if weight <= 115:
        return Roster.SlotType.STRAWWEIGHT
    elif weight <= 125:
        return Roster.SlotType.FLYWEIGHT
    elif weight <= 135:
        return Roster.SlotType.BANTAMWEIGHT
    elif weight <= 145:
        return Roster.SlotType.FEATHERWEIGHT
    elif weight <= 155:
        return Roster.SlotType.LIGHTWEIGHT
    elif weight <= 170:
        return Roster.SlotType.WELTERWEIGHT
    elif weight <= 185:
        return Roster.SlotType.MIDDLEWEIGHT
    elif weight <= 205:
        return Roster.SlotType.LIGHT_HEAVYWEIGHT
    else:
        return Roster.SlotType.HEAVYWEIGHT
    
def generate_draft_order(league, draft):
    """
    Generates a full snake-style draft order for a league by creating
    DraftOrder entries for each team and round.

    :param league: Instance of League model object
    :param draft: Instance of Draft model object
    """
    teams = Team.objects.filter(owner__league=league) # Get teams by following team owner relation and inserting league as the filter
    if teams.count() == 0:
        raise ValueError("Cannot generate draft order: league has no teams")
    if teams.count() < 2:
        raise ValueError("Draft requires at least 2 teams")
    
    teams_list = list(teams) # Converts teams to list
    forward_teams = random.sample(teams_list, k=len(teams_list)) # Shuffles teams randomly
    reversed_teams = forward_teams[::-1] # Reverses picks for odd rounds

    rounds = 10
    pick = 1
    # Snake draft iterate over rounds;
    for i in range(rounds):
        if i%2 == 0:
            for team in forward_teams:
               DraftOrder.objects.create(team=team, draft=draft, pick_num=pick)
               pick += 1
        else:
            for team in reversed_teams:
                DraftOrder.objects.create(team=team, draft=draft, pick_num=pick)
                pick += 1

def execute_draft_pick(team, fighter, slot_type, draft, pick_num):
    """
    Executes a draft pick by recording the pick, assigning the fighter to the roster, and advancing the draft order
    
    :param team: Instance of Team model object
    :param fighter: Instance of Fighter model object
    :param slot_type: Instance of slot_type class object
    :param draft: Instance of Draft model object
    :param pick_num: Integer indicating the pick number of current pick
    """
    Roster.objects.create(team=team, fighter=fighter, slot_type=slot_type)
    DraftPick.objects.create(fighter=fighter, team=team, draft=draft, pick_num=pick_num)
    draft.current_pick += 1
    draft.pick_start_time = timezone.now()
    draft.save()

def autopick_fighter(team, draft):
    """
    Automatically selects a random available fighter for the team during the draft.
    Prioritizes filling weight class slots, falling back to FLEX if all weight classes are filled.
    Returns the randomly chosen fighter's FighterCareerStats object.
    
    :param team: Instance of Team model object
    :param draft: Instance of Draft model object
    :return: tuple of (FighterCareerStats object, Roster.SlotType) for the autopicked fighter and assigned slot; returns (None, None) if no fighters are available or no slots are open
    """
    # Get roster slots already filled for team as a set for O(1) lookups
    filled_slots = get_filled_slots(team)
    
    # Get drafted fighter ids in league
    drafted_fighter_ids = get_drafted_fighter_ids(draft)
    draftable_fighters = get_draftable_fighters(drafted_fighter_ids=drafted_fighter_ids)
    all_weight_slots = {
        Roster.SlotType.STRAWWEIGHT, Roster.SlotType.FLYWEIGHT,
        Roster.SlotType.BANTAMWEIGHT, Roster.SlotType.FEATHERWEIGHT,
        Roster.SlotType.LIGHTWEIGHT, Roster.SlotType.WELTERWEIGHT,
        Roster.SlotType.MIDDLEWEIGHT, Roster.SlotType.LIGHT_HEAVYWEIGHT,
        Roster.SlotType.HEAVYWEIGHT
    }
    open_weight_slots = all_weight_slots - filled_slots
    flex_available = Roster.SlotType.FLEX not in filled_slots

    # Build eligible fighters: those whose weight class slot is open
    weight_class_eligible = []
    for fighter in draftable_fighters:
        if fighter.weight is None:
            continue
        slot_type = weight_to_slot(fighter.weight)
        if slot_type in open_weight_slots:
            weight_class_eligible.append((fighter, slot_type))

    if weight_class_eligible:
        # Prefer filling an open weight class slot directly
        fighter, slot_type = random.choice(weight_class_eligible)
    elif flex_available:
        # All weight class slots are full; fall back to FLEX with any undrafted fighter
        if not draftable_fighters:
            return None, None
        fighter = random.choice(list(draftable_fighters))
        slot_type = Roster.SlotType.FLEX
    else:
        # No slots available at all
        return None, None

    return fighter, slot_type

def is_user_in_league(user, league_id):
    """
    Checks if a user is in a league by checking if they own a team in the league

    :param user: Instance of User model object
    :param league: Instance of League model object
    :return: none; raises PermissionError if user is not in league
    """
    if not LeagueMember.objects.filter(owner=user, league__id=league_id).exists():
        raise PermissionError("User is not in league")

def get_draftable_fighters(drafted_fighter_ids=(), prefetch_fight_scores=False):
    """
    Retrieves a queryset of draftable fighters for a given draft, excluding already drafted fighters and annotating with fantasy points if wanted.

    :param drafted_fighter_ids: Optional set of fighter IDs that have already been drafted
    :param prefetch_fight_scores: Boolean indicating whether to prefetch FightScore objects
    :return: Queryset of FighterCareerStats objects annotated with fantasy points
    """
    draftable_fighters = ()
    if prefetch_fight_scores:
        draftable_fighters = Fighters.objects.filter(is_active=True).exclude(fighter_id__in=drafted_fighter_ids).prefetch_related(
            Prefetch(
                'fightscore_set',
                queryset=FightScore.objects.select_related('fight__event').order_by('-fight__event__date')
            )
        )
    else:
        draftable_fighters = Fighters.objects.filter(is_active=True).exclude(fighter_id__in=drafted_fighter_ids)
    return draftable_fighters

def get_drafted_fighter_ids(draft):
    """
    Retrieves a set of fighter IDs that have already been drafted in the given draft.

    :param draft: Instance of Draft model object
    :return: Set of fighter IDs that have been drafted
    """
    return set(DraftPick.objects.filter(draft=draft).values_list('fighter__fighter_id', flat=True))

def get_filled_slots(team):
    """
    Retrieves a set of slot types that are already filled for a given team.

    :param team: Instance of Team model object
    :return: Set of Roster.SlotType values representing filled slots
    """
    # Get roster slots already filled for team as a set for O(1) lookups
    filled_slots = set(Roster.objects.filter(team=team).values_list('slot_type', flat=True))
    return filled_slots

def get_or_create_user_from_token(request):
    """
    Adds an authenticated user to the database if they do not already exist.
    This function should be called after a user successfully authenticates via Auth0.
    """
    auth0_id = request.oauth_token.get("sub")
    email = request.oauth_token.get("https://ufcfantasy.com/email")
    username = request.oauth_token.get("username")
    
    defaults = {"email": email}
    if username:
        defaults["username"] = username
        defaults["profile_complete"] = True
    else:
        defaults["username"] = ''
        defaults["profile_complete"] = False
    
    user, created = User.objects.get_or_create(
        auth0_id=auth0_id,
        defaults=defaults
    )
    # Ensure email is up to date in case it has changed in Auth0 since last login
    if user.email != email:
        user.email = email
        user.save(update_fields=["email"])
    return user