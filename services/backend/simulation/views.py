import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

logger = logging.getLogger(__name__)

VALID_STRATEGIES = {"skill_first", "proximity_first", "random"}


class SimulationRunView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        from asgiref.sync import async_to_sync
        from engine.simulator import run_simulation_scenario

        params = request.data.get("params", {})
        if not isinstance(params, dict):
            return Response({"detail": "params must be a JSON object"}, status=400)

        num_steps = params.get("num_steps", 50)
        strategy = params.get("strategy", "skill_first")

        try:
            num_steps = int(num_steps)
            if not (1 <= num_steps <= 200):
                return Response({"detail": "num_steps must be between 1 and 200"}, status=400)
        except (TypeError, ValueError):
            return Response({"detail": "num_steps must be an integer"}, status=400)

        if strategy not in VALID_STRATEGIES:
            return Response(
                {"detail": f"strategy must be one of: {', '.join(sorted(VALID_STRATEGIES))}"},
                status=400,
            )

        try:
            result = async_to_sync(run_simulation_scenario)(
                num_steps=num_steps, strategy=strategy
            )
            return Response({"result": result})
        except Exception as e:
            logger.error("Simulation failed: %s", e)
            return Response({"detail": str(e)}, status=500)
