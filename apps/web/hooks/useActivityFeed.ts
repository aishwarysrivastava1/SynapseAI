"use client";

import { useState, useEffect } from "react";
import { collection, query, orderBy, limit, onSnapshot } from "firebase/firestore";
import { db } from "../lib/firebase";
import { ActivityEvent } from "../lib/types";

export function useActivityFeed(maxEvents: number = 20) {
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const q = query(
      collection(db, "activity"),
      orderBy("timestamp", "desc"),
      limit(maxEvents)
    );

    const unsubscribe = onSnapshot(q, (snapshot) => {
      const data: ActivityEvent[] = [];
      snapshot.forEach((doc) => {
        data.push({ id: doc.id, ...doc.data() } as ActivityEvent);
      });
      setEvents(data);
      setLoading(false);
    }, (error) => {
      console.error("useActivityFeed error:", error);
      setLoading(false);
    });

    return () => unsubscribe();
  }, [maxEvents]);

  return { events, loading };
}
