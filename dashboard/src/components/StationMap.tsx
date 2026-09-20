"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import MaplibreMap, {
  Layer,
  Source,
  Popup,
  NavigationControl,
  type MapLayerMouseEvent,
} from "react-map-gl/maplibre";
import { setWorkerUrl } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { api, type City, type Station, type StationImbalance } from "@/lib/api";

setWorkerUrl("/maplibre/maplibre-gl-worker.mjs");

const BASEMAP_STYLE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";

const CITY_CENTER: Record<City, { longitude: number; latitude: number; zoom: number }> = {
  new_york: { longitude: -73.97, latitude: 40.735, zoom: 11.5 },
  chicago: { longitude: -87.66, latitude: 41.88, zoom: 11 },
};

const TYPOLOGY_COLOR: Record<string, string> = {
  "commuter-hub": "#4f8cf2",
  leisure: "#f2a63a",
  mixed: "#5b6473",
};

type Mode = "imbalance" | "typology";
type Selected = {
  station_id: string;
  name: string;
  net_balance: number | null;
  typology: string | null;
  lat: number;
  lon: number;
};

export function StationMap() {
  const searchParams = useSearchParams();
  const city = (searchParams.get("city") === "chicago" ? "chicago" : "new_york") as City;
  const [mode, setMode] = useState<Mode>("imbalance");
  const [hour, setHour] = useState(8);
  const [stations, setStations] = useState<Station[]>([]);
  const [imbalance, setImbalance] = useState<StationImbalance[]>([]);
  const [selected, setSelected] = useState<Selected | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setSelected(null);
    api.stations(city).then(setStations).catch(() => setStations([]));
  }, [city]);

  useEffect(() => {
    if (mode !== "imbalance") return;
    setLoading(true);
    api
      .networkImbalance(hour, city)
      .then((rows) => {
        setImbalance(rows);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [hour, mode, city]);

  const geojson = useMemo(() => {
    if (mode === "typology") {
      return {
        type: "FeatureCollection" as const,
        features: stations
          .filter((s) => s.typology)
          .map((s) => ({
            type: "Feature" as const,
            geometry: { type: "Point" as const, coordinates: [s.lon, s.lat] },
            properties: { station_id: s.station_id, name: s.name, typology: s.typology, net_balance: null },
          })),
      };
    }
    const byId = new Map(imbalance.map((r) => [r.station_id, r.avg_net_balance]));
    return {
      type: "FeatureCollection" as const,
      features: stations
        .filter((s) => byId.has(s.station_id))
        .map((s) => ({
          type: "Feature" as const,
          geometry: { type: "Point" as const, coordinates: [s.lon, s.lat] },
          properties: {
            station_id: s.station_id,
            name: s.name,
            net_balance: byId.get(s.station_id) ?? 0,
            typology: s.typology,
          },
        })),
    };
  }, [stations, imbalance, mode]);

  const paint =
    mode === "typology"
      ? {
          "circle-radius": 5,
          "circle-color": [
            "match",
            ["get", "typology"],
            "commuter-hub", TYPOLOGY_COLOR["commuter-hub"],
            "leisure", TYPOLOGY_COLOR.leisure,
            TYPOLOGY_COLOR.mixed,
          ] as unknown as string,
          "circle-stroke-width": 1,
          "circle-stroke-color": "#0b0f14",
          "circle-opacity": 0.85,
        }
      : {
          "circle-radius": ["interpolate", ["linear"], ["abs", ["get", "net_balance"]], 0, 3, 40, 11] as unknown as number,
          "circle-color": [
            "interpolate",
            ["linear"],
            ["get", "net_balance"],
            -40, "#f2645a",
            0, "#5b6473",
            40, "#35d0ba",
          ] as unknown as string,
          "circle-stroke-width": 1,
          "circle-stroke-color": "#0b0f14",
          "circle-opacity": 0.85,
        };

  return (
    <div className="relative h-full w-full">
      <MaplibreMap
        key={city}
        initialViewState={CITY_CENTER[city]}
        mapStyle={BASEMAP_STYLE}
        style={{ width: "100%", height: "100%" }}
        interactiveLayerIds={["stations"]}
        onClick={(e: MapLayerMouseEvent) => {
          const f = e.features?.[0];
          if (!f) return;
          const [lon, lat] = (f.geometry as GeoJSON.Point).coordinates;
          setSelected({
            station_id: f.properties!.station_id,
            name: f.properties!.name,
            net_balance: f.properties!.net_balance,
            typology: f.properties!.typology,
            lat,
            lon,
          });
        }}
      >
        <NavigationControl position="top-right" />
        <Source id="stations" type="geojson" data={geojson}>
          {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
          <Layer id="stations" type="circle" paint={paint as any} />
        </Source>
        {selected && (
          <Popup
            longitude={selected.lon}
            latitude={selected.lat}
            onClose={() => setSelected(null)}
            closeOnClick={false}
            offset={12}
          >
            <div className="min-w-45 p-1 text-sm">
              <div className="font-medium">{selected.name}</div>
              {mode === "imbalance" ? (
                <div className="mt-1 text-xs text-muted">
                  Net balance @ {String(hour).padStart(2, "0")}:00:{" "}
                  <span className={(selected.net_balance ?? 0) < 0 ? "text-danger" : "text-accent"}>
                    {(selected.net_balance ?? 0) > 0 ? "+" : ""}
                    {(selected.net_balance ?? 0).toFixed(1)}
                  </span>
                </div>
              ) : (
                <div className="mt-1 text-xs text-muted">
                  Typology: <span className="text-foreground">{selected.typology ?? "unclassified"}</span>
                </div>
              )}
              <Link
                href={`/stations/${encodeURIComponent(selected.station_id)}`}
                className="mt-2 inline-block text-xs font-medium text-accent hover:underline"
              >
                View demand curve &rarr;
              </Link>
            </div>
          </Popup>
        )}
      </MaplibreMap>

      <div className="pointer-events-none absolute inset-x-0 top-0 flex flex-col items-center gap-2 p-4">
        <div className="pointer-events-auto flex gap-1 rounded-xl border border-border bg-surface/90 p-1 shadow-lg backdrop-blur">
          {(["imbalance", "typology"] as Mode[]).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium capitalize transition-colors ${
                mode === m ? "bg-accent-soft text-accent" : "text-muted hover:text-foreground"
              }`}
            >
              {m}
            </button>
          ))}
        </div>

        {mode === "imbalance" && (
          <div className="pointer-events-auto flex items-center gap-4 rounded-2xl border border-border bg-surface/90 px-5 py-3 shadow-lg backdrop-blur">
            <span className="text-xs font-medium text-muted">Hour of day</span>
            <input
              type="range"
              min={0}
              max={23}
              value={hour}
              onChange={(e) => setHour(Number(e.target.value))}
              className="w-48 accent-accent"
            />
            <span className="w-14 text-sm font-semibold tabular-nums text-foreground">
              {String(hour).padStart(2, "0")}:00
            </span>
            {loading && <span className="text-xs text-muted">loading&hellip;</span>}
          </div>
        )}
      </div>

      <div className="pointer-events-none absolute bottom-4 left-4 rounded-xl border border-border bg-surface/90 px-3 py-2 text-xs text-muted backdrop-blur">
        {mode === "imbalance" ? (
          <>
            <div className="flex items-center gap-2">
              <span className="inline-block h-2 w-2 rounded-full bg-danger" /> bleeding (net outflow)
            </div>
            <div className="mt-1 flex items-center gap-2">
              <span className="inline-block h-2 w-2 rounded-full bg-accent" /> accumulating (net inflow)
            </div>
          </>
        ) : (
          Object.entries(TYPOLOGY_COLOR).map(([label, color]) => (
            <div key={label} className="flex items-center gap-2 not-first:mt-1">
              <span className="inline-block h-2 w-2 rounded-full" style={{ background: color }} />
              {label}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
