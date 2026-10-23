from pydantic import BaseModel


class CityStat(BaseModel):
    city: str
    trip_count: int
    station_count: int


class Station(BaseModel):
    station_id: str
    name: str
    lat: float
    lon: float


class StationDemandHour(BaseModel):
    hour_of_day: int
    avg_trips_per_day: float


class StationDemand(BaseModel):
    station_id: str
    name: str
    range_days: int
    total_trips: int
    by_hour: list[StationDemandHour]


class NetworkDemandHour(BaseModel):
    hour_of_day: int
    trip_count: int


class StationImbalance(BaseModel):
    station_id: str
    name: str
    hour_of_day: int
    avg_net_balance: float


class WeekdayVsWeekend(BaseModel):
    weekday_mean_trips_per_day: float
    weekend_mean_trips_per_day: float
    weekday_days: int
    weekend_days: int
    holidays_excluded: int
    pct_difference: float
    test_used: str
    statistic: float
    p_value: float
    # Same comparison after removing seasonality (None when the window is too short).
    adjusted_pct_difference: float | None = None
    adjusted_p_value: float | None = None


class RebalancingCandidate(BaseModel):
    station_id: str
    name: str
    stockout_episodes: int
    estimated_lost_trips: float
    truck_hours_needed: float
    lost_trips_per_truck_hour: float


class ForecastDay(BaseModel):
    date: str
    trip_count: float
    is_forecast: bool


class StationForecast(BaseModel):
    station_id: str
    name: str
    method: str
    history_days_used: int
    forecast: list[ForecastDay]
