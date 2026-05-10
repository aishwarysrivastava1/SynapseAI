import os
from django.core.asgi import get_asgi_application

_env = os.environ.get("DEPLOYMENT_ENV", "development").lower()
_settings_map = {
    "production": "config.settings.production",
    "staging": "config.settings.staging",
    "development": "config.settings.development",
}
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    _settings_map.get(_env, "config.settings.development"),
)

django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from apps.realtime.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": URLRouter(websocket_urlpatterns),
})
