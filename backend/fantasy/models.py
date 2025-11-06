from django.db import models

"""
    - Populates the database with tables Fighters, Events, Fights, FightStats, RoundStats, and FighterCareerStats
    - Fighters serves as a primary key to FightStats and has a one-to-one relationship with FighterCareerStats and holds fighters metadata
    - Events serves as a primary key to Fights and holds event metadata
    - Fights serves as a primary key to FightStats and holds a foreign key to event; Fights holds specific fights metadata
    - FightStats holds a foreign key to Fight and Fighters and includes fight stats for each fighter for each of their fights (2 rows per fight; 1 per fighter)
    - RoundStats holds a foreign key to FightStats and includes per round fight stats for each fighter for each fight
    - FighterCareerStats holds a one-to-one relationship with Fighters and contains fighters’ career stats
"""

class Fighters(models.Model):
    fighter_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=50, null=True, blank=True)
    last_name = models.CharField(max_length=50, null=True, blank=True)
    full_name = models.CharField(max_length=100, null=True, blank=True, unique=True)
    nick_name = models.CharField(max_length=50, null=True, blank=True)
    stance = models.CharField(max_length=50, null=True, blank=True)
    weight = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)
    reach = models.IntegerField(null=True, blank=True)
    dob = models.DateField(null=True, blank=True)


class Events(models.Model):
    event_id = models.AutoField(primary_key=True)
    event = models.CharField(max_length=100, null=True, blank=True)
    date = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=50, null=True, blank=True)


class Fights(models.Model):
    fight_id = models.AutoField(primary_key=True)
    event = models.ForeignKey(Events, on_delete=models.CASCADE, null=True, blank=True)
    bout = models.CharField(max_length=100, null=True, blank=True)
    weight_class = models.CharField(max_length=100, null=True, blank=True)
    method = models.CharField(max_length=50, null=True, blank=True)
    round = models.IntegerField(null=True, blank=True)
    round_format = models.CharField(max_length=50, null=True, blank=True)
    time = models.CharField(max_length=50, null=True, blank=True)
    winner = models.ForeignKey(Fighters, on_delete=models.SET_NULL, null=True, blank=True)

class FightStats(models.Model):
    fight = models.ForeignKey(Fights, on_delete=models.CASCADE, null=True, blank=True)
    fighter = models.ForeignKey(Fighters, on_delete=models.CASCADE, null=True, blank=True)
    result = models.CharField(max_length=10, null=True, blank=True)
    kd = models.IntegerField(default=0, null=True, blank=True)
    sig_str_landed = models.IntegerField(default=0, null=True, blank=True)
    sig_str_attempted = models.IntegerField(default=0, null=True, blank=True)
    total_str_landed = models.IntegerField(default=0, null=True, blank=True)
    total_str_attempted = models.IntegerField(default=0, null=True, blank=True)
    td_landed = models.IntegerField(default=0, null=True, blank=True)
    td_attempted = models.IntegerField(default=0, null=True, blank=True)
    sub_att = models.IntegerField(default=0, null=True, blank=True)
    ctrl_time = models.IntegerField(default=0, null=True, blank=True)
    reversals = models.IntegerField(default=0, null=True, blank=True)
    head_str_landed = models.IntegerField(default=0, null=True, blank=True)
    head_str_attempted = models.IntegerField(default=0, null=True, blank=True)
    body_str_landed = models.IntegerField(default=0, null=True, blank=True)
    body_str_attempted = models.IntegerField(default=0, null=True, blank=True)
    leg_str_landed = models.IntegerField(default=0, null=True, blank=True)
    leg_str_attempted = models.IntegerField(default=0, null=True, blank=True)
    distance_str_landed = models.IntegerField(default=0, null=True, blank=True)
    distance_str_attempted = models.IntegerField(default=0, null=True, blank=True)
    clinch_str_landed = models.IntegerField(default=0, null=True, blank=True)
    clinch_str_attempted = models.IntegerField(default=0, null=True, blank=True)
    ground_str_landed = models.IntegerField(default=0, null=True, blank=True)
    ground_str_attempted = models.IntegerField(default=0, null=True, blank=True)


class RoundStats(models.Model):
    fight_stats = models.ForeignKey(FightStats, on_delete=models.CASCADE, null=True, blank=True)
    round_number = models.IntegerField(null=True, blank=True)
    kd = models.IntegerField(default=0, null=True, blank=True)
    sig_str_landed = models.IntegerField(default=0, null=True, blank=True)
    sig_str_attempted = models.IntegerField(default=0, null=True, blank=True)
    total_str_landed = models.IntegerField(default=0, null=True, blank=True)
    total_str_attempted = models.IntegerField(default=0, null=True, blank=True)
    td_landed = models.IntegerField(default=0, null=True, blank=True)
    td_attempted = models.IntegerField(default=0, null=True, blank=True)
    sub_att = models.IntegerField(default=0, null=True, blank=True)
    ctrl_time = models.IntegerField(default=0, null=True, blank=True)
    reversals = models.IntegerField(default=0, null=True, blank=True)
    head_str_landed = models.IntegerField(default=0, null=True, blank=True)
    head_str_attempted = models.IntegerField(default=0, null=True, blank=True)
    body_str_landed = models.IntegerField(default=0, null=True, blank=True)
    body_str_attempted = models.IntegerField(default=0, null=True, blank=True)
    leg_str_landed = models.IntegerField(default=0, null=True, blank=True)
    leg_str_attempted = models.IntegerField(default=0, null=True, blank=True)
    distance_str_landed = models.IntegerField(default=0, null=True, blank=True)
    distance_str_attempted = models.IntegerField(default=0, null=True, blank=True)
    clinch_str_landed = models.IntegerField(default=0, null=True, blank=True)
    clinch_str_attempted = models.IntegerField(default=0, null=True, blank=True)
    ground_str_landed = models.IntegerField(default=0, null=True, blank=True)
    ground_str_attempted = models.IntegerField(default=0, null=True, blank=True)

class FighterCareerStats(models.Model):
    fighter = models.OneToOneField(Fighters, on_delete=models.CASCADE, null=True, blank=True)
    total_fights = models.IntegerField(default=0)
    wins = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)
    draws = models.IntegerField(default=0)
    knockouts = models.IntegerField(default=0)
    submissions = models.IntegerField(default=0)
    unanimous_decisions = models.IntegerField(default=0)
    split_decisions = models.IntegerField(default=0)
    sig_str_landed = models.IntegerField(default=0)
    sig_str_attempted = models.IntegerField(default=0)
    total_str_landed = models.IntegerField(default=0)
    total_str_attempted = models.IntegerField(default=0)
    td_landed = models.IntegerField(default=0)
    td_attempted = models.IntegerField(default=0)
    sub_att = models.IntegerField(default=0)
    ctrl_time = models.IntegerField(default=0)
    reversals = models.IntegerField(default=0)
    head_str_landed = models.IntegerField(default=0)
    head_str_attempted = models.IntegerField(default=0)
    body_str_landed = models.IntegerField(default=0)
    body_str_attempted = models.IntegerField(default=0)
    leg_str_landed = models.IntegerField(default=0)
    leg_str_attempted = models.IntegerField(default=0)
    distance_str_landed = models.IntegerField(default=0)
    distance_str_attempted = models.IntegerField(default=0)
    clinch_str_landed = models.IntegerField(default=0)
    clinch_str_attempted = models.IntegerField(default=0)
    ground_str_landed = models.IntegerField(default=0)
    ground_str_attempted = models.IntegerField(default=0)
