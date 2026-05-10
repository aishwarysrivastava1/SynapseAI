import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)


class SimulationRunView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        try:
            from engine.simulator import run_simulation
            params = request.data.get("params", {})
            result = run_simulation(**params)
            return Response({"result": result})
        except Exception as e:
            logger.error("Simulation failed: %s", e)
            return Response({"detail": str(e)}, status=500)
