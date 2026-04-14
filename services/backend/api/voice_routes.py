from fastapi import APIRouter, Request, BackgroundTasks, HTTPException, Header, Depends
from fastapi.responses import HTMLResponse, Response
from twilio.twiml.voice_response import VoiceResponse
from twilio.request_validator import RequestValidator
from services.gemini_service import extract_entities, extract_entities_from_audio
import os
import io
import urllib.request
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
validator = RequestValidator(TWILIO_AUTH_TOKEN)

async def verify_twilio_signature(request: Request, x_twilio_signature: str = Header(None)):
    if not TWILIO_AUTH_TOKEN:
        logger.warning("TWILIO_AUTH_TOKEN not set, skipping strict signature validation.")
        return True # For hackathon demo ease if token not dropped in .env
        
    url = str(request.url)
    form_data = await request.form()
    
    # Twilio signature check requires standard dict, multi-dicts need flattening
    params = {k: v for k, v in form_data.items()}
    
    if not validator.validate(url, params, x_twilio_signature or ""):
        logger.error("Twilio signature validation failed. Potential spoofing attempt.")
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")
    return True

async def process_voice_recording(recording_url: str):
    logger.info(f"Processing voice recording: {recording_url}")
    try:
        req = urllib.request.Request(recording_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            audio_data = response.read()

        extraction = await extract_entities_from_audio(audio_data, "audio/wav")
        # In this hackathon build, write graph directly, but typically you'd run through the writer logic
        # if the extraction contains nodes/edges.
        from services.graph_writer import write_extraction_to_graph
        await write_extraction_to_graph(extraction)
        logger.info("Voice report ingested via Gemini successfully")

    except Exception as e:
        logger.error(f"Failed to process voice recording: {e}")

@router.post("/twiml", dependencies=[Depends(verify_twilio_signature)])
async def twilio_webhook(request: Request):
    """Endpoint for Twilio Phone Number Webhook."""
    response = VoiceResponse()
    response.say("Welcome to SYNAPSE AI Emergency Dispatch. Please state your location, your need, and any required skills clearly after the beep. Press any key when finished.", language="hi-IN", voice="Polly.Aditi")
    
    response.record(max_length=60, action="/api/voice/recording", play_beep=True)
    
    response.say("No input was received. Goodbye.", language="hi-IN", voice="Polly.Aditi")
    
    return Response(content=str(response), media_type="application/xml")

@router.post("/recording", dependencies=[Depends(verify_twilio_signature)])
async def twilio_recording_callback(request: Request, background_tasks: BackgroundTasks):
    """Webhook triggered by Twilio after recording finishes."""
    form_data = await request.form()
    recording_url = form_data.get("RecordingUrl")
    
    if recording_url:
         # Twilio stores files as .wav usually but the URL points to it
         background_tasks.add_task(process_voice_recording, recording_url + ".wav")
         
    response = VoiceResponse()
    response.say("Your report has been received and logged into the SYNAPSE system. Help will be coordinated shortly. Goodbye.", language="hi-IN", voice="Polly.Aditi")
    
    return Response(content=str(response), media_type="application/xml")
