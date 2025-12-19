'''
    Contains serializers for django views
'''
from rest_framework import serializers
from fantasy.models import Fighters, FighterCareerStats, Events, Fights

class WinSerializer(serializers.HyperlinkedModelSerializer):
    total = serializers.IntegerField(source='wins', read_only=True)
    class Meta:
        model = FighterCareerStats
        fields = [
            'total',
            'ko_tko_wins',
            'tko_doctor_stoppage_wins',
            'submission_wins',
            'unanimous_decision_wins',
            'split_decision_wins',
            'majority_decision_wins',
            'dq_wins',
        ]

class LossSerializer(serializers.HyperlinkedModelSerializer):
    total = serializers.IntegerField(source='losses', read_only=True)
    class Meta:
        model = FighterCareerStats
        fields = [
            'total',
            'ko_tko_losses',
            'tko_doctor_stoppage_losses',
            'submission_losses',
            'unanimous_decision_losses',
            'split_decision_losses',
            'majority_decision_losses',
            'dq_losses',
        ]

class RecordSerializer(serializers.HyperlinkedModelSerializer):
    wins = WinSerializer(source='*', read_only=True)
    losses = LossSerializer(source='*', read_only=True)
    class Meta:
        model = FighterCareerStats
        fields = ['wins', 'losses', 'draws']

class FighterSerializer(serializers.HyperlinkedModelSerializer):
    record = RecordSerializer(source='fightercareerstats', many=False, read_only=True)

    class Meta:
        model = Fighters
        fields = [
            'fighter_id',
            'first_name',
            'last_name',
            'full_name',
            'nick_name',
            'stance',
            'weight',
            'height',
            'reach',
            'dob',
            'record',
        ]

class EventSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Events
        fields = [
            'event_id',
            'event',
            'date',
            'location',
        ]

class FightSerializer(serializers.HyperlinkedModelSerializer):
    event = EventSerializer(many=False, read_only=True)
    winner = serializers.CharField(source='winner.full_name', read_only=True)

    class Meta:
        model = Fights
        fields = [
            'fight_id',
            'event',
            'bout',
            'weight_class',
            'method',
            'round',
            'round_format',
            'time',
            'winner',
        ]

class TotalStrikesSerialier(serializers.HyperlinkedModelSerializer):
    landed = serializers.IntegerField(source='total_str_landed', read_only=True)
    attempted = serializers.IntegerField(source='total_str_attempted', read_only=True)
    class Meta:
        model = FighterCareerStats
        fields = [
            'landed',
            'attempted',
        ]

class SignificantStrikesSerialier(serializers.HyperlinkedModelSerializer):
    landed = serializers.IntegerField(source='sig_str_landed', read_only=True)
    attempted = serializers.IntegerField(source='sig_str_attempted', read_only=True)
    class Meta:
        model = FighterCareerStats
        fields = [
            'landed',
            'attempted',
        ]

class HeadStrikesSerialier(serializers.HyperlinkedModelSerializer):
    landed = serializers.IntegerField(source='head_str_landed', read_only=True)
    attempted = serializers.IntegerField(source='head_str_attempted', read_only=True)
    class Meta:
        model = FighterCareerStats
        fields = [
            'landed',
            'attempted',
        ]

class BodyStrikesSerializer(serializers.HyperlinkedModelSerializer):
    landed = serializers.IntegerField(source='body_str_landed', read_only=True)
    attempted = serializers.IntegerField(source='body_str_attempted', read_only=True)

    class Meta:
        model = FighterCareerStats
        fields = ['landed', 'attempted']

class LegStrikesSerializer(serializers.HyperlinkedModelSerializer):
    landed = serializers.IntegerField(source='leg_str_landed', read_only=True)
    attempted = serializers.IntegerField(source='leg_str_attempted', read_only=True)

    class Meta:
        model = FighterCareerStats
        fields = ['landed', 'attempted']

class DistanceStrikesSerializer(serializers.HyperlinkedModelSerializer):
    landed = serializers.IntegerField(source='distance_str_landed', read_only=True)
    attempted = serializers.IntegerField(source='distance_str_attempted', read_only=True)

    class Meta:
        model = FighterCareerStats
        fields = ['landed', 'attempted']

