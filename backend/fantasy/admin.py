from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from accounts.models import User
from .models import (
    Fighters,
    Events,
    Fights,
    FightStats,
    RoundStats,
    FighterCareerStats,
    RoundScore,
    FightScore,
    League, 
    Draft, 
    LeagueMember, 
    Team, 
    Roster, 
    DraftPick, 
    DraftOrder
)

# Register your models here.
admin.site.register(Fighters)
admin.site.register(Events)
admin.site.register(Fights)
admin.site.register(FightStats)
admin.site.register(RoundStats)
admin.site.register(FighterCareerStats)
admin.site.register(RoundScore)
admin.site.register(FightScore)
admin.site.register(User, UserAdmin)
admin.site.register(League)
admin.site.register(Draft)
admin.site.register(LeagueMember)
admin.site.register(Team)
admin.site.register(Roster)
admin.site.register(DraftPick)
admin.site.register(DraftOrder)