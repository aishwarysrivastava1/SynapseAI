"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function LegacyTaskRedirect() {
  const router = useRouter();
  useEffect(() => { router.replace("/vol/dashboard"); }, [router]);
  return null;
}
