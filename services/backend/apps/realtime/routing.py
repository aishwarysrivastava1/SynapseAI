from django.urls import path
from .consumers import RealtimeConsumer

websocket_urlpatterns = [
    path("api/realtime/ws", RealtimeConsumer.as_asgi()),
]
