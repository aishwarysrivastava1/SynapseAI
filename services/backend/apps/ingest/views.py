import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from asgiref.sync import async_to_sync
from django.http import HttpResponse

logger = logging.getLogger(__name__)


class IngestTextView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        from services.gemini_service import extract_entities
        text = request.data.get("text", "")
        if not text:
            return Response({"detail": "text required"}, status=400)
        try:
            result = async_to_sync(extract_entities)(text)
            return Response({"entities": result})
        except Exception as e:
            logger.error("ingest_text failed: %s", e)
            return Response({"detail": str(e)}, status=500)


class IngestDocumentView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response({"detail": "file required"}, status=400)
        try:
            content = file.read().decode("utf-8", errors="replace")
            from services.gemini_service import extract_entities
            result = async_to_sync(extract_entities)(content)
            return Response({"entities": result, "filename": file.name})
        except Exception as e:
            logger.error("ingest_document failed: %s", e)
            return Response({"detail": str(e)}, status=500)


class IngestVoiceView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        return Response({"message": "Voice ingest received"})


class VoiceTwiMLView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        from twilio.twiml.voice_response import VoiceResponse
        response = VoiceResponse()
        response.say("Welcome to Sanchaalan Saathi. Please leave your message after the beep.")
        response.record(timeout=10, transcribe=True, action="/api/voice/recording")
        return HttpResponse(str(response), content_type="application/xml")


class VoiceRecordingView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        transcription = request.data.get("TranscriptionText", "")
        recording_url = request.data.get("RecordingUrl", "")
        if transcription:
            import threading
            def _process():
                try:
                    from services.gemini_service import extract_entities
                    async_to_sync(extract_entities)(transcription)
                except Exception as e:
                    logger.warning("Voice transcription processing failed: %s", e)
            threading.Thread(target=_process, daemon=True).start()
        return HttpResponse("<?xml version='1.0' encoding='UTF-8'?><Response/>", content_type="application/xml")
