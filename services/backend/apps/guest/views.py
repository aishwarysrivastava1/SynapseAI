from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from apps.guest.models import Guest, GuestData


class GuestSessionView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        guest_id = getattr(request, "guest_id", None)
        return Response({"guest_id": guest_id, "is_guest": True})


class GuestDataView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        guest_id = getattr(request, "guest_id", None)
        if not guest_id:
            return Response({"data": {}})
        obj = GuestData.objects.filter(guest_id=guest_id).first()
        return Response({"data": obj.data if obj else {}})

    def post(self, request):
        guest_id = getattr(request, "guest_id", None)
        if not guest_id:
            return Response({"detail": "No guest session"}, status=400)
        data = request.data.get("data", {})
        obj, _ = GuestData.objects.update_or_create(
            guest_id=guest_id, defaults={"data": data}
        )
        return Response({"message": "Guest data saved"})
