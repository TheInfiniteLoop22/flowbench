import { StationDetail } from "@/components/StationDetail";

export default async function StationPage({ params }: PageProps<"/stations/[id]">) {
  const { id } = await params;
  return <StationDetail stationId={decodeURIComponent(id)} />;
}
