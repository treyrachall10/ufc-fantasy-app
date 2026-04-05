"""
    -   Responsible for populating and updating database through connecting headers with model fields
"""
import csv
from datetime import datetime
from django.db.models import Prefetch
from fantasy.models import Fighters, Events, Fights, FightStats, RoundStats, RoundScore, FightScore, FighterCareerStats, League, Team, Roster, Draft
from config import DATACLEANPATH, MODEL_MAP
from scripts.utils import normalize_name
from scripts.scoring import score_knockdowns, score_td_landed, score_sub_att, score_ctrl_time, score_round_finish, score_time


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

def populate_fights_table():
    """
        -   Populates the Fights table with event and winner foreign keys
        -   RETURNS: Nothing; it just builds the Fights table
    """
    print("Populating fights table...")
    model_class = Fights
    csv_file = MODEL_MAP["fights"]["file"]
    unique_fields = MODEL_MAP["fights"]["unique_fields"]

    # Get all concrete model fields (excluding auto-generated ones), exclude primary keys
    model_fields = [f.name for f in model_class._meta.get_fields() if f.concrete and not f.auto_created and not f.primary_key]

    create_list = []  # Holds new fight objects to bulk create
    update_list = []  # Holds existing fight objects with updated data to bulk update

    # Build lookup for Events FK (keyed by event name only, no date)
    events = Events.objects.all()
    events_by_name = {
        event.event: event
        for event in events
    }

    # Build lookup for Fighters FK (keyed by normalized_name)
    fighters = Fighters.objects.all()
    fighters_by_normalized_name = {
        fighter.normalized_name: fighter
        for fighter in fighters
    }

    # Build lookup for existing Fights (keyed by event and bout)
    existing_fights = model_class.objects.all()
    fights_by_lookup = {
        (fight.event_id, fight.bout): fight
        for fight in existing_fights
    }

    # Process CSV file
    with open(f"{DATACLEANPATH}/{csv_file}", "r") as file:
        reader = csv.DictReader(file)

        for row in reader:
            row_data = {}

            # Parse field values from CSV (skip FK fields; handle them separately)
            for field in model_fields:
                if field in {"event", "winner"}:
                    continue  # FK fields handled below

                if field not in row:
                    continue

                value = row[field]

                if value == "":
                    row_data[field] = None
                else:
                    try:
                        row_data[field] = int(float(value))
                    except ValueError:
                        row_data[field] = value.strip()  # String values

            # Resolve event FK (match by event name only)
            event_name = row.get("event").strip() if not None else None
            if event_name:
                event_obj = events_by_name.get(event_name.strip())
                if event_obj is None:
                    raise ValueError(f"Event not found: {event_name}")
                row_data["event"] = event_obj
            else:
                raise ValueError("Event name missing in row")

            # Resolve winner FK (match by normalized fighter name)
            winner_name = row.get("winner")
            if winner_name:
                normalized_winner = normalize_name(winner_name)
                winner_obj = fighters_by_normalized_name.get(normalized_winner)
                if winner_obj is None:
                    raise ValueError(f"Winner fighter not found: {winner_name}")
                row_data["winner"] = winner_obj
            else:
                row_data["winner"] = None  # Allow null winner (draws)

            # Build lookup key using unique fields (event_id and bout)
            bout = row_data.get("bout")
            event_id = row_data["event"].event_id if row_data.get("event") else None
            lookup_key = (event_id, bout)

            existing_obj = fights_by_lookup.get(lookup_key)

            # If record does not exist, create new one
            if existing_obj is None:
                try:
                    new_obj = model_class(**row_data)
                    create_list.append(new_obj)
                    fights_by_lookup[lookup_key] = new_obj
                except Exception as e:
                    print(f"ERROR creating fight object from row {row}")
                    print(f"   {e}")
                continue

            # If record exists, check for changes
            has_changes = False
            for field in model_fields:
                if field in {"event", "winner"}:
                    continue  # FK updates handled differently; skip for now

                if field not in row_data:
                    continue

                new_value = row_data.get(field)
                if getattr(existing_obj, field) != new_value:
                    setattr(existing_obj, field, new_value)
                    has_changes = True

            if has_changes:
                update_list.append(existing_obj)

    # Bulk create new records
    if create_list:
        try:
            model_class.objects.bulk_create(
                objs=create_list,
                update_fields=[field for field in model_fields if field not in unique_fields and field not in {"event", "winner"}],
            )
        except Exception as e:
            print("ERROR bulk creating fights")
            print(f"   {e}")

    # Bulk update existing records
    if update_list:
        try:
            model_class.objects.bulk_update(objs=update_list, fields=model_fields)
        except Exception as e:
            print("ERROR bulk updating fights")
            print(f"   {e}")

    print(f"Created {len(create_list)} new fights rows.")
    print(f"Updated {len(update_list)} existing fights rows.")


