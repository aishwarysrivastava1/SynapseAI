import {
  signInWithPopup,
  GoogleAuthProvider,
  signOut,
  onAuthStateChanged,
  getIdToken,
  type User,
  type Unsubscribe,
} from "firebase/auth";
import { auth } from "./firebase";

export async function signInWithGoogle(): Promise<User> {
  if (!auth) throw new Error("Firebase is not configured. Add NEXT_PUBLIC_FIREBASE_* env vars.");
  const result = await signInWithPopup(auth, new GoogleAuthProvider());
  return result.user;
}

export async function logoutUser(): Promise<void> {
  if (auth) await signOut(auth);
  try {
    localStorage.removeItem("ngo_token");
    document.cookie = "ngo_token=; path=/; max-age=0";
  } catch {
    // SSR — no localStorage
  }
}

export function observeAuthState(cb: (user: User | null) => void): Unsubscribe {
  if (!auth) return () => {};
  return onAuthStateChanged(auth, cb);
}

export async function getCurrentIdToken(): Promise<string | null> {
  if (!auth?.currentUser) return null;
  try {
    return await getIdToken(auth.currentUser);
  } catch {
    return null;
  }
}
