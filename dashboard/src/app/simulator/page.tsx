import type { Metadata } from "next";
import { Suspense } from "react";
import { SimulatorClient } from "@/components/SimulatorClient";

export const metadata: Metadata = { title: "Rebalancing simulator" };

export default function SimulatorPage() {
  return (
    <Suspense>
      <SimulatorClient />
    </Suspense>
  );
}
