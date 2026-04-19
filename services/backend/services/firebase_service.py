import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
import base64
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def _parse_service_account_json(raw: str) -> dict | None:
    """
    Robustly parse FIREBASE_SERVICE_ACCOUNT_JSON from Render / Railway / Vercel.

    Platforms differ in how they store the value:
      1. Valid JSON pasted directly                → json.loads() works
      2. JSON with double-escaped newlines         → replace \\n → \n in private_key
      3. Base64-encoded JSON                       → base64 decode first
      4. JSON wrapped in single quotes             → strip outer quotes

    Returns the parsed dict or None on failure.
    """
    candidates = [raw]

    # Strip surrounding single or double quotes added by some platforms
    stripped = raw.strip().strip("'\"")
    if stripped != raw:
        candidates.append(stripped)

    # Try base64 decode
    try:
        decoded = base64.b64decode(raw).decode("utf-8")
        candidates.append(decoded)
    except Exception:
        pass

    for candidate in candidates:
        # Attempt 1: direct parse
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

        # Attempt 2: fix double-escaped newlines in private_key
        # Render sometimes stores \n as the two characters \ and n
        try:
            fixed = candidate.replace("\\\\n", "\\n")
            result = json.loads(fixed)
            return result
        except json.JSONDecodeError:
            pass

        # Attempt 3: replace literal \n outside JSON string context
        # (env var pasted with real newlines replaced by spaces)
        try:
            fixed = candidate.replace("\r\n", "\\n").replace("\r", "\\n")
            result = json.loads(fixed)
            return result
        except json.JSONDecodeError:
            pass

    return None


class FirebaseService:
    def __init__(self):
        self.db = None
        self.initialize_firebase()

    def initialize_firebase(self):
        try:
            if not firebase_admin._apps:
                service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
                if not service_account_json:
                    logger.error("FIREBASE_SERVICE_ACCOUNT_JSON not found in environment variables.")
                    return
                cred_dict = _parse_service_account_json(service_account_json)
                if cred_dict is None:
                    logger.error(
                        "Could not parse FIREBASE_SERVICE_ACCOUNT_JSON. "
                        "Paste the raw JSON value in Render — do not add extra quotes. "
                        "Alternatively, base64-encode the JSON and paste the encoded string."
                    )
                    return
                try:
                    cred = credentials.Certificate(cred_dict)
                    firebase_admin.initialize_app(cred)
                    logger.info(f"Firebase Admin initialized for project: {cred_dict.get('project_id')}")
                except Exception as e:
                    logger.error(f"Firebase initialization error: {e}")
                    return

            self.db = firestore.client()
        except Exception as e:
            logger.error(f"Error initializing Firestore: {e}")

    # ── Notifications ─────────────────────────────────────────────────────────

    def add_notification(self, title: str, message: str, n_type: str = "INFO"):
        """Adds a notification to the Firestore 'notifications' collection."""
        if not self.db:
            return
        try:
            self.db.collection("notifications").add({
                "title": title,
                "message": message,
                "type": n_type,
                "timestamp": datetime.utcnow(),
                "read": False
            })
            logger.info(f"Notification added: {title}")
        except Exception as e:
            logger.error(f"Failed to add notification: {e}")

    # ── Needs (real-time sync) ─────────────────────────────────────────────────

    def sync_need_to_firestore(self, need_id: str, need_data: dict):
        """Writes a Need from Neo4j to Firestore so the frontend gets real-time updates."""
        if not self.db:
            return
        try:
            lat = need_data.get("lat") or 28.6139
            lng = need_data.get("lng") or 77.2090
            self.db.collection("needs").document(need_id).set({
                "id": need_id,
                "type": need_data.get("type", "unknown"),
                "sub_type": need_data.get("sub_type", ""),
                "description": need_data.get("description", ""),
                "urgency_score": float(need_data.get("urgency_score", 0.5)),
                "population_affected": int(need_data.get("population_affected", 1)),
                "status": need_data.get("status", "PENDING"),
                "location": {
                    "lat": float(lat),
                    "lng": float(lng),
                    "name": need_data.get("location_name", "Unknown Area"),
                },
                "reported_at": datetime.utcnow(),
                "tasks_spawned": 0,
            })
            logger.info(f"Need synced to Firestore: {need_id}")
        except Exception as e:
            logger.error(f"Failed to sync need to Firestore: {e}")

    def update_need_status(self, need_id: str, status: str):
        """Updates the status of a need in Firestore."""
        if not self.db:
            return
        try:
            self.db.collection("needs").document(need_id).update({
                "status": status,
                "updated_at": datetime.utcnow(),
            })
        except Exception as e:
            logger.error(f"Failed to update need status in Firestore: {e}")

    # ── Tasks ──────────────────────────────────────────────────────────────────

    def create_task_from_need(self, need_id: str, need_data: dict):
        """Creates a corresponding task in Firestore when a need is created."""
        if not self.db:
            return
        try:
            lat = need_data.get("lat") or 28.6139
            lng = need_data.get("lng") or 77.2090
            self.db.collection("tasks").document(need_id).set({
                "neoNeedId": need_id,
                "title": f"Need: {need_data.get('type', 'Unknown').upper()}",
                "description": need_data.get("description", ""),
                "status": "OPEN",
                "createdAt": datetime.utcnow(),
                "urgency": float(need_data.get("urgency_score", 0.5)),
                "location": {
                    "lat": float(lat),
                    "lng": float(lng),
                    "name": need_data.get("location_name", "Unknown Area"),
                },
                "xpReward": int(need_data.get("urgency_score", 0.5) * 1000),
            })
            logger.info(f"Task created in Firestore for need: {need_id}")
        except Exception as e:
            logger.error(f"Failed to create task in Firestore: {e}")

    # ── Activity feed ──────────────────────────────────────────────────────────

    def log_activity(self, event_type: str, title: str, description: str, metadata: dict = None):
        """Writes a real-time activity event to the 'activity' Firestore collection."""
        if not self.db:
            return
        try:
            self.db.collection("activity").add({
                "type": event_type,
                "title": title,
                "description": description,
                "timestamp": datetime.utcnow(),
                "metadata": metadata or {},
            })
        except Exception as e:
            logger.error(f"Failed to log activity: {e}")

firebase_service = FirebaseService()
