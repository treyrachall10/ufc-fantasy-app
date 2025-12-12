'''
    Contains views for API
'''
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .serializers import *
from fantasy.models import Fighters, Events

@api_view(['GET'])
def GetFighterProfileViewSet(request):
    fighters = Fighters.objects.all()
    serializer = FighterSerializer(fighters, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def GetEventViewSet(request):
    events = Events.objects.all()
    serializer = EventSerializer(events, many=True)
    return Response(serializer.data)