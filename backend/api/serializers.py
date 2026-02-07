'''
    Contains serializers for django views
'''
from rest_framework import serializers
from fantasy.models import DraftOrder, DraftPick, Fighters, FighterCareerStats, Events, Fights, FightScore, FightStats, RoundScore, Team, League, Draft

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
    record = RecordSerializer(source='*', many=False, read_only=True)

    fighter_id = serializers.IntegerField(source='fighter.fighter_id')
    first_name = serializers.CharField(source='fighter.first_name')
    last_name = serializers.CharField(source='fighter.last_name')
    full_name = serializers.CharField(source='fighter.full_name')
    nick_name = serializers.CharField(source='fighter.nick_name')
    stance = serializers.CharField(source='fighter.stance')
    weight = serializers.IntegerField(source='fighter.weight')
    height = serializers.IntegerField(source='fighter.height')
    reach = serializers.IntegerField(source='fighter.reach')
    dob = serializers.DateField(source='fighter.dob')

    class Meta:
        model = FighterCareerStats
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

class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Events
        fields = [
            'event_id',
            'event',
            'date',
            'location',
        ]

class FightSerializer(serializers.ModelSerializer):
    event = EventSerializer(many=False, read_only=True)
    winner = serializers.CharField(source='winner.full_name', read_only=True)
    method = serializers.SerializerMethodField()

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
    
    def get_method(self, obj):
        method = obj.method
        if 'Decision' in method:
            return 'DEC'
        elif method == 'KO/TKO':
            return 'TKO'
        elif method == 'Submission':
            return 'SUB'

class FighterFightSerializer(FightSerializer):
    opponent = serializers.SerializerMethodField()
    result = serializers.SerializerMethodField()

    class Meta(FightSerializer.Meta):
        fields = FightSerializer.Meta.fields + ['opponent'] + ['result']

    def get_opponent(self, obj):
        fighter_id = self.context['fighter_id']
        for fightStat in obj.fightstats_set.all():
            if fightStat.fighter_id != fighter_id:
                return fightStat.fighter.full_name
        return None
    
    def get_result(self, obj):
        fighter_id = self.context['fighter_id']
        if obj.winner is None:
            return 'D'
        if obj.winner_id == fighter_id:
            return 'W'
        return 'L'
            

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
    fighter = FighterSerializer(source='*', many=False, read_only=True)
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

class FantasyFightScoreSerializer(serializers.HyperlinkedModelSerializer):
    date = serializers.DateField(source='fight.event.date', read_only=True)
    bout = serializers.CharField(source='fight.bout', read_only=True)
    class Meta:
        model = FightScore
        fields = [
            'bout',
            'date',
            'fight_total_points',
        ]

class SignificantStrikesFightStatsSerializer(serializers.Serializer):
    landed = serializers.IntegerField(source='sig_str_landed', read_only=True)
    attempted = serializers.IntegerField(source='sig_str_attempted', read_only=True)

class DistanceStrikesFightStatsSerializer(serializers.Serializer):
    landed = serializers.IntegerField(source='distance_str_landed', read_only=True)
    attempted = serializers.IntegerField(source='distance_str_attempted', read_only=True)

class HeadStrikesFightStatsSerializer(serializers.Serializer):
    landed = serializers.IntegerField(source='head_str_landed', read_only=True)
    attempted = serializers.IntegerField(source='head_str_attempted', read_only=True)

class BodyStrikesFightStatsSerializer(serializers.Serializer):
    landed = serializers.IntegerField(source='body_str_landed', read_only=True)
    attempted = serializers.IntegerField(source='body_str_attempted', read_only=True)

class LegStrikesFightStatsSerializer(serializers.Serializer):
    landed = serializers.IntegerField(source='leg_str_landed', read_only=True)
    attempted = serializers.IntegerField(source='leg_str_attempted', read_only=True)

class ClinchStrikesFightStatsSerializer(serializers.Serializer):
    landed = serializers.IntegerField(source='clinch_str_landed', read_only=True)
    attempted = serializers.IntegerField(source='clinch_str_attempted', read_only=True)

class GroundStrikesFightStatsSerializer(serializers.Serializer):
    landed = serializers.IntegerField(source='ground_str_landed', read_only=True)
    attempted = serializers.IntegerField(source='ground_str_attempted', read_only=True)

class TotalStrikesFightStatsSerializer(serializers.Serializer):
    landed = serializers.IntegerField(source='total_str_landed', read_only=True)
    attempted = serializers.IntegerField(source='total_str_attempted', read_only=True)

class FightStatsStrikingSerializer(serializers.Serializer):
    total = TotalStrikesFightStatsSerializer(source='*', read_only=True)
    significant = SignificantStrikesFightStatsSerializer(source='*', read_only=True)
    distance = DistanceStrikesFightStatsSerializer(source='*', read_only=True)
    head = HeadStrikesFightStatsSerializer(source='*', read_only=True)
    body = BodyStrikesFightStatsSerializer(source='*', read_only=True)
    leg = LegStrikesFightStatsSerializer(source='*', read_only=True)
    clinch = ClinchStrikesFightStatsSerializer(source='*', read_only=True)
    ground = GroundStrikesFightStatsSerializer(source='*', read_only=True)
    
