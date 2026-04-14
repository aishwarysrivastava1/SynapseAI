"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { auth, db } from "./firebase";
import { onAuthStateChanged, User, GoogleAuthProvider, signInWithPopup, signOut as fbSignOut } from "firebase/auth";
import { doc, getDoc, setDoc } from "firebase/firestore";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  signInWithGoogle: () => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  signInWithGoogle: async () => {},
  signOut: async () => {},
});

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (currentUser) => {
      setUser(currentUser);
      
      if (currentUser) {
        // Check if volunteer doc exists
        const volRef = doc(db, "volunteers", currentUser.uid);
        const volSnap = await getDoc(volRef);
        
        if (!volSnap.exists()) {
          // Auto-create profile
          await setDoc(volRef, {
            uid: currentUser.uid,
            name: currentUser.displayName || "New Volunteer",
            phone: currentUser.phoneNumber || "",
            skills: [],
            location: { lat: 28.6139, lng: 77.2090 }, // Default Delhi
            reputationScore: 100,
            totalXP: 0,
            totalTasksCompleted: 0,
            currentActiveTasks: 0,
            availabilityStatus: "ACTIVE"
          });
        }
      }
      setLoading(false);
    });

    return unsubscribe;
  }, []);

  const signInWithGoogle = async () => {
    const provider = new GoogleAuthProvider();
    await signInWithPopup(auth, provider);
  };

  const signOut = async () => {
    await fbSignOut(auth);
  };

  return (
    <AuthContext.Provider value={{ user, loading, signInWithGoogle, signOut }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
