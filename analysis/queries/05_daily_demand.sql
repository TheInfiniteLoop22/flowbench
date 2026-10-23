-- Query 5: system-wide daily trip counts, the input series for the
-- forecasting baseline. Same
-- shape as query 4's per-day series but without the weekday/weekend
-- split — this one needs strict date order for a time-series backtest.
SELECT
    t.date,
    t.is_weekend,
    t.is_holiday,
    count(f.ride_id) AS trip_count
FROM warehouse.dim_time t
LEFT JOIN warehouse.fact_trips f ON f.start_date = t.date AND f.city = 'new_york'  -- second city: scope to NYC, see query 9
GROUP BY t.date, t.is_weekend, t.is_holiday
ORDER BY t.date;