class TakedownFightStatsSerializer(serializers.Serializer):
    landed = serializers.IntegerField(source='td_landed', read_only=True)
    attempted = serializers.IntegerField(source='td_attempted', read_only=True)

class FightStatsGrapplingSerializer(serializers.Serializer):
    takedowns = TakedownFightStatsSerializer(source='*', read_only=True)
    sub_att = serializers.IntegerField(read_only=True)
    reversals = serializers.IntegerField(read_only=True)
    ctrl_time = serializers.IntegerField(read_only=True)

class FightStatsSerializer(serializers.Serializer):
    striking = FightStatsStrikingSerializer(source="*", read_only=True)
    grappling = FightStatsGrapplingSerializer(source="*", read_only=True)
    kd = serializers.IntegerField(read_only=True)

class FightScoreSerializer(serializers.HyperlinkedModelSerializer):
    """
        -   Fight level fantasy scores serializer
    """
    class Meta:
        model = FightScore
        fields = [
            'points_win',
            'points_round',
            'points_time',
            'fight_total_points'
        ]

class RoundScoreSerializer(serializers.HyperlinkedModelSerializer):
    """
        -   Individual rounds fantasy scores serializer
    """
    class Meta:
        model = RoundScore
        fields = [
            "points_knockdowns",
            "points_sig_str_landed",
            "points_td_landed",
            "points_sub_att",
            "points_ctrl_time",
            "points_reversals",
            "round_total_points",
        ]

class FantasyBreakdownSerializer(serializers.Serializer):
    """
        -   Totals for all round stats serializer
    """
    points_knockdowns = serializers.FloatField()
    points_sig_str_landed = serializers.FloatField()
    points_td_landed = serializers.FloatField()
    points_sub_att = serializers.FloatField()
    points_ctrl_time = serializers.FloatField()
    points_reversals = serializers.FloatField()
    round_total_points = serializers.FloatField()

class FantasyScoreSerializer(serializers.Serializer):
    """
        -   Serializes fantasy dicts
    """
    round = serializers.DictField(child=RoundScoreSerializer())
    fight = FightScoreSerializer()
    breakdown = FantasyBreakdownSerializer()
    total = serializers.FloatField()

class HeadToHeadStatsSerializer(serializers.Serializer):
    """
        -   Fight stats dashboard serializer
    """
    fighterA = FighterSerializer(read_only=True)
    fighterB = FighterSerializer(read_only=True)
    fighterAFightStats = FightStatsSerializer(read_only=True)
    fighterBFightStats = FightStatsSerializer(read_only=True)
    event = EventSerializer(read_only=True)
    winner = serializers.CharField(source="fight.winner.full_name", read_only=True)
    bout = serializers.CharField(source='fight.bout', read_only=True)
    fighterAFantasy = FantasyScoreSerializer()
    fighterBFantasy = FantasyScoreSerializer()



class UserLeaguesAndTeamsListSerializer(serializers.Serializer):
    """
        -   Serializers league members set to return users leagues and teams information
    """
    league_id = serializers.IntegerField(source="league.id")
    league_name = serializers.CharField(source="league.name")

    team_id = serializers.SerializerMethodField()
    team_name = serializers.SerializerMethodField()
    
    def get_team_id(self, obj):
        print(obj.team_set.all()[0].__dict__)
        team = obj.team_set.all()[0]
        return team.id
    
    def get_team_name(self, obj):
        team = obj.team_set.all()[0]
        return team.name
    class Meta:
        fields = [
            "league_id",
            "league_name",
            "team_id",
            "team_name"
        ]

class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = [
            'id',
            'owner',
            'name',
            'created_at'
        ]

class LeagueSerializer(serializers.ModelSerializer):
    class Meta:
        model = League
        fields = [
            "id",
            "name",
            "status",
            "capacity",
            "join_key",
            "created_at",
            "creator"
        ]

class DraftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Draft
        fields = [
            "id",
            "status",
            "draft_date"
        ]

class TeamListFighterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Fighters
        fields = [
            'fighter_id',
            'full_name',
            'weight',
        ]

class TeamListFantasyScoreSerializer(serializers.Serializer):
    last_fight_points = serializers.FloatField(read_only=True)
    average_points = serializers.FloatField(read_only=True)

class DraftOrderSerializer(serializers.ModelSerializer):
    team = TeamSerializer(many=False, read_only=True)
    user = serializers.CharField(source='team.owner.owner.username', read_only=True)

    class Meta:
        model = DraftOrder
        fields = [
            'pick_num',
            'team',
            'user',
        ]

class DraftableFighterSerializer(serializers.ModelSerializer):
    fighter = TeamListFighterSerializer(source='*', many=False, read_only=True)
    fantasy_score = TeamListFantasyScoreSerializer(source='*', many=False, read_only=True)

    class Meta:
        model = FighterCareerStats
        fields = [
            'fighter',
            'fantasy_score',
        ]

class DraftPickHistorySerializer(serializers.ModelSerializer):
    team = TeamSerializer(many=False, read_only=True)
    fighter = TeamListFighterSerializer(many=False, read_only=True)
    
    class Meta:
        model = DraftPick
        fields = [
            'pick_num',
            'team',
            'fighter',
        ]