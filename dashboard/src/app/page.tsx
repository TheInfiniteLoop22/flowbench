import type { Metadata } from "next";
import { StationMapClient } from "@/components/StationMapClient";

export const metadata: Metadata = { title: "Network map" };

export default function Home() {
  return (
    <div className="h-[calc(100dvh-7.5rem)] w-full md:h-screen">
      <StationMapClient />
    </div>
  );
}
