"""
    -   Responsible for populating and updating database through connecting headers with model fields
"""
import csv
from django.db import models
from fantasy.models import Fighters, Events, Fights, FightStats, RoundStats, RoundScore, FightScore
from config import DATACLEANPATH, MODEL_MAP
from scripts.utils import normalize_name
from scripts.scoring import score_knockdowns, score_td_landed, score_sub_att, score_ctrl_time, score_win, score_round_finish, score_time


def resolve_lookup_value(field_name, value):
    """
        -   Normalizes lookup values so key types match DB field types
    """
    if field_name in {"dob", "date"} and isinstance(value, str) and value:
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return value
    return value

def populate_simple_tables():
    """
        -   Populates tables with no foreign key dependencies
        -   RETURNS: Nothing; it just builds each table
    """
    simple_model_configs = []
    for model_key in MODEL_MAP:
        if MODEL_MAP[model_key].get("foreign_keys") is False:
            simple_model_configs.append((model_key, MODEL_MAP[model_key]))

    for model_key, model_config in simple_model_configs:
        print(f"Populating {model_key} table...")
        model_class = model_config["model"]
        csv_file = model_config["file"]
        unique_fields = model_config["unique_fields"]
        attributes = model_config.get("attributes", model_config.get("attribute", []))

        create_list = [] # Holds new model objects to bulk create
        update_list = [] # Holds existing model objects with updated data to bulk update

        # Get existing records from database and create a lookup dict based on unique fields for quick access during population
        existing_records = model_class.objects.all()
        records_by_lookup = {
            tuple(
                resolve_lookup_value(field_name, getattr(existing_record, field_name))
                for field_name in unique_fields
            ): existing_record
            for existing_record in existing_records
        }

        with open(f"{DATACLEANPATH}/{csv_file}", "r") as file:
            reader = csv.DictReader(file)

            for row in reader:
                row_data = {}

                for attribute in attributes:
                    value = row.get(attribute)

                    if value is None or value == "":
                        row_data[attribute] = None
                        continue

                    cleaned_value = value.strip()
                    # Convert numeric fields to integers, handle boolean for is_active, and keep strings as they are
                    if attribute in {"height", "weight", "reach"}:
                        row_data[attribute] = int(float(cleaned_value))
                    elif attribute == "is_active":
                        row_data[attribute] = cleaned_value.lower() == "true"
                    else:
                        row_data[attribute] = cleaned_value

                lookup_key = tuple(
                    resolve_lookup_value(field_name, row_data.get(field_name))
                    for field_name in unique_fields
                )
                existing_obj = records_by_lookup.get(lookup_key)
                # If no existing record is found, create a new model object and add it to the create list; otherwise, check for updates and add to update list if there are changes
                if existing_obj is None:
                    new_obj = model_class(**row_data)
                    create_list.append(new_obj)
                    records_by_lookup[lookup_key] = new_obj
                    continue

                has_changes = False
                for attribute in attributes:
                    new_value = row_data.get(attribute)
                    if getattr(existing_obj, attribute) != new_value:
                        setattr(existing_obj, attribute, new_value)
                        has_changes = True

                if has_changes:
                    update_list.append(existing_obj)

        if create_list:
            model_class.objects.bulk_create(
                objs=create_list,
                update_fields=[field for field in attributes if field not in unique_fields],
            )

        if update_list:
            model_class.objects.bulk_update(objs=update_list, fields=attributes)

        print(f"Created {len(create_list)} new {model_key} rows.")
        print(f"Updated {len(update_list)} existing {model_key} rows.")

def populate_round_score():
    """
        -   Iterates through rows in RoundStats model and calculates fantasy scores
        -   RETURNS: Nothing; populates the RoundScore table 
    """
    entry_counter = 0
    round_stats = RoundStats.objects.filter(roundscore__isnull=True) # Filters every row that needs scoring
    objs = [] # Holds round score objects to bulk create
    # Iterate through round_stats; score round; append to objs list
    for row in round_stats:
        # Skip row if stats are incompleted
        if (row.fight_stats is None
            or row.fight_stats.fighter is None
            or row.fight_stats.fight is None
        ):
            continue
        # Score points for each action
        obj = RoundScore(
            round_stats=row,
            points_knockdowns=score_knockdowns(row.kd),
            points_sig_str_landed=row.sig_str_landed,
            points_td_landed=score_td_landed(row.td_landed),
            points_sub_att=score_sub_att(row.sub_att),
            points_ctrl_time=score_ctrl_time(row.ctrl_time),
            points_reversals=row.reversals,
            round_total_points=(
                score_knockdowns(row.kd)
                + row.sig_str_landed
                + score_td_landed(row.td_landed)
                + score_sub_att(row.sub_att)
                + score_ctrl_time(row.ctrl_time)
                + row.reversals
            )
        )
        objs.append(obj)
        entry_counter += 1

    RoundScore.objects.bulk_create(objs=objs)
    print(f"Created {entry_counter} new RoundScore rows.")

def populate_fight_score():
    """
        -   Populates the FightScore table
        -   RETURNS: Nothing; populates the FightScore table 
    """
    entry_counter = 0
    fights = Fights.objects.filter(fightscore__isnull=True) # Filters every fight that needs scoring
    objs = [] # Holds fight objects to bulk create
    # Iterate through fights; score fight; append to objs list
    for fight in fights:
        # Skip fights with no winner ONLY if it's not a draw
        if fight.winner is None and fight.method not in ("Decision - Split", "Decision - Majority", "Draw"):
            continue
        fight_stats = FightStats.objects.filter(fight=fight) # Filter FightStats rows for fight(should contain 2 rows. 1 for each fighter.)
        # Skip incomplete fight data
        if fight_stats.count() != 2:
            continue
        # Iterate through fight_stats rows (fight stat for each fighter)
        for fight_stat in fight_stats:
            # Skip incomplete fight data
            if fight_stat.fighter is None:
                continue
            total_rounds_score = 0
            round_stats = RoundStats.objects.filter(fight_stats=fight_stat) # Filter every round for the fighter in the fight
            # Iterate through every round in round_stats; add all round totals; create FightScore object
            for round in round_stats:
                round_score = RoundScore.objects.get(round_stats=round)
                total_rounds_score += round_score.round_total_points
            is_winner = (fight.winner is not None and fight_stat.fighter.full_name == fight.winner.full_name) # Determines if fighter is winner
            # LOSER
            if not is_winner:
                obj = FightScore(
                fighter = fight_stat.fighter,
                fight = fight,
                points_win = 0,
                points_round = 0,
                points_time = 0,
                fight_total_points = total_rounds_score,
            )
            # WINNER
            else:
                points_round = score_round_finish(round=fight.round, time=fight.time,)
                points_time = score_time(fight.time)
                points_win = 20
                obj = FightScore(
                    fighter = fight_stat.fighter,
                    fight = fight,
                    points_win = points_win,
                    points_round = points_round,
                    points_time = points_time,
                    fight_total_points =  total_rounds_score + points_win + points_round + points_time,
                )
            objs.append(obj)
            entry_counter += 1

    FightScore.objects.bulk_create(objs=objs)
    print(f"Created {entry_counter} new FightScore rows.")

def populate_database():
    populate_fighter_stats_tables()
    populate_round_score()
    populate_fight_score()