"""
    -   Responsible for populating and updating database through connecting headers with model fields
"""
import csv
from django.db import models
from fantasy.models import Fighters, Events, Fights, FightStats, RoundStats, RoundScore, FightScore
from config import DATACLEANPATH, MODEL_MAP
from scripts.utils import normalize_name
from scripts.scoring import score_knockdowns, score_td_landed, score_sub_att, score_ctrl_time, score_win, score_round_finish, score_time

def populate_fighter_stats_tables():
    """
        -   Populates database dynamically by reading the files in the MODEL_FILE_MAP
        -   RETURNS: Nothing; it just builds the database
        -   THIS ONLY POPULATES THE FIGHTERS IN FIGHT STATS, THIS HAS NOTHING TO DO WITH FANTASY SCORING TABLES
    """
    # Iterate through every model in MODEL_FILE_MAP
    for key, value in MODEL_MAP.items():

        entry_counter = 0
        model = value['model']  # Holds model object
        csv_file = value['file']
        foreign_keys = value['foreign_keys']  # Holds dict of foreign key model objects for each model
        unique_fields = value['unique_fields']  # List of unique fields to search for each model in get_or_create()
        model_fields = [f.name for f in model._meta.get_fields() if f.concrete and not f.auto_created]

        try:
            with open(f"{DATACLEANPATH}/{csv_file}", 'r') as file:
                reader = csv.DictReader(file)

                # Iterate through each row create object based on csv contents
                for row in reader:
                    row_data = {}  # Serves as a dict mapping each csv column to a model field
                    lookup_kwargs = {}

                    # Iterate through fields if field is in csv header; add row header/value in row_data
                    for field in model_fields:
                        if field in row:
                            # Handles empty cells, NaN's
                            if row[field] == '':
                                row_data[field] = None
                            else:
                                try:
                                    row_data[field] = int(float(row[field]))
                                except ValueError:
                                    row_data[field] = row[field].strip()  # Handles strings with trailing spaces

                    # Iterate through foreign keys; create foreign key object based on model
                    if foreign_keys and isinstance(foreign_keys, dict):
                        for fk_name, fk_model in foreign_keys.items():

                            if fk_model is Events:
                                event_name = row.get('event')
                                if event_name:
                                    event = Events.objects.filter(event=event_name.strip()).first()
                                    if event is None:
                                        raise ValueError(f"Event not found: {event_name}")
                                    row_data[fk_name] = event

                            elif fk_model is Fighters:
                                if model is Fights:
                                    name = row.get('winner')
                                else:
                                    name = row.get('fighter')

                                if name:
                                    normalized_name = normalize_name(name)
                                    fighter = Fighters.objects.filter(
                                        normalized_name=normalized_name
                                    ).first()

                                    if fighter is None:
                                        raise ValueError(f"Fighter not found: {name}")

                                    row_data[fk_name] = fighter

                            elif fk_model is Fights:
                                event_name = row.get('event')
                                bout = " ".join(row.get('bout', '').split())

                                if event_name:
                                    event = Events.objects.filter(event=event_name.strip()).first()
                                    if event is None:
                                        raise ValueError(f"Event not found: {event_name}")

                                    fight = Fights.objects.filter(event=event, bout=bout).first()
                                    if fight is None:
                                        raise ValueError(f"Fight not found: {bout}")

                                    row_data[fk_name] = fight

                            elif fk_model is FightStats:
                                name = row.get('fighter')
                                event_name = row.get('event')
                                bout = " ".join(row.get('bout', '').split())

                                if event_name:
                                    event = Events.objects.filter(event=event_name.strip()).first()
                                    if event is None:
                                        raise ValueError(f"Event not found: {event_name}")

                                    fight = Fights.objects.filter(event=event, bout=bout).first()
                                    if fight is None:
                                        raise ValueError(f"Fight not found: {bout}")

                                if name:
                                    normalized_name = normalize_name(name)
                                    fighter = Fighters.objects.filter(
                                        normalized_name=normalized_name
                                    ).first()

                                    if fighter is None:
                                        raise ValueError(f"Fighter not found: {name}")

                                    fight_stats = FightStats.objects.filter(
                                        fight=fight, fighter=fighter
                                    ).first()

                                    if fight_stats is None:
                                        raise ValueError(
                                            f"FightStats not found for {name} in {bout}"
                                        )

                                    row_data[fk_name] = fight_stats

                    # Iterate through unique fields; add unique field data to lookup_kwargs and delete the field from row_data
                    for unique_field in unique_fields:
                        if unique_field in row_data:
                            lookup_kwargs[unique_field] = row_data[unique_field]
                            del row_data[unique_field]

                    try:
                        obj, created = model.objects.get_or_create(
                            **lookup_kwargs,       # the unique identifier fields (e.g. fight, fighter)
                            defaults=row_data      # everything else to fill in when creating
                        )
                        if created:
                            entry_counter += 1
                    except Exception as e:
                        print(f"ERROR creating {key} record for row {row}")
                        print(f"   {e}")

            print(f"Populated {key} ({entry_counter} records)")

        except FileNotFoundError:
            print(f"ERROR: Could not find file '{value['file']}'")


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