def populate_fight_stats_table():
    """
        -   Populates the FightStats table with fight and fighter foreign keys
        -   RETURNS: Nothing; it just builds the FightStats table
    """
    print("Populating fight_stats table...")
    model_class = FightStats
    csv_file = MODEL_MAP["fight_stats"]["file"]
    unique_fields = MODEL_MAP["fight_stats"]["unique_fields"]

    # Get all concrete model fields (excluding auto-generated ones), exclude primary keys
    model_fields = [f.name for f in model_class._meta.get_fields() if f.concrete and not f.auto_created and not f.primary_key]

    create_list = []  # Holds new fight stats objects to bulk create
    update_list = []  # Holds existing fight stats objects with updated data to bulk update

    # Build lookup for Events FK (keyed by event name)
    events = Events.objects.all()
    events_by_name = {
        event.event: event
        for event in events
    }

    # Build lookup for Fighters FK (keyed by normalized_name)
    fighters = Fighters.objects.all()
    fighters_by_normalized_name = {
        fighter.normalized_name: fighter
        for fighter in fighters
    }

    # Build lookup for Fights FK (keyed by event_id and bout)
    fights = Fights.objects.all()
    fights_by_lookup = {
        (fight.event_id, fight.bout): fight
        for fight in fights
    }

    # Build lookup for existing FightStats (keyed by fight_id and fighter_id)
    existing_fight_stats = model_class.objects.all()
    fight_stats_by_lookup = {
        (fs.fight_id, fs.fighter_id): fs
        for fs in existing_fight_stats
    }

    # Process CSV file
    with open(f"{DATACLEANPATH}/{csv_file}", "r") as file:
        reader = csv.DictReader(file)

        for row in reader:
            row_data = {}

            # Parse field values from CSV (skip FK fields; handle them separately)
            for field in model_fields:
                if field in {"fight", "fighter"}:
                    continue  # FK fields handled below

                if field not in row:
                    continue

                value = row[field]

                if value == "":
                    row_data[field] = None
                else:
                    try:
                        row_data[field] = int(float(value))
                    except ValueError:
                        row_data[field] = value.strip()  # String values

            # Resolve Event FK first (needed to find Fight)
            event_name = row.get("event")
            if event_name:
                event_obj = events_by_name.get(event_name.strip())
                if event_obj is None:
                    raise ValueError(f"Event not found: {event_name}")
            else:
                raise ValueError("Event name missing in row")

            # Resolve Fight FK using Event and bout
            bout = row.get("bout")
            if bout:
                bout = " ".join(bout.split())  # Normalize whitespace
                fight_lookup_key = (event_obj.event_id, bout)
                fight_obj = fights_by_lookup.get(fight_lookup_key)
                if fight_obj is None:
                    raise ValueError(f"Fight not found for event {event_name} and bout {bout}")
                row_data["fight"] = fight_obj
            else:
                raise ValueError("Bout name missing in row")

            # Resolve Fighter FK (match by normalized fighter name)
            fighter_name = row.get("fighter")
            if fighter_name:
                normalized_fighter = normalize_name(fighter_name)
                fighter_obj = fighters_by_normalized_name.get(normalized_fighter)
                if fighter_obj is None:
                    raise ValueError(f"Fighter not found: {fighter_name}")
                row_data["fighter"] = fighter_obj
            else:
                raise ValueError("Fighter name missing in row")

            # Build lookup key using fight_id and fighter_id
            lookup_key = (fight_obj.fight_id, fighter_obj.fighter_id)

            existing_obj = fight_stats_by_lookup.get(lookup_key)

            # If record does not exist, create new one
            if existing_obj is None:
                try:
                    new_obj = model_class(**row_data)
                    create_list.append(new_obj)
                    fight_stats_by_lookup[lookup_key] = new_obj
                except Exception as e:
                    print(f"ERROR creating fight_stats object from row {row}")
                    print(f"   {e}")
                continue

            # If record exists, check for changes
            has_changes = False
            for field in model_fields:
                if field in {"fight", "fighter"}:
                    continue  # FK updates handled differently; skip for now

                if field not in row_data:
                    continue

                new_value = row_data.get(field)
                if getattr(existing_obj, field) != new_value:
                    setattr(existing_obj, field, new_value)
                    has_changes = True

            if has_changes:
                update_list.append(existing_obj)

    # Bulk create new records
    if create_list:
        try:
            model_class.objects.bulk_create(
                objs=create_list,
                update_fields=[field for field in model_fields if field not in unique_fields and field not in {"fight", "fighter"}],
            )
        except Exception as e:
            print("ERROR bulk creating fight_stats")
            print(f"   {e}")

    # Bulk update existing records
    if update_list:
        try:
            model_class.objects.bulk_update(objs=update_list, fields=model_fields)
        except Exception as e:
            print("ERROR bulk updating fight_stats")
            print(f"   {e}")

    print(f"Created {len(create_list)} new fight_stats rows.")
    print(f"Updated {len(update_list)} existing fight_stats rows.")


