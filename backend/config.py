"""
    -   Holds constant variables for paths and other variables to be used in rest of program
"""
from fantasy.models import Fighters, Events, Fights, FightStats, RoundStats, FighterCareerStats

DATACLEANPATH = 'data/clean'
DATARAWPATH = 'data/raw'

MODEL_MAP = {
    "fighters": {
        "file": "fighters_metadata_clean.csv", 
        "model": Fighters,
        "foreign_keys": False,
        "unique_fields": ["normalized_name"]
    },
    "events": {
        "file": "event_data_clean.csv",
        "model": Events,
        "foreign_keys": False,
        "unique_fields": ["event"]
    },
    "fights": {
        "file": "fight_results_clean.csv",
        "model": Fights,
        "foreign_keys": {
            "event": Events,
            "winner": Fighters
        },
        "unique_fields": ["event", "bout"]
    },
    "fight_stats": {
        "file": "total_fight_stats_clean.csv",
        "model": FightStats,
        "foreign_keys": {
            "fight": Fights,
            "fighter": Fighters
        },
        "unique_fields": ["fight", "fighter"]
    },
    "round_stats": {
        "file": "round_stats_clean.csv",
        "model": RoundStats,
        "foreign_keys": {
            "fight_stats": FightStats
        },
        "unique_fields": ["fight_stats", "round_number"]
    },
    "fighter_career_stats": {
        "file": "career_stats_clean.csv",
        "model": FighterCareerStats,
        "foreign_keys": {
            "fighter": Fighters
        },
        "unique_fields": ["fighter"]
    }
}
