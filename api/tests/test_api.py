import os

import psycopg2
import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_list_stations(client):
    r = client.get("/stations")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 3
    ids = {s["station_id"] for s in body}
    assert ids == {"S1", "S2", "S3"}


def test_list_stations_pagination(client):
    r = client.get("/stations", params={"limit": 1, "offset": 1})
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_list_stations_defaults_to_new_york(client):
    r = client.get("/stations")
    assert r.status_code == 200
    ids = {s["station_id"] for s in r.json()}
    assert ids == {"S1", "S2", "S3"}
    assert "C1" not in ids


def test_list_stations_chicago_filter(client):
    r = client.get("/stations", params={"city": "chicago"})
    assert r.status_code == 200
    ids = {s["station_id"] for s in r.json()}
    assert ids == {"C1"}


def test_cities_endpoint(client):
    r = client.get("/cities")
    assert r.status_code == 200
    by_city = {c["city"]: c for c in r.json()}
    assert set(by_city) == {"new_york", "chicago"}
    assert by_city["new_york"]["station_count"] == 3
    assert by_city["chicago"]["station_count"] == 1


def test_network_demand_is_city_scoped(client):
    nyc = client.get("/network/demand").json()
    chi = client.get("/network/demand", params={"city": "chicago"}).json()
    assert sum(r["trip_count"] for r in nyc) != sum(r["trip_count"] for r in chi)


def test_station_forecast(client):
    r = client.get("/stations/S1/forecast", params={"days": 3})
    assert r.status_code == 200
    body = r.json()
    assert body["station_id"] == "S1"
    forecast_days = [d for d in body["forecast"] if d["is_forecast"]]
    history_days = [d for d in body["forecast"] if not d["is_forecast"]]
    assert len(forecast_days) == 3
    assert len(history_days) > 0
    assert all(d["trip_count"] >= 0 for d in body["forecast"])


def test_station_forecast_unknown_station_is_404(client):
    r = client.get("/stations/does-not-exist/forecast")
    assert r.status_code == 404


def test_station_demand(client):
    r = client.get("/stations/S1/demand")
    assert r.status_code == 200
    body = r.json()
    assert body["station_id"] == "S1"
    assert body["total_trips"] == 86  # baseline 3x14 + day-varying bonus batch, see conftest fixture
    hours = {h["hour_of_day"] for h in body["by_hour"]}
    assert hours == {8, 9, 13, 18}


def test_station_demand_unknown_station_is_404(client):
    r = client.get("/stations/does-not-exist/demand")
    assert r.status_code == 404


def test_station_demand_range_filter_reduces_or_matches_total(client):
    # Only 7/30/90/all-time are precomputed (warehouse/migrations/0011_*.sql)
    # -- matches the dashboard's fixed range toggle, not an arbitrary N.
    full = client.get("/stations/S1/demand").json()["total_trips"]
    limited = client.get("/stations/S1/demand", params={"range": 7}).json()["total_trips"]
    assert limited <= full


def test_station_demand_rejects_unsupported_range(client):
    r = client.get("/stations/S1/demand", params={"range": 15})
    assert r.status_code == 422


def test_network_demand(client):
    r = client.get("/network/demand")
    assert r.status_code == 200
    body = r.json()
    hours = {row["hour_of_day"] for row in body}
    assert hours == {8, 9, 13, 18}
    assert sum(row["trip_count"] for row in body) == 3 * 42 + 44  # 3 stations' baseline + S1's bonus batch


def test_network_imbalance_shape_and_ordering(client):
    r = client.get("/network/imbalance", params={"hour": 8})
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 3
    balances = [row["avg_net_balance"] for row in body]
    assert balances == sorted(balances)  # ascending, most-depleted first


def test_network_imbalance_requires_valid_hour(client):
    r = client.get("/network/imbalance", params={"hour": 24})
    assert r.status_code == 422
    r = client.get("/network/imbalance")
    assert r.status_code == 422  # hour is required, no default


def test_weekday_vs_weekend_runs_a_real_test(client):
    r = client.get("/insights/weekday-vs-weekend")
    assert r.status_code == 200
    body = r.json()
    assert body["test_used"] == "Mann-Whitney U"
    assert 0.0 <= body["p_value"] <= 1.0
    assert body["weekday_days"] + body["weekend_days"] + body["holidays_excluded"] == 14


def test_rebalancing_candidates_respects_limit(client):
    r = client.get("/insights/rebalancing-candidates", params={"limit": 2})
    assert r.status_code == 200
    assert len(r.json()) <= 2


def test_rebalancing_candidates_custom_truck_capacity_changes_truck_hours(client):
    slow = client.get("/insights/rebalancing-candidates", params={"bikes_per_truck_hour": 5}).json()
    fast = client.get("/insights/rebalancing-candidates", params={"bikes_per_truck_hour": 50}).json()
    if slow and fast:  # only meaningful if the tiny fixture produced any stockout episodes at all
        by_station_slow = {r["station_id"]: r["truck_hours_needed"] for r in slow}
        by_station_fast = {r["station_id"]: r["truck_hours_needed"] for r in fast}
        common = set(by_station_slow) & set(by_station_fast)
        for station_id in common:
            assert by_station_slow[station_id] >= by_station_fast[station_id]


def test_survives_server_closing_idle_connections(client):
    """Neon suspends idle compute and drops connections; the next request must still succeed."""
    assert client.get("/cities").status_code == 200   # make sure the pool holds a connection
    admin = psycopg2.connect(os.environ["DATABASE_URL"])
    admin.autocommit = True
    with admin.cursor() as cur:
        cur.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = current_database() AND pid <> pg_backend_pid()")
    admin.close()
    assert client.get("/cities").status_code == 200


def test_more_concurrent_requests_than_connections_all_succeed(client):
    """The pool holds 10 connections; 40 simultaneous requests must queue, not fail."""
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(40) as ex:
        codes = list(ex.map(lambda _: client.get("/cities").status_code, range(120)))
    assert set(codes) == {200}


def test_weekday_vs_weekend_adjusted_fields_absent_for_short_window(client):
    body = client.get("/insights/weekday-vs-weekend").json()
    assert body["adjusted_pct_difference"] is None and body["adjusted_p_value"] is None  # fixture has 14 days


def test_seasonal_adjustment_sharpens_a_weekday_effect_hidden_by_season():
    """A big seasonal swing plus a 15% weekday premium: adjusting for season recovers the premium
    and gives far stronger evidence than the raw comparison."""
    import numpy as np
    from scipy import stats
    from api.main import seasonally_adjusted_comparison

    days = np.arange(240)
    weekend = (days % 7) >= 5
    season = 115 + 55 * np.sin(days / 240 * 2 * np.pi - 1.5)
    noise = np.random.default_rng(1).normal(0, 2, 240)
    counts = list(season * np.where(weekend, 1.0, 1.15) + noise)

    wd = [c for c, w in zip(counts, weekend) if not w]
    we = [c for c, w in zip(counts, weekend) if w]
    raw_p = stats.mannwhitneyu(wd, we).pvalue
    adj_pct, adj_p = seasonally_adjusted_comparison(counts, list(weekend), [False] * 240)
    assert 0.10 < adj_pct < 0.20
    assert adj_p < raw_p * 1e-6


def test_seasonal_adjustment_returns_none_when_too_short():
    from api.main import seasonally_adjusted_comparison
    assert seasonally_adjusted_comparison([1.0] * 20, [False] * 20, [False] * 20) == (None, None)
