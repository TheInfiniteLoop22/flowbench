"""FlowBench API — read-only analytics surface over the warehouse. No
auth, no writes. Run with:

    uvicorn api.main:app --reload
"""
from contextlib import asynccontextmanager
from datetime import timedelta

import numpy as np
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from scipy import stats

from . import queries
from .db import close_pool, get_cursor, init_pool
from .schemas import (
    CityStat,
    ForecastDay,
    NetworkDemandHour,
    RebalancingCandidate,
    Station,
    StationDemand,
    StationDemandHour,
    StationForecast,
    StationImbalance,
    WeekdayVsWeekend,
)

# Second-city support: every city-scoped endpoint
# defaults to "new_york" so the dashboard's existing pages keep working
# unchanged unless they explicitly ask for "chicago".
CityQuery = Query("new_york", pattern="^(new_york|chicago)$")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_pool()
    yield
    close_pool()


app = FastAPI(title="FlowBench API", lifespan=lifespan)

# Read-only, no-auth analytics API — safe to allow any
# origin, there's nothing here a browser-based CSRF/credential attack
# could exploit (no cookies, no writes).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
)


@app.get("/cities", response_model=list[CityStat])
def cities():
    with get_cursor() as cur:
        cur.execute(queries.CITIES)
        rows = cur.fetchall()
    return [CityStat(city=r[0], trip_count=r[1], station_count=r[2]) for r in rows]


@app.get("/stations", response_model=list[Station])
def list_stations(
    city: str = CityQuery, limit: int = Query(500, ge=1, le=5000), offset: int = Query(0, ge=0)
):
    with get_cursor() as cur:
        cur.execute(queries.LIST_STATIONS, {"city": city, "limit": limit, "offset": offset})
        rows = cur.fetchall()
    return [Station(station_id=r[0], name=r[1], lat=r[2], lon=r[3]) for r in rows]


STATION_DEMAND_RANGES = (7, 30, 90)


@app.get("/stations/{station_id}/demand", response_model=StationDemand)
def station_demand(station_id: str, range: int | None = Query(None)):
    if range is not None and range not in STATION_DEMAND_RANGES:
        raise HTTPException(
            status_code=422,
            detail=f"range must be one of {STATION_DEMAND_RANGES} or omitted for all-time",
        )
    with get_cursor() as cur:
        cur.execute(queries.STATION_EXISTS, {"station_id": station_id})
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"station {station_id!r} not found")
        name = row[0]

        # 0 is the "all time" bucket in warehouse.station_hourly_demand_agg
        # (warehouse/migrations/0011_*.sql) -- only 7/30/90/0 are
        # precomputed, matching the dashboard's fixed range toggle
        # (dashboard/src/components/StationDetail.tsx's RANGES).
        cur.execute(queries.STATION_DEMAND, {"station_id": station_id, "range_days": range or 0})
        hours = cur.fetchall()

    return StationDemand(
        station_id=station_id,
        name=name,
        range_days=range or 367,
        total_trips=sum(r[2] for r in hours),
        by_hour=[StationDemandHour(hour_of_day=r[0], avg_trips_per_day=float(r[1])) for r in hours],
    )


