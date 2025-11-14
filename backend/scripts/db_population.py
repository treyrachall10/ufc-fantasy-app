"""
    -   Responsible for populating and updating database through connecting headers with model fields
"""
import csv
from django.db import models
from fantasy.models import Fighters, Events, Fights, FightStats
from config import DATACLEANPATH, MODEL_MAP

def populate_fighter_stats_tables():
    """
        -   Populates database dynamically by reading the files in the MODEL_FILE_MAP
        -   RETURNS: Nothing; it just builds the database
        -   THIS ONLY POPULATES THE FIGHTERS IN FIGHT STATS, THIS HAS NOTHING TO DO WITH FANTASY SCORING TABLES
    """
    # Iterate through every model in MODEL_FILE_MAP
    for key, value in MODEL_MAP.items():

        entry_counter = 0
        model = value['model'] # Holds model object
        csv_file = value['file']
        foreign_keys = value['foreign_keys'] # Holds dict of foreign key model objects for each model
        unique_fields = value['unique_fields'] # List of unique fields to search for each model in get_or_create()
        model_fields = [f.name for f in model._meta.get_fields() if f.concrete and not f.auto_created]

        try:
            with open(f"{DATACLEANPATH}/{csv_file}", 'r') as file:
                reader = csv.DictReader(file)
                # Iterate through each row create object based on csv contents
                for row in reader:
                    row_data = {} # Serves as a dict mapping each csv column to a model field
                    lookup_kwargs = {}
                    # Iterate through fields  if field is in csv header; add row header/value in row_data
                    for field in model_fields:
                        if field in row:
                            # Handles empty cells, NaN's
                            if row[field] == '':
                                row_data[field] = None
                            else:
                                try:
                                    row_data[field] = int(float(row[field]))
                                except ValueError:
                                    row_data[field] = row[field].strip() # Handles strings with tailing spaces
                    # Iterate through foreign keys; create foreign key object based on model
                    if foreign_keys and isinstance(foreign_keys, dict):
                        for fk_name, fk_model in foreign_keys.items():
                            if fk_model is Events:
                                event_name = row.get('event')
                                if event_name:
                                    row_data[fk_name] = Events.objects.filter(event=event_name.strip()).first()
                            elif fk_model is Fighters:
                                if model is Fights:
                                    name = row.get('winner')
                                else:
                                    name = row.get('fighter')
                                if name:
                                    row_data[fk_name] = Fighters.objects.filter(full_name=name.strip()).first()
                            elif fk_model is Fights:
                                event_name = row.get('event')
                                bout = " ".join(row.get('bout', '').split())
                                event_obj = None
                                if event_name:
                                    event_obj = Events.objects.filter(event=event_name.strip()).first()
                                if event_obj and bout:
                                    row_data[fk_name] = Fights.objects.filter(event=event_obj, bout=bout.strip()).first()
                            elif fk_model is FightStats:
                                name = row.get('fighter')
                                event_name = row.get('event')
                                bout = row.get('bout')
                                event_obj = None
                                fighter_obj = None
                                fight_obj = None
                                if event_name:
                                    event_obj = Events.objects.filter(event=event_name.strip()).first()
                                    if event_obj and bout:
                                        fight_obj = Fights.objects.filter(event=event_obj, bout=bout.strip()).first()
                                if name:
                                    fighter_obj = Fighters.objects.filter(full_name=name.strip()).first()
                                if fight_obj and fighter_obj:
                                    row_data[fk_name] = FightStats.objects.filter(fight=fight_obj, fighter=fighter_obj).first()
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