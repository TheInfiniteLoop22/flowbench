"use client";

import dynamic from "next/dynamic";

const StationMap = dynamic(() => import("@/components/StationMap").then((m) => m.StationMap), {
  ssr: false,
});

export function StationMapClient() {
  return <StationMap />;
}
