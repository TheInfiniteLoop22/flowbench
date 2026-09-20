import { Suspense } from "react";
import { SimulatorClient } from "@/components/SimulatorClient";

export default function SimulatorPage() {
  return (
    <Suspense>
      <SimulatorClient />
    </Suspense>
  );
}
