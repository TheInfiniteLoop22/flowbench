import { StationMapClient } from "@/components/StationMapClient";

export default function Home() {
  return (
    <div className="h-[calc(100vh-3.5rem)] w-full md:h-screen">
      <StationMapClient />
    </div>
  );
}