def populate_round_stats_table():
    """
        -   Populates the RoundStats table with fight_stats foreign key
        -   RETURNS: Nothing; it just builds the RoundStats table
    """
    print("Populating round_stats table...")
    model_class = RoundStats
    csv_file = MODEL_MAP["round_stats"]["file"]
    unique_fields = MODEL_MAP["round_stats"]["unique_fields"]

    # Get all concrete model fields (excluding auto-generated ones), exclude primary keys
    model_fields = [f.name for f in model_class._meta.get_fields() if f.concrete and not f.auto_created and not f.primary_key]

    create_list = []  # Holds new round stats objects to bulk create
    update_list = []  # Holds existing round stats objects with updated data to bulk update

    # Build lookup for Events FK (keyed by event name)
    events = Events.objects.all()
    events_by_name = {
        event.event: event
        for event in events
    }

    # Build lookup for Fighters FK (keyed by normalized_name)
    fighters = Fighters.objects.all()
    fighters_by_normalized_name = {
        fighter.normalized_name: fighter
        for fighter in fighters
    }

    # Build lookup for Fights FK (keyed by event_id and bout)
    fights = Fights.objects.all()
    fights_by_lookup = {
        (fight.event_id, fight.bout): fight
        for fight in fights
    }

    # Build lookup for FightStats FK (keyed by fight_id and fighter_id)
    fight_stats = FightStats.objects.all()
    fight_stats_by_lookup = {
        (fight_stat.fight_id, fight_stat.fighter_id): fight_stat
        for fight_stat in fight_stats
    }

    # Build lookup for existing RoundStats (keyed by fight_stats_id and round_number)
    existing_round_stats = model_class.objects.all()
    round_stats_by_lookup = {
        (round_stat.fight_stats_id, round_stat.round_number): round_stat
        for round_stat in existing_round_stats
    }

    # Process CSV file
    with open(f"{DATACLEANPATH}/{csv_file}", "r") as file:
        reader = csv.DictReader(file)

        for row in reader:
            row_data = {}

            # Parse field values from CSV (skip FK field; handle it separately)
            for field in model_fields:
                if field == "fight_stats":
                    continue

                if field not in row:
                    continue

                value = row[field]

                if value == "":
                    row_data[field] = None
                else:
                    try:
                        row_data[field] = int(float(value))
                    except ValueError:
                        row_data[field] = value.strip()

            # Resolve Event first
            event_name = row.get("event")
            if event_name:
                event_obj = events_by_name.get(event_name.strip())
                if event_obj is None:
                    raise ValueError(f"Event not found: {event_name}")
            else:
                raise ValueError("Event name missing in row")

            # Resolve Fight using Event and bout
            bout = row.get("bout")
            if bout:
                bout = " ".join(bout.split())
                fight_lookup_key = (event_obj.event_id, bout)
                fight_obj = fights_by_lookup.get(fight_lookup_key)
                if fight_obj is None:
                    raise ValueError(f"Fight not found for event {event_name} and bout {bout}")
            else:
                raise ValueError("Bout name missing in row")

            # Resolve Fighter
            fighter_name = row.get("fighter")
            if fighter_name:
                normalized_fighter = normalize_name(fighter_name)
                fighter_obj = fighters_by_normalized_name.get(normalized_fighter)
                if fighter_obj is None:
                    raise ValueError(f"Fighter not found: {fighter_name}")
            else:
                raise ValueError("Fighter name missing in row")

            # Resolve FightStats using fight and fighter
            fight_stats_lookup_key = (fight_obj.fight_id, fighter_obj.fighter_id)
            fight_stats_obj = fight_stats_by_lookup.get(fight_stats_lookup_key)
            if fight_stats_obj is None:
                raise ValueError(
                    f"FightStats not found for fight {fight_obj.fight_id} and fighter {fighter_obj.fighter_id}"
                )
            row_data["fight_stats"] = fight_stats_obj

            # Build lookup key using unique fields (fight_stats, round_number)
            lookup_key = (fight_stats_obj.id, row_data.get("round_number"))
            existing_obj = round_stats_by_lookup.get(lookup_key)

            # If record does not exist, create new one
            if existing_obj is None:
                try:
                    new_obj = model_class(**row_data)
                    create_list.append(new_obj)
                    round_stats_by_lookup[lookup_key] = new_obj
                except Exception as e:
                    print(f"ERROR creating round_stats object from row {row}")
                    print(f"   {e}")
                continue

            # If record exists, check for changes
            has_changes = False
            for field in model_fields:
                if field == "fight_stats":
                    continue

                if field not in row_data:
                    continue

                new_value = row_data.get(field)
                if getattr(existing_obj, field) != new_value:
                    setattr(existing_obj, field, new_value)
                    has_changes = True

            if has_changes:
                update_list.append(existing_obj)

    # Bulk create new records
    if create_list:
        try:
            model_class.objects.bulk_create(
                objs=create_list,
                update_fields=[field for field in model_fields if field not in unique_fields and field != "fight_stats"],
            )
        except Exception as e:
            print("ERROR bulk creating round_stats")
            print(f"   {e}")

    # Bulk update existing records
    if update_list:
        try:
            model_class.objects.bulk_update(objs=update_list, fields=model_fields)
        except Exception as e:
            print("ERROR bulk updating round_stats")
            print(f"   {e}")

    print(f"Created {len(create_list)} new round_stats rows.")
    print(f"Updated {len(update_list)} existing round_stats rows.")


