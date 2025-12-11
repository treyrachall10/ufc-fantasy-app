from rest_framework import serializers
from fantasy.models import Fighters, FighterCareerStats

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