class ClinchStrikesSerializer(serializers.HyperlinkedModelSerializer):
    landed = serializers.IntegerField(source='clinch_str_landed', read_only=True)
    attempted = serializers.IntegerField(source='clinch_str_attempted', read_only=True)

    class Meta:
        model = FighterCareerStats
        fields = ['landed', 'attempted']

class GroundStrikesSerializer(serializers.HyperlinkedModelSerializer):
    landed = serializers.IntegerField(source='ground_str_landed', read_only=True)
    attempted = serializers.IntegerField(source='ground_str_attempted', read_only=True)

    class Meta:
        model = FighterCareerStats
        fields = ['landed', 'attempted']

class StrikingSerializer(serializers.HyperlinkedModelSerializer):
    total = TotalStrikesSerialier(source='*', read_only=True)
    significant = SignificantStrikesSerialier(source='*', read_only=True)
    distance = DistanceStrikesSerializer(source='*', read_only=True)
    head = HeadStrikesSerialier(source='*', read_only=True)
    body = BodyStrikesSerializer(source='*', read_only=True)
    leg = LegStrikesSerializer(source='*', read_only=True)
    clinch = ClinchStrikesSerializer(source='*', read_only=True)
    ground = GroundStrikesSerializer(source='*', read_only=True)
    class Meta:
        model = FighterCareerStats
        fields = [
            'total',
            'significant',
            'distance',
            'head',
            'body',
            'leg',
            'clinch',
            'ground',
        ]

class TakedownSerializer(serializers.HyperlinkedModelSerializer):
    attempted = serializers.IntegerField(source='td_attempted', read_only=True)
    landed = serializers.IntegerField(source='td_landed', read_only=True)
    class Meta:
        model = FighterCareerStats
        fields = [
            'attempted',
            'landed',
        ]
    
class GrapplingSerializer(serializers.HyperlinkedModelSerializer):
    takedowns = TakedownSerializer(source='*', read_only=True)
    class Meta:
        model = FighterCareerStats
        fields = [
            'takedowns',
            'sub_att',
            'reversals',
            'ctrl_time',
        ]

class OpponentSignificantStrikesSerializer(serializers.HyperlinkedModelSerializer):
    landed = serializers.IntegerField(source='sig_str_landed_opp', read_only=True)
    attempted = serializers.IntegerField(source='sig_str_attempted_opp', read_only=True)

    class Meta:
        model = FighterCareerStats
        fields = ['landed', 'attempted']

class OpponentStrikingSerializer(serializers.HyperlinkedModelSerializer):
    significant = OpponentSignificantStrikesSerializer(source='*', read_only=True)

    class Meta:
        model = FighterCareerStats
        fields = ['significant']

class OpponentTakedownSerializer(serializers.HyperlinkedModelSerializer):
    landed = serializers.IntegerField(source='td_landed_opp', read_only=True)
    attempted = serializers.IntegerField(source='td_attempted_opp', read_only=True)

    class Meta:
        model = FighterCareerStats
        fields = ['landed', 'attempted']

class OpponentGrapplingSerializer(serializers.HyperlinkedModelSerializer):
    takedowns = OpponentTakedownSerializer(source='*', read_only=True)
    ctrl_time = serializers.IntegerField(source='ctrl_time_opp', read_only=True)
    class Meta:
        model = FighterCareerStats
        fields = [
            'takedowns',
            'ctrl_time',
        ]


class OpponentStatsSerializer(serializers.HyperlinkedModelSerializer):
    striking = OpponentStrikingSerializer(source='*', read_only=True)
    grappling = OpponentGrapplingSerializer(source='*', read_only=True)
    class Meta:
        model = FighterCareerStats
        fields = [
            'striking',
            'grappling',
        ]

class FighterCareerStatsSerializer(serializers.HyperlinkedModelSerializer):
    fighter = FighterSerializer(many=False, read_only=True)
    striking = StrikingSerializer(source='*', read_only=True)
    grappling = GrapplingSerializer(source='*', read_only=True)
    opponent = OpponentStatsSerializer(source='*', read_only=True)
    class Meta:
        model = FighterCareerStats
        fields = [
            'fighter',
            'total_fights',
            'striking',
            'grappling',
            'total_fight_time',

            # Opponent Stats
            'opponent',
        ]