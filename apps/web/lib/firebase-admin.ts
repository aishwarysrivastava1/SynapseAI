import * as admin from 'firebase-admin';

if (!admin.apps.length) {
  try {
    const saJson = process.env.FIREBASE_SERVICE_ACCOUNT_JSON;
    if (saJson) {
      admin.initializeApp({
        credential: admin.credential.cert(JSON.parse(saJson)),
        storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET
      });
    } else {
      admin.initializeApp({
        projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
        storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET
      });
    }
  } catch (error) {
    console.error('Firebase admin initialization error', error);
  }
}

// Guard against calling these when no app was successfully initialised
const app = admin.apps[0] ?? null;

export const adminDb = app ? admin.firestore() : null as unknown as admin.firestore.Firestore;
export const adminStorage = app ? admin.storage() : null as unknown as admin.storage.Storage;
export const FieldValue = admin.firestore.FieldValue;
