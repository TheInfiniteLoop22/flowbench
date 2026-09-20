"""FlowBench API — read-only analytics surface over the warehouse. No
auth, no writes (SPEC.md §1, §5). Run with:

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
    RebalancingSimulation,
    SimulatorAllocation,
    Station,
    StationDemand,
    StationDemandHour,
    StationForecast,
    StationImbalance,
    WeekdayVsWeekend,
)

# Second-city stretch (docs/PHASE_PLAN.md): every city-scoped endpoint
# defaults to "new_york" so the dashboard's existing pages keep working
# unchanged unless they explicitly ask for "chicago".
CityQuery = Query("new_york", pattern="^(new_york|chicago)$")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_pool()
    yield
    close_pool()


app = FastAPI(title="FlowBench API", lifespan=lifespan)

# Read-only, no-auth analytics API (SPEC.md §1) — safe to allow any
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
    return [Station(station_id=r[0], name=r[1], lat=r[2], lon=r[3], typology=r[4]) for r in rows]


@app.get("/stations/{station_id}/demand", response_model=StationDemand)
def station_demand(station_id: str, range: int | None = Query(None, ge=1, le=367)):
    with get_cursor() as cur:
        cur.execute(queries.STATION_EXISTS, {"station_id": station_id})
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"station {station_id!r} not found")
        name = row[0]

        cur.execute(queries.STATION_DEMAND, {"station_id": station_id, "range_days": range})
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
    """Stretch (docs/PHASE_PLAN.md "short-horizon per-station demand
    forecast"): a per-station 7-day-trailing-moving-average baseline,
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

    wd_p = stats.shapiro(weekday).pvalue
    we_p = stats.shapiro(weekend).pvalue
    if wd_p > 0.05 and we_p > 0.05:
        test_used = "Welch's t-test"
        statistic, p_value = stats.ttest_ind(weekday, weekend, equal_var=False)
    else:
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


@app.get("/insights/rebalancing-simulator", response_model=RebalancingSimulation)
def rebalancing_simulator(
    trucks: int = Query(2, ge=1, le=50),
    hours_per_shift: float = Query(8, ge=0.5, le=24),
    bikes_per_truck_hour: int = Query(20, ge=1, le=200),
    city: str = CityQuery,
):
    """Stretch (docs/PHASE_PLAN.md "what-if rebalancing simulator"):
    given a truck fleet (count x shift length) and the truck-capacity
    assumption also used by /insights/rebalancing-candidates, greedily
    spends the resulting truck-hour budget on stations in ROI order
    (highest recovered-trips-per-truck-hour first) until the budget runs
    out, prorating the last, partially-covered station. Answers "how
    many of the estimated 302,565 lost trips/year could rebalancing
    actually recover, given a stated fleet size?" rather than just
    ranking candidates in the abstract.
    """
    budget_hours = trucks * hours_per_shift

    with get_cursor() as cur:
        # Every qualifying station (docs/BUG_TRACKER.md-style caveat: ~2,128
        # as of the last warehouse build), not just a top slice — needed so
        # total_lost_trips_recoverable is the real addressable total, not
        # an artifact of an arbitrary cutoff.
        cur.execute(queries.REBALANCING_CANDIDATES_RANKED, {"limit": 5000, "city": city})
        rows = cur.fetchall()

    allocations: list[SimulatorAllocation] = []
    remaining = budget_hours
    total_recovered = 0.0
    total_recoverable = sum(float(r[4]) for r in rows)

    for station_id, name, num_episodes, avg_hourly_outflow, estimated_lost_trips in rows:
        if remaining <= 0:
            break
        truck_hours_needed = num_episodes * float(avg_hourly_outflow) / bikes_per_truck_hour
        if truck_hours_needed <= 0:
            continue
        used = min(truck_hours_needed, remaining)
        share = used / truck_hours_needed
        recovered = float(estimated_lost_trips) * share
        allocations.append(
            SimulatorAllocation(
                station_id=station_id,
                name=name,
                truck_hours_used=round(used, 2),
                trips_recovered=round(recovered, 1),
                fully_covered=used >= truck_hours_needed,
            )
        )
        total_recovered += recovered
        remaining -= used

    return RebalancingSimulation(
        trucks=trucks,
        hours_per_shift=hours_per_shift,
        bikes_per_truck_hour=bikes_per_truck_hour,
        budget_hours=round(budget_hours, 2),
        budget_used_hours=round(budget_hours - remaining, 2),
        stations_covered=len(allocations),
        stations_fully_covered=sum(1 for a in allocations if a.fully_covered),
        total_lost_trips_recoverable=round(total_recoverable, 1),
        total_recovered_trips=round(total_recovered, 1),
        allocations=allocations,
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
