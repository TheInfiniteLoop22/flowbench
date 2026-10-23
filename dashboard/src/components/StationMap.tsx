"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import MaplibreMap, {
  Layer,
  Source,
  Popup,
  NavigationControl,
  type MapLayerMouseEvent,
  type MapRef,
} from "react-map-gl/maplibre";
import { setWorkerUrl } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { api, type City, type Station, type StationImbalance } from "@/lib/api";
import { ColdStartNote } from "@/components/ColdStartNote";

setWorkerUrl("/maplibre/maplibre-gl-worker.mjs");

const BASEMAP_STYLE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";

const CITY_CENTER: Record<City, { longitude: number; latitude: number; zoom: number }> = {
  new_york: { longitude: -73.97, latitude: 40.735, zoom: 11.5 },
  chicago: { longitude: -87.66, latitude: 41.88, zoom: 11 },
};

const PLAY_INTERVAL_MS = 900;

type LoadState = "loading" | "ready" | "error";
type Selected = {
  station_id: string;
  name: string;
  net_balance: number | null;
  lat: number;
  lon: number;
};

export function StationMap() {
  const searchParams = useSearchParams();
  const city = (searchParams.get("city") === "chicago" ? "chicago" : "new_york") as City;
  return <StationMapInner key={city} city={city} />;
}

