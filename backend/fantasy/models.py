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
from django.conf import settings

class Fighters(models.Model):
    fighter_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=50, null=True, blank=True)
    last_name = models.CharField(max_length=50, null=True, blank=True)
    full_name = models.CharField(max_length=100, null=True, blank=True, unique=True)
    normalized_name = models.CharField(max_length=100, null=True, blank=True, unique=True)
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
    time = models.IntegerField(default=0, null=True, blank=True)
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

    # Opponent stats
    sig_str_landed_opp = models.IntegerField(default=0, null=True, blank=True)
    sig_str_attempted_opp = models.IntegerField(default=0, null=True, blank=True)
    td_landed_opp = models.IntegerField(default=0, null=True, blank=True)
    td_attempted_opp = models.IntegerField(default=0, null=True, blank=True)
    ctrl_time_opp = models.IntegerField(default=0, null=True, blank=True)

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

    # Wins by method
    ko_tko_wins = models.IntegerField(default=0)
    tko_doctor_stoppage_wins = models.IntegerField(default=0)
    submission_wins = models.IntegerField(default=0)
    unanimous_decision_wins = models.IntegerField(default=0)
    split_decision_wins = models.IntegerField(default=0)
    majority_decision_wins = models.IntegerField(default=0)
    dq_wins = models.IntegerField(default=0)

    # Losses by method
    ko_tko_losses = models.IntegerField(default=0)
    tko_doctor_stoppage_losses = models.IntegerField(default=0)
    submission_losses = models.IntegerField(default=0)
    unanimous_decision_losses = models.IntegerField(default=0)
    split_decision_losses = models.IntegerField(default=0)
    majority_decision_losses = models.IntegerField(default=0)
    dq_losses = models.IntegerField(default=0)

    # Striking / grappling stats
    sig_str_landed = models.IntegerField(default=0)
    sig_str_attempted = models.IntegerField(default=0)
    total_str_landed = models.IntegerField(default=0)
    total_str_attempted = models.IntegerField(default=0)
    td_landed = models.IntegerField(default=0)
    td_attempted = models.IntegerField(default=0)
    sub_att = models.IntegerField(default=0)
    ctrl_time = models.IntegerField(default=0)
    reversals = models.IntegerField(default=0)
    total_fight_time = models.IntegerField(default=0)

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

    # Opponent stats
    sig_str_landed_opp = models.IntegerField(default=0, null=True, blank=True)
    sig_str_attempted_opp = models.IntegerField(default=0, null=True, blank=True)
    td_landed_opp = models.IntegerField(default=0, null=True, blank=True)
    td_attempted_opp = models.IntegerField(default=0, null=True, blank=True)
    ctrl_time_opp = models.IntegerField(default=0, null=True, blank=True)

class RoundScore(models.Model):
    round_stats=models.ForeignKey(RoundStats, on_delete=models.CASCADE, null=True, blank=True)
    points_knockdowns=models.FloatField(default=0,null=True, blank=True)
    points_sig_str_landed=models.FloatField(default=0,null=True, blank=True)
    points_td_landed=models.FloatField(default=0,null=True, blank=True)
    points_sub_att=models.FloatField(default=0,null=True, blank=True)
    points_ctrl_time=models.FloatField(default=0,null=True, blank=True)
    points_reversals=models.FloatField(default=0,null=True, blank=True)
    round_total_points=models.FloatField(default=0, null=True, blank=True)
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['round_stats'],
                name='unique_roundscore_per_round'
            )
        ]

class FightScore(models.Model):
    fighter=models.ForeignKey(Fighters, on_delete=models.CASCADE, null=True, blank=True)
    fight=models.ForeignKey(Fights, on_delete=models.CASCADE, null=True, blank=True)
    points_win=models.FloatField(default=0, null=True, blank=True)
    points_round=models.FloatField(default=0, null=True, blank=True)
    points_time=models.FloatField(default=0, null=True, blank=True)
    fight_total_points=models.FloatField(default=0, null=True, blank=True)
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['fight', 'fighter'],
                name='unique_fight_fighter_per_fight'
            )
        ]
