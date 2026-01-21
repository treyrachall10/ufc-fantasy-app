"""
    - Utility functions for api file
"""

from fantasy.models import RoundScore, FightScore, Roster
import secrets
import string

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