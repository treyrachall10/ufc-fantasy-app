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