def populate_fighter_career_stats_table():
    """
        -   Populates the FighterCareerStats table with fighter foreign key
        -   RETURNS: Nothing; it just builds the FighterCareerStats table
    """
    print("Populating fighter_career_stats table...")
    model_class = FighterCareerStats
    csv_file = MODEL_MAP["fighter_career_stats"]["file"]
    unique_fields = MODEL_MAP["fighter_career_stats"]["unique_fields"]

    # Get all concrete model fields (excluding auto-generated ones), exclude primary keys
    model_fields = [f.name for f in model_class._meta.get_fields() if f.concrete and not f.auto_created and not f.primary_key]

    create_list = []  # Holds new career stats objects to bulk create
    update_list = []  # Holds existing career stats objects with updated data to bulk update

    # Build lookup for Fighters FK (keyed by normalized_name)
    fighters = Fighters.objects.all()
    fighters_by_normalized_name = {
        fighter.normalized_name: fighter
        for fighter in fighters
    }

    # Build lookup for existing FighterCareerStats (keyed by fighter_id)
    existing_career_stats = model_class.objects.all()
    career_stats_by_lookup = {
        stats.fighter_id: stats
        for stats in existing_career_stats
    }

    # Process CSV file
    with open(f"{DATACLEANPATH}/{csv_file}", "r") as file:
        reader = csv.DictReader(file)

        for row in reader:
            row_data = {}

            # Parse field values from CSV (skip FK field; handle it separately)
            for field in model_fields:
                if field == "fighter":
                    continue

                if field not in row:
                    continue

                value = row[field]

                if value == "":
                    row_data[field] = None
                else:
                    try:
                        row_data[field] = int(float(value))
                    except ValueError:
                        row_data[field] = value.strip()

            # Resolve Fighter FK (match by normalized fighter name)
            fighter_name = row.get("fighter")
            if fighter_name:
                normalized_fighter = normalize_name(fighter_name)
                fighter_obj = fighters_by_normalized_name.get(normalized_fighter)
                if fighter_obj is None:
                    raise ValueError(f"Fighter not found: {fighter_name}")
                row_data["fighter"] = fighter_obj
            else:
                raise ValueError("Fighter name missing in row")

            # Build lookup key using fighter_id
            lookup_key = fighter_obj.fighter_id

            existing_obj = career_stats_by_lookup.get(lookup_key)

            # If record does not exist, create new one
            if existing_obj is None:
                try:
                    new_obj = model_class(**row_data)
                    create_list.append(new_obj)
                    career_stats_by_lookup[lookup_key] = new_obj
                except Exception as e:
                    print(f"ERROR creating fighter_career_stats object from row {row}")
                    print(f"   {e}")
                continue

            # If record exists, check for changes
            has_changes = False
            for field in model_fields:
                if field == "fighter":
                    continue

                if field not in row_data:
                    continue

                new_value = row_data.get(field)
                if getattr(existing_obj, field) != new_value:
                    setattr(existing_obj, field, new_value)
                    has_changes = True

            if has_changes:
                update_list.append(existing_obj)

    # Bulk create new records
    if create_list:
        try:
            model_class.objects.bulk_create(
                objs=create_list,
                update_fields=[field for field in model_fields if field not in unique_fields and field != "fighter"],
            )
        except Exception as e:
            print("ERROR bulk creating fighter_career_stats")
            print(f"   {e}")

    # Bulk update existing records
    if update_list:
        try:
            model_class.objects.bulk_update(objs=update_list, fields=model_fields)
        except Exception as e:
            print("ERROR bulk updating fighter_career_stats")
            print(f"   {e}")

    print(f"Created {len(create_list)} new fighter_career_stats rows.")
    print(f"Updated {len(update_list)} existing fighter_career_stats rows.")


