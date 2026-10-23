-- Query 4: weekday vs. weekend demand comparison. Grain is one row per
-- calendar day (n=367) — the two groups being compared are "weekday days"
-- vs. "weekend days", each summarized by that day's total trip count.
-- The significance test itself (Mann-Whitney U, which makes no
-- normality assumption) runs in Python — see q04_weekday_vs_weekend.py.
SELECT
    t.date,
    t.is_weekend,
    t.is_holiday,
    count(f.ride_id) AS trip_count
FROM warehouse.dim_time t
LEFT JOIN warehouse.fact_trips f ON f.start_date = t.date AND f.city = 'new_york'  -- second city: scope to NYC, see query 9
GROUP BY t.date, t.is_weekend, t.is_holiday
ORDER BY t.date;