function StationMapInner({ city }: { city: City }) {
  const mapRef = useRef<MapRef>(null);
  const [hour, setHour] = useState(8);
  const [playing, setPlaying] = useState(false);
  const [stations, setStations] = useState<Station[]>([]);
  const [stationsState, setStationsState] = useState<LoadState>("loading");
  const [retry, setRetry] = useState(0);
  const [imbalance, setImbalance] = useState<StationImbalance[]>([]);
  const [selected, setSelected] = useState<Selected | null>(null);
  const [settledKey, setSettledKey] = useState("");
  const [imbalanceFailed, setImbalanceFailed] = useState(false);
  const [query, setQuery] = useState("");
  const imbalanceKey = `${hour}|${retry}`;
  const loading = settledKey !== imbalanceKey;
  const showError = stationsState === "error" || (imbalanceFailed && !loading);
  const showLoading = stationsState === "loading" && !showError;

  useEffect(() => {
    let stale = false;
    api
      .stations(city)
      .then((rows) => {
        if (stale) return;
        setStations(rows);
        setStationsState("ready");
      })
      .catch(() => {
        if (stale) return;
        setStations([]);
        setStationsState("error");
      });
    return () => {
      stale = true;
    };
  }, [city, retry]);

  useEffect(() => {
    let stale = false;
    api
      .networkImbalance(hour, city)
      .then((rows) => {
        if (stale) return;
        setImbalance(rows);
        setImbalanceFailed(false);
        setSettledKey(imbalanceKey);
      })
      .catch(() => {
        if (stale) return;
        setImbalanceFailed(true);
        setSettledKey(imbalanceKey);
      });
    return () => {
      stale = true;
    };
  }, [hour, city, imbalanceKey]);

  useEffect(() => {
    if (!playing) return;
    const id = setInterval(() => setHour((h) => (h + 1) % 24), PLAY_INTERVAL_MS);
    return () => clearInterval(id);
  }, [playing]);

  const balanceById = useMemo(
    () => new Map(imbalance.map((r) => [r.station_id, r.avg_net_balance])),
    [imbalance]
  );

  const geojson = useMemo(
    () => ({
      type: "FeatureCollection" as const,
      features: stations
        .filter((s) => balanceById.has(s.station_id))
        .map((s) => ({
          type: "Feature" as const,
          geometry: { type: "Point" as const, coordinates: [s.lon, s.lat] },
          properties: {
            station_id: s.station_id,
            name: s.name,
            net_balance: balanceById.get(s.station_id) ?? 0,
          },
        })),
    }),
    [stations, balanceById]
  );

  const matches = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (q.length < 2) return [];
    return stations.filter((s) => s.name.toLowerCase().includes(q)).slice(0, 6);
  }, [query, stations]);

  const pickStation = (s: Station) => {
    setPlaying(false);
    setQuery("");
    setSelected({
      station_id: s.station_id,
      name: s.name,
      net_balance: balanceById.get(s.station_id) ?? null,
      lat: s.lat,
      lon: s.lon,
    });
    mapRef.current?.flyTo({ center: [s.lon, s.lat], zoom: 15, duration: 900 });
  };

  const paint = {
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
        ref={mapRef}
        initialViewState={CITY_CENTER[city]}
        mapStyle={BASEMAP_STYLE}
        style={{ width: "100%", height: "100%" }}
        interactiveLayerIds={["stations"]}
        cursor="default"
        onClick={(e: MapLayerMouseEvent) => {
          const f = e.features?.[0];
          if (!f) return;
          const [lon, lat] = (f.geometry as GeoJSON.Point).coordinates;
          setSelected({
            station_id: f.properties!.station_id,
            name: f.properties!.name,
            net_balance: f.properties!.net_balance,
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
              <div className="mt-1 text-xs text-muted">
                Net balance @ {String(hour).padStart(2, "0")}:00:{" "}
                {selected.net_balance == null ? (
                  <span className="text-foreground">n/a</span>
                ) : Math.abs(selected.net_balance) < 0.05 ? (
                  <span className="text-foreground">0.0</span>
                ) : (
                  <span className={selected.net_balance < 0 ? "text-danger" : "text-accent"}>
                    {selected.net_balance > 0 ? "+" : ""}
                    {selected.net_balance.toFixed(1)}
                  </span>
                )}
              </div>
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

      <div className="pointer-events-none absolute inset-x-0 top-0 flex flex-col items-center gap-2 p-3 pr-14 sm:p-4 sm:pr-14">
        <div className="pointer-events-auto relative w-full max-w-sm">
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search stations…"
            aria-label="Search stations"
            className="w-full rounded-xl border border-border bg-surface/90 px-3.5 py-2 text-sm text-foreground shadow-lg backdrop-blur placeholder:text-muted"
          />
          {matches.length > 0 && (
            <ul className="absolute left-0 right-0 top-full z-10 mt-1 overflow-hidden rounded-xl border border-border bg-surface-2 shadow-xl">
              {matches.map((s) => (
                <li key={s.station_id}>
                  <button
                    onClick={() => pickStation(s)}
                    className="block w-full truncate px-3.5 py-2 text-left text-sm text-foreground transition-colors hover:bg-accent-soft"
                  >
                    {s.name}
                  </button>
                </li>
              ))}
            </ul>
          )}
          {query.trim().length >= 2 && matches.length === 0 && stationsState === "ready" && (
            <div className="absolute left-0 right-0 top-full mt-1 rounded-xl border border-border bg-surface-2 px-3.5 py-2 text-sm text-muted shadow-xl">
              No matching stations
            </div>
          )}
        </div>

        <div className="pointer-events-auto flex items-center gap-3 rounded-2xl border border-border bg-surface/90 px-4 py-2.5 shadow-lg backdrop-blur sm:gap-4 sm:px-5 sm:py-3">
          <button
            onClick={() => setPlaying((p) => !p)}
            aria-label={playing ? "Pause animation" : "Play through the day"}
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent-soft text-xs text-accent transition-colors hover:bg-accent/25"
          >
            {playing ? "❚❚" : "▶"}
          </button>
          <input
            type="range"
            min={0}
            max={23}
            value={hour}
            aria-label="Hour of day"
            onChange={(e) => {
              setPlaying(false);
              setHour(Number(e.target.value));
            }}
            className="w-32 accent-accent sm:w-48"
          />
          <span className="w-12 text-sm font-semibold tabular-nums text-foreground">
            {String(hour).padStart(2, "0")}:00
          </span>
          {loading && <span className="hidden text-xs text-muted sm:inline">loading&hellip;</span>}
        </div>

      </div>

      {(showLoading || showError) && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center p-6">
          <div className="pointer-events-auto max-w-sm space-y-3 rounded-2xl border border-border bg-surface/95 p-5 text-center shadow-xl backdrop-blur">
            {showLoading ? (
              <>
                <div className="text-sm font-medium">Loading stations&hellip;</div>
                <ColdStartNote />
              </>
            ) : (
              <>
                <div className="text-sm font-medium">Couldn&apos;t reach the data API</div>
                <p className="text-xs text-muted">It may still be waking up from idle.</p>
                <button
                  onClick={() => {
                    setStationsState("loading");
                    setImbalanceFailed(false);
                    setRetry((n) => n + 1);
                  }}
                  className="rounded-lg bg-accent-soft px-4 py-1.5 text-xs font-medium text-accent transition-colors hover:bg-accent/20"
                >
                  Try again
                </button>
              </>
            )}
          </div>
        </div>
      )}

      <div className="pointer-events-none absolute bottom-8 left-3 rounded-xl border border-border bg-surface/90 px-3 py-2 text-xs text-muted backdrop-blur sm:bottom-4 sm:left-4">
        <div className="w-44">
          <div className="text-[11px] uppercase tracking-wide">Avg net bikes / hour</div>
          <div
            className="mt-1.5 h-2 rounded-full"
            style={{ background: "linear-gradient(to right, #f2645a, #5b6473, #35d0ba)" }}
          />
          <div className="mt-1 flex justify-between text-[11px]">
            <span className="text-danger">bleeding</span>
            <span className="text-accent">filling</span>
          </div>
          <div className="mt-1 text-[11px]">Bigger dot = bigger imbalance</div>
        </div>
      </div>
    </div>
  );
}
