from django.contrib import admin
from django.contrib import admin
from .models import (
    Fighters,
    Events,
    Fights,
    FightStats,
    RoundStats,
    FighterCareerStats,
    RoundScore,
    FightScore,
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