'''
    -   Fantasy Models
'''

class League(models.Model):

    class Status(models.TextChoices):
        SETUP = "SETUP", "Setup"
        DRAFTING = "DRAFTING", "Drafting"
        LIVE = "LIVE", "Live"
        COMPLETED = "COMPLETED", "Completed"       

    name=models.CharField(max_length=64)
    creator=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status=models.CharField(choices=Status.choices, default=Status.SETUP)
    capacity = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)
    join_key = models.CharField(unique=True, max_length=12)

class LeagueMember(models.Model):

    class Role(models.TextChoices):
        CREATOR = "CREATOR", "Creator"
        PLAYER = "PLAYER", "Player"

    owner=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    league=models.ForeignKey(League, on_delete=models.CASCADE)
    role=models.CharField(choices=Role.choices, default=Role.PLAYER)
    joined_at=models.DateTimeField(auto_now_add=True)

class Team(models.Model):
    owner=models.ForeignKey(LeagueMember, on_delete=models.CASCADE)
    name=models.CharField(max_length=64)
    created_at=models.DateTimeField(auto_now_add=True)

class Roster(models.Model):

    class SlotType(models.TextChoices):
        
        STRAWWEIGHT = "STRAWWEIGHT", "Strawweight"
        FLYWEIGHT = "FLYWEIGHT", "Flyweight"
        BANTAMWEIGHT = "BANTAMWEIGHT", "Bantamweight"
        FEATHERWEIGHT = "FEATHERWEIGHT", "Featherweight"
        LIGHTWEIGHT = "LIGHTWEIGHT", "Lightweight"
        WELTERWEIGHT = "WELTERWEIGHT", "Welterweight"
        MIDDLEWEIGHT = "MIDDLEWEIGHT", "Middleweight"
        LIGHT_HEAVYWEIGHT = "LIGHT_HEAVYWEIGHT", "Light Heavyweight"
        HEAVYWEIGHT = "HEAVYWEIGHT", "Heavyweight"
        
        # Special
        FLEX = "FLEX", "Flex"

    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    fighter = models.ForeignKey(Fighters, on_delete=models.CASCADE, null=True, blank=True)
    slot_type = models.CharField(choices=SlotType.choices, max_length=32)

class Draft(models.Model):

    class Status(models.TextChoices):
        NOT_SCHEDULED = "NOT_SCHEDULED", "Not Scheduled"
        PENDING = "PENDING", "Pending"        
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"
    league=models.ForeignKey(League, on_delete=models.CASCADE)
    status=models.CharField(choices=Status.choices, default=Status.NOT_SCHEDULED, max_length=16)
    draft_date=models.DateTimeField(null=True, blank=True)
    current_pick=models.IntegerField(default=0)
    pick_start_time=models.DateTimeField(null=True, blank=True)

class DraftOrder(models.Model):
    team=models.ForeignKey(Team, on_delete=models.CASCADE)
    draft=models.ForeignKey(Draft, on_delete=models.CASCADE)
    pick_num=models.IntegerField()

    class Meta:
        # Ensures only one draft pick per draft
        constraints = [
            models.UniqueConstraint(
                fields=['draft', 'pick_num'], 
                name="unique_draft_pick_in_draft")
        ]
        ordering = ['pick_num']

class DraftPick(models.Model):
    fighter=models.ForeignKey(Fighters, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    pick_num=models.IntegerField()
    draft=models.ForeignKey(Draft, on_delete=models.CASCADE)
    class Meta:
        # Ensures only one draft pick and fighter per draft
        constraints = [
            models.UniqueConstraint(
                fields=['fighter', 'draft'], 
                name="unique_fighter_in__draft"),
            models.UniqueConstraint(
                fields=['pick_num', 'draft'], 
                name="unique_pick_num_in_draft"),
                
        ]