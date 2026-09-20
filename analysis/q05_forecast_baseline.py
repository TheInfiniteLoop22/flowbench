"""Query 5: short-horizon demand forecast baseline. Resolves SPEC.md open
question #4 (moving average vs. simple linear regression) from the EDA
here rather than deciding upfront, then backtests whichever wins.

Non-goal per SPEC.md §9: no ML/deep-learning forecasting — this is
deliberately a simple, defensible baseline, not a demand model.

Usage: python analysis/q05_forecast_baseline.py
"""
import pathlib
import time

import numpy as np
from scipy import stats

from db import get_conn

SQL = (pathlib.Path(__file__).resolve().parent / "queries" / "05_daily_demand.sql").read_text()
HOLDOUT_DAYS = 28


def mae(actual, pred):
    return float(np.mean(np.abs(np.array(actual) - np.array(pred))))


def rmse(actual, pred):
    return float(np.sqrt(np.mean((np.array(actual) - np.array(pred)) ** 2)))


def mape(actual, pred):
    actual = np.array(actual, dtype=float)
    pred = np.array(pred, dtype=float)
    return float(np.mean(np.abs((actual - pred) / actual)))


def main():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            t0 = time.time()
            cur.execute(SQL)
            rows = cur.fetchall()
            elapsed = time.time() - t0
            print(f"{len(rows)} calendar days in {elapsed:.1f}s")

            cur.execute("SELECT count(*) FROM warehouse.fact_trips")
            total_trips = cur.fetchone()[0]
            total_here = sum(r[3] for r in rows)
            status = "OK" if total_here == total_trips else "FAIL"
            print(f"  [{status}] sum(trip_count) == fact_trips rows: {total_here:,} vs {total_trips:,}\n")
    finally:
        conn.close()

    y = np.array([r[3] for r in rows], dtype=float)
    n = len(y)

    x = np.arange(n)
    slope, intercept, r_value, p_value, _ = stats.linregress(x, y)
    print("EDA — linear trend over the full window:")
    print(f"  slope={slope:+.1f} trips/day, R^2={r_value**2:.3f} "
          f"(trend explains only {r_value**2:.1%} of day-to-day variance — weak)")

    def autocorr(series, lag):
        s = series - series.mean()
        return float(np.corrcoef(s[:-lag], s[lag:])[0, 1])

    print(f"  autocorrelation: lag-1={autocorr(y, 1):.3f}, lag-7={autocorr(y, 7):.3f}")

    def ma_forecast(train, test):
        preds, history = [], list(train)
        for actual in test:
            preds.append(np.mean(history[-7:]))
            history.append(actual)  # walk-forward: real value fed back in once observed
        return np.array(preds)

    def lr_forecast(train, test):
        tx = np.arange(len(train))
        s, i, _, _, _ = stats.linregress(tx, train)
        fx = np.arange(len(train), len(train) + len(test))
        return s * fx + i

    # Resolve open question #4 empirically: pick whichever baseline wins a
    # validation holdout (the 28 days *before* the final test window),
    # then only ever report the final test-window score for the winner —
    # avoids picking a model and grading it on the same data.
    val_train, val_test = y[: -2 * HOLDOUT_DAYS], y[-2 * HOLDOUT_DAYS : -HOLDOUT_DAYS]
    val_ma_mae = mae(val_test, ma_forecast(val_train, val_test))
    val_lr_mae = mae(val_test, lr_forecast(val_train, val_test))
    print(f"\nValidation holdout (days {n - 2*HOLDOUT_DAYS}..{n - HOLDOUT_DAYS}): "
          f"7-day MA MAE={val_ma_mae:,.0f}, linear regression MAE={val_lr_mae:,.0f}")

    if val_ma_mae <= val_lr_mae:
        decision, forecast_fn = "7-day moving average", ma_forecast
        print(f"Decision: {decision} — a weak trend (R^2={r_value**2:.3f}) isn't worth giving up "
              "the day-of-week shape a trailing mean captures; confirmed by lower validation MAE.")
    else:
        decision, forecast_fn = "simple linear regression", lr_forecast
        print(f"Decision: {decision} — won lower validation MAE despite the weak trend fit.")

    train_y, test_y = y[:-HOLDOUT_DAYS], y[-HOLDOUT_DAYS:]
    final_preds = forecast_fn(train_y, test_y)
    print(f"\nFinal test holdout (last {HOLDOUT_DAYS} days), {decision}:")
    print(f"  MAE={mae(test_y, final_preds):,.0f}  RMSE={rmse(test_y, final_preds):,.0f}  "
          f"MAPE={mape(test_y, final_preds):.1%}")
    print(f"\nBaseline shipped: {decision}.")


if __name__ == "__main__":
    main()
