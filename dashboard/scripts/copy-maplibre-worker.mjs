// maplibre-gl v6 loads its web worker from a separate .mjs file that
// Turbopack does not emit, so tiles never load. Serve it from /public and
// point setWorkerUrl at it (see src/components/StationMap.tsx).
import { cpSync, mkdirSync } from "node:fs";

const src = "node_modules/maplibre-gl/dist";
const dest = "public/maplibre";
mkdirSync(dest, { recursive: true });
for (const f of ["maplibre-gl-worker.mjs", "maplibre-gl-shared.mjs"]) {
  cpSync(`${src}/${f}`, `${dest}/${f}`);
}
