from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny


class RealtimeStatusView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        from services.realtime_events import realtime_bus
        return Response({
            "status": "ok",
            "connected_ngo_channels": len(realtime_bus._ngo_channels),
        })
