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
    typology: str | None = None


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


class SimulatorAllocation(BaseModel):
    station_id: str
    name: str
    truck_hours_used: float
    trips_recovered: float
    fully_covered: bool


class RebalancingSimulation(BaseModel):
    trucks: int
    hours_per_shift: float
    bikes_per_truck_hour: int
    budget_hours: float
    budget_used_hours: float
    stations_covered: int
    stations_fully_covered: int
    total_lost_trips_recoverable: float
    total_recovered_trips: float
    allocations: list[SimulatorAllocation]