@app.get("/stations/{station_id}/forecast", response_model=StationForecast)
def station_forecast(station_id: str, days: int = Query(7, ge=1, le=14)):
    """Short-horizon per-station demand forecast: a per-station 7-day-trailing-moving-average baseline,
    the same method analysis/q05 picked for the system-wide series after
    empirically beating a linear trend on a validation holdout. Applied
    per-station here rather than system-wide; not re-validated per
    station (2,492 stations, no per-station backtest budget) — it's the
    same baseline shown to win in aggregate, not independently confirmed
    for every individual station.
    """
    with get_cursor() as cur:
        cur.execute(queries.STATION_EXISTS, {"station_id": station_id})
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"station {station_id!r} not found")
        name = row[0]

        cur.execute(queries.STATION_DAILY_DEMAND, {"station_id": station_id})
        rows = cur.fetchall()

    history = [float(r[1]) for r in rows]
    last_date = rows[-1][0]

    forecast: list[ForecastDay] = [
        ForecastDay(date=r[0].isoformat(), trip_count=float(r[1]), is_forecast=False)
        for r in rows[-30:]
    ]
    window = list(history)
    for i in range(1, days + 1):
        predicted = float(np.mean(window[-7:])) if window else 0.0
        forecast.append(
            ForecastDay(date=(last_date + timedelta(days=i)).isoformat(),
                        trip_count=round(predicted, 1), is_forecast=True)
        )
        window.append(predicted)  # walk-forward: no real future value exists yet

    return StationForecast(
        station_id=station_id,
        name=name,
        method="7-day trailing moving average",
        history_days_used=len(history),
        forecast=forecast,
    )


@app.get("/network/demand", response_model=list[NetworkDemandHour])
def network_demand(city: str = CityQuery):
    with get_cursor() as cur:
        cur.execute(queries.NETWORK_DEMAND, {"city": city})
        rows = cur.fetchall()
    return [NetworkDemandHour(hour_of_day=r[0], trip_count=r[1]) for r in rows]


@app.get("/network/imbalance", response_model=list[StationImbalance])
def network_imbalance(hour: int = Query(..., ge=0, le=23), city: str = CityQuery):
    with get_cursor() as cur:
        cur.execute(queries.NETWORK_IMBALANCE, {"hour_of_day": hour, "city": city})
        rows = cur.fetchall()
    return [
        StationImbalance(station_id=r[0], name=r[1], hour_of_day=r[2], avg_net_balance=float(r[3]))
        for r in rows
    ]


@app.get("/insights/weekday-vs-weekend", response_model=WeekdayVsWeekend)
def weekday_vs_weekend(city: str = CityQuery):
    with get_cursor() as cur:
        cur.execute(queries.WEEKDAY_VS_WEEKEND_DAILY, {"city": city})
        rows = cur.fetchall()

    weekday = [r[3] for r in rows if not r[1] and not r[2]]
    weekend = [r[3] for r in rows if r[1] and not r[2]]
    holidays = sum(1 for r in rows if r[2])

    if len(weekday) < 3 or len(weekend) < 3:
        raise HTTPException(status_code=500, detail="not enough days in the warehouse to run the test")

    # Mann-Whitney U: no assumption about the shape of the daily-trip
    # distribution, so no normality pre-test is needed.
    test_used = "Mann-Whitney U"
    statistic, p_value = stats.mannwhitneyu(weekday, weekend, alternative="two-sided")

    wd_mean = sum(weekday) / len(weekday)
    we_mean = sum(weekend) / len(weekend)
    return WeekdayVsWeekend(
        weekday_mean_trips_per_day=wd_mean,
        weekend_mean_trips_per_day=we_mean,
        weekday_days=len(weekday),
        weekend_days=len(weekend),
        holidays_excluded=holidays,
        pct_difference=wd_mean / we_mean - 1,
        test_used=test_used,
        statistic=float(statistic),
        p_value=float(p_value),
    )


@app.get("/insights/rebalancing-candidates", response_model=list[RebalancingCandidate])
def rebalancing_candidates(
    limit: int = Query(20, ge=1, le=100),
    bikes_per_truck_hour: int = Query(20, ge=1, le=200),
    city: str = CityQuery,
):
    with get_cursor() as cur:
        cur.execute(
            queries.REBALANCING_CANDIDATES,
            {"limit": limit, "bikes_per_truck_hour": bikes_per_truck_hour, "city": city},
        )
        rows = cur.fetchall()
    return [
        RebalancingCandidate(
            station_id=r[0], name=r[1], stockout_episodes=r[2],
            estimated_lost_trips=float(r[3]), truck_hours_needed=float(r[4]),
            lost_trips_per_truck_hour=float(r[5]),
        )
        for r in rows
    ]
