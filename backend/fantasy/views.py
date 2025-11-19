from django.shortcuts import render
from django.http import JsonResponse
from fantasy.models import *

def get_fighter(request, fighter_id):
    """
        -   Contains logic for the fighter stats view
    """
    try:
        fighter = Fighters.objects.get(fighter_id=fighter_id)
    except:
        return JsonResponse({"error": "Fighter not found"}, status=404)
    
    try:
        fighter_career_stats = FighterCareerStats.objects.get(fighter=fighter)
    except:
        return JsonResponse({"error": "Career stats not available"}, status=404)

    fighter_data = {
        # --- Fighter basic info ---
        "fighter_id": fighter.fighter_id,
        "first_name": fighter.first_name,
        "last_name": fighter.last_name,
        "full_name": fighter.full_name,
        "nick_name": fighter.nick_name,
        "stance": fighter.stance,
        "weight": fighter.weight,
        "height": fighter.height,
        "reach": fighter.reach,
        "dob": fighter.dob,

        # --- Career Stats ---
        "total_fights": fighter_career_stats.total_fights,
        "wins": fighter_career_stats.wins,
        "losses": fighter_career_stats.losses,
        "draws": fighter_career_stats.draws,
        "ko_tko": fighter_career_stats.ko_tko,
        "tko_doctor_stoppages": fighter_career_stats.tko_doctor_stoppages,
        "submissions": fighter_career_stats.submissions,
        "unanimous_decisions": fighter_career_stats.unanimous_decisions,
        "split_decisions": fighter_career_stats.split_decisions,
        "majority_decisions": fighter_career_stats.majority_decisions,
        "dq": fighter_career_stats.dq,

        "sig_str_landed": fighter_career_stats.sig_str_landed,
        "sig_str_attempted": fighter_career_stats.sig_str_attempted,
        "total_str_landed": fighter_career_stats.total_str_landed,
        "total_str_attempted": fighter_career_stats.total_str_attempted,

        "td_landed": fighter_career_stats.td_landed,
        "td_attempted": fighter_career_stats.td_attempted,
        "sub_att": fighter_career_stats.sub_att,
        "ctrl_time": fighter_career_stats.ctrl_time,
        "reversals": fighter_career_stats.reversals,

        "head_str_landed": fighter_career_stats.head_str_landed,
        "head_str_attempted": fighter_career_stats.head_str_attempted,
        "body_str_landed": fighter_career_stats.body_str_landed,
        "body_str_attempted": fighter_career_stats.body_str_attempted,
        "leg_str_landed": fighter_career_stats.leg_str_landed,
        "leg_str_attempted": fighter_career_stats.leg_str_attempted,

        "distance_str_landed": fighter_career_stats.distance_str_landed,
        "distance_str_attempted": fighter_career_stats.distance_str_attempted,
        "clinch_str_landed": fighter_career_stats.clinch_str_landed,
        "clinch_str_attempted": fighter_career_stats.clinch_str_attempted,
        "ground_str_landed": fighter_career_stats.ground_str_landed,
        "ground_str_attempted": fighter_career_stats.ground_str_attempted,
    }
    return JsonResponse(fighter_data)