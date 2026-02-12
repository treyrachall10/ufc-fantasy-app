"""
    - Utility functions for api file
"""
from django.utils import timezone
from fantasy.models import Draft, RoundScore, FightScore, Roster, Team, DraftOrder, DraftPick, LeagueMember, FighterCareerStats
import secrets
import string
import random

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
    :return: Instance of FighterCareerStats model object (randomly chosen available fighter)
    """
    # Get roster slots already filled for team as a set for O(1) lookups
    filled_slots = set(Roster.objects.filter(team=team).values_list('slot_type', flat=True))
    
    # Get drafted fighter ids in league
    drafted_fighter_ids = set(DraftPick.objects.filter(draft=draft).values_list('fighter__fighter_id', flat=True))
    
    # If FLEX is available, all undrafted fighters are eligible
    if Roster.SlotType.FLEX not in filled_slots:
        available_fighters = list(FighterCareerStats.objects.exclude(fighter_id__in=drafted_fighter_ids))
        if not available_fighters:
            return None
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
            return None
        
        fighter = random.choice(eligible_fighters)
    
    return fighter.fighter

def is_user_in_league(user, league_id):
    """
    Checks if a user is in a league by checking if they own a team in the league

    :param user: Instance of User model object
    :param league: Instance of League model object
    :return: none; raises PermissionError if user is not in league
    """
    if not LeagueMember.objects.filter(owner=user, league__id=league_id).exists():
        raise PermissionError("User is not in league")