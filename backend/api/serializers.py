'''
    Contains serializers for django views
'''
from rest_framework import serializers
from fantasy.models import Fighters, FighterCareerStats, Events, Fights

class RecordSerializer(serializers.HyperlinkedModelSerializer):
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

class FighterCareerStatsSerializer(serializers.ModelSerializer):
    fighter = FighterSerializer(many=False, read_only=True)

    class Meta:
        model = FighterCareerStats
        fields = [
            'fighter',
            'total_fights',

            'ko_tko',
            'tko_doctor_stoppages',
            'submissions',

            'unanimous_decisions',
            'split_decisions',
            'majority_decisions',
            'dq',

            'sig_str_landed',
            'sig_str_attempted',
            'total_str_landed',
            'total_str_attempted',

            'td_landed',
            'td_attempted',

            'sub_att',
            'ctrl_time',
            'reversals',

            'head_str_landed',
            'head_str_attempted',
            'body_str_landed',
            'body_str_attempted',
            'leg_str_landed',
            'leg_str_attempted',

            'distance_str_landed',
            'distance_str_attempted',
            'clinch_str_landed',
            'clinch_str_attempted',
            'ground_str_landed',
            'ground_str_attempted',
        ]