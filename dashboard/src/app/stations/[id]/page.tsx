import type { Metadata } from "next";
import { StationDetail } from "@/components/StationDetail";

export const metadata: Metadata = { title: "Station demand" };

export default async function StationPage({ params }: PageProps<"/stations/[id]">) {
  const { id } = await params;
  return <StationDetail stationId={decodeURIComponent(id)} />;
}