def populate_round_score():
    """
        -   Iterates through rows in RoundStats model and calculates fantasy scores
        -   RETURNS: Nothing; populates the RoundScore table 
    """
    entry_counter = 0
    round_stats = RoundStats.objects.filter(roundscore__isnull=True).select_related('fight_stats__fighter', 'fight_stats__fight') # Filters every row that needs scoring
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
    print("Populating fight_score table...")
    entry_counter = 0
    fights = Fights.objects.filter(fightscore__isnull=True).select_related('winner').prefetch_related(
        'fightstats_set__fighter',
        'fightstats_set__roundstats_set__roundscore_set'
    ) # Filters every fight that needs scoring and prefetches related data
    objs = [] # Holds fight objects to bulk create
    # Iterate through fights; score fight; append to objs list
    for fight in fights:
        # Skip fights with no winner ONLY if it's not a draw
        if fight.winner is None and fight.method not in ("Decision - Split", "Decision - Majority", "Draw"):
            continue
        fight_stats = fight.fightstats_set.all() # Use prefetched FightStats
        # Skip incomplete fight data
        if len(fight_stats) != 2:
            continue
        # Iterate through fight_stats rows (fight stat for each fighter)
        for fight_stat in fight_stats:
            # Skip incomplete fight data
            if fight_stat.fighter is None:
                continue
            total_rounds_score = 0
            round_stats = fight_stat.roundstats_set.all() # Use prefetched RoundStats
            # Iterate through every round in round_stats; add all round totals; create FightScore object
            for round in round_stats:
                round_score = round.roundscore_set.all() # Use prefetched RoundScore
                total_rounds_score += round_score[0].round_total_points
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

def populate_team_scores():
    '''
        -   Populates and updates all teams scores in the Team table for completed-draft leagues
        -   RETURNS: Nothing; updates the Team table with new scores
    '''
    # Get all leagues whose drafts are completed and prefetch related team and roster data.
    leagues = League.objects.filter(draft__status=Draft.Status.COMPLETED).prefetch_related(
        Prefetch(
            'draft_set',
            queryset=Draft.objects.filter(status=Draft.Status.COMPLETED),
        ),
        Prefetch(
            'leaguemember_set__team_set',
            queryset=Team.objects.prefetch_related(
                Prefetch(
                    'roster_set',
                    queryset=Roster.objects.select_related('fighter'),
                )
            ),
        ),
    )

    # Iterate through each eligible league.
    for league in leagues:
        # Iterate through each team connected to the league.
        for league_member in league.leaguemember_set.all():
            for team in league_member.team_set.all():
                # Iterate through each roster row connected to the team.
                for roster in team.roster_set.all():
                    # Iterate through each fighter in the roster row.
                    if roster.fighter is None:
                        continue
                    for fighter in [roster.fighter]:
                        pass

def populate_database():
    populate_simple_tables()
    populate_fights_table()
    populate_fight_stats_table()
    populate_round_stats_table()
    populate_fighter_career_stats_table()
    populate_round_score()
    populate_fight_score()