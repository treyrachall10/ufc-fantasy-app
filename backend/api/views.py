from rest_framework.decorators import api_view
from rest_framework.response import Response

from .serializers import FighterSerializer
from fantasy.models import Fighters

@api_view(['GET'])
def GetFighterProfileViewSet(request):
    fighters = Fighters.objects.all()
    serializer = FighterSerializer(fighters, many=True)
    return Response(serializer.data)