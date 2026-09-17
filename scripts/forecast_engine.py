"""
TelNova Communications - Financial Planning & Forecasting Engine
==================================================================
Mirrors the same rigor as the companion HR Analytics project's workforce
forecasting engine, applied to financial planning:

1. REVENUE & EBITDA FORECAST
   - 12-month linear-trend regression on the last 18 months of revenue,
     blended 50/50 with a stated annual growth target, then EBITDA is
     derived by holding the trailing-12-month average EBITDA margin.

2. CASH FLOW / LIQUIDITY FORECAST
   - Holt's linear (double) exponential smoothing on trailing free cash
     flow, projected forward 12 months, plus a resulting cash-runway view
     (starting cash + cumulative forecast FCF).

3. CAPITAL PLAN
   - 12-month capex budget derived from the forecast revenue at the
     trailing capex-intensity ratio, split into Growth vs. Maintenance
     using each category's historical share -- the same
     "replacement + growth" logic as the HR project's hiring plan.

4. BUDGET OVERRUN RISK SCORE
   - Every cost center scored 0-100 with a transparent weighted-factor
     model: average historical overspend, whether overspend is
     accelerating, spend volatility, and how large the cost center's
     absolute budget is (bigger dollar bases carry more risk exposure).
     Min-max scaled across this population, banded into
     Low / Medium / High / Critical -- fully explainable, no black box.

Author: Milad Shabani
"""

import numpy as np
import pandas as pd
from datetime import datetime

TODAY = datetime(2026, 9, 1)


# ----------------------------------------------------------------------
# 1. REVENUE & EBITDA FORECAST
# ----------------------------------------------------------------------
def forecast_revenue_ebitda(pnl_df, horizon_months=12, growth_target_annual=0.08):
    hist = pnl_df.copy()
    hist["Month"] = pd.to_datetime(hist["Month"])
    hist = hist.sort_values("Month").tail(18).reset_index(drop=True)

    x = np.arange(len(hist))
    y = hist["RevenueUSD"].values
    slope, intercept = np.polyfit(x, y, 1)

    future_x = np.arange(len(hist), len(hist) + horizon_months)
    trend_forecast = intercept + slope * future_x

    last_actual = y[-1]
    growth_path = last_actual * (1 + growth_target_annual) ** (np.arange(1, horizon_months + 1) / 12)
    blended_revenue = 0.5 * trend_forecast + 0.5 * growth_path

    trailing_ebitda_margin = pnl_df.tail(12)["EBITDA_MarginPct"].mean()
    forecast_ebitda = blended_revenue * trailing_ebitda_margin

    future_months = pd.date_range(start=hist["Month"].max() + pd.offsets.MonthBegin(1), periods=horizon_months, freq="MS")
    forecast_df = pd.DataFrame({
        "Month": future_months.date,
        "ForecastRevenue_Trend": np.round(trend_forecast, 0),
        "ForecastRevenue_GrowthTarget": np.round(growth_path, 0),
        "ForecastRevenue_Blended": np.round(blended_revenue, 0),
        "ForecastEBITDA": np.round(forecast_ebitda, 0),
        "AssumedEBITDAMarginPct": round(trailing_ebitda_margin, 4),
    })
    return forecast_df, slope


# ----------------------------------------------------------------------
# 2. CASH FLOW / LIQUIDITY FORECAST (Holt's linear exponential smoothing)
# ----------------------------------------------------------------------
def forecast_cash_flow(cashflow_df, balance_df, horizon_months=12, alpha=0.4, beta=0.25):
    hist = cashflow_df.copy()
    hist["Month"] = pd.to_datetime(hist["Month"])
    hist = hist.sort_values("Month").reset_index(drop=True)

    series = hist["FreeCashFlowUSD"].values
    level = series[0]
    trend = series[1] - series[0]

    for t in range(1, len(series)):
        last_level = level
        level = alpha * series[t] + (1 - alpha) * (level + trend)
        trend = beta * (level - last_level) + (1 - beta) * trend

    forecasts = [level + h * trend for h in range(1, horizon_months + 1)]

    starting_cash = balance_df.sort_values("Month")["CashUSD"].iloc[-1]
    cumulative_cash = starting_cash
    future_months = pd.date_range(start=hist["Month"].max() + pd.offsets.MonthBegin(1), periods=horizon_months, freq="MS")
    rows = []
    for m, fcf in zip(future_months, forecasts):
        cumulative_cash += fcf
        rows.append(dict(Month=m.date(), ForecastFreeCashFlow=round(fcf, 0), ProjectedCashBalance=round(cumulative_cash, 0)))
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------
# 3. CAPITAL PLAN (12-month capex budget by category)
# ----------------------------------------------------------------------
def forecast_capex_plan(capex_df, revenue_forecast_df, horizon_months=12):
    hist = capex_df.copy()
    hist["Month"] = pd.to_datetime(hist["Month"])
    trailing = hist[hist["Month"] >= hist["Month"].max() - pd.DateOffset(months=12)]

    monthly_revenue_trailing = trailing.groupby("Month")["ActualSpendUSD"].sum()
    # trailing capex intensity vs. revenue -- approximate using the P&L-independent
    # revenue total already embedded in the forecast frame's growth trajectory
    cat_shares = trailing.groupby("Category")["ActualSpendUSD"].sum()
    cat_shares = (cat_shares / cat_shares.sum()).to_dict()
    cat_types = trailing.drop_duplicates("Category").set_index("Category")["CapexType"].to_dict()

    trailing_capex_intensity = trailing["ActualSpendUSD"].sum() / trailing_capex_intensity_denominator(trailing)

    rows = []
    for _, r in revenue_forecast_df.iterrows():
        month_capex_total = r["ForecastRevenue_Blended"] * trailing_capex_intensity
        for cat, share in cat_shares.items():
            rows.append(dict(
                Month=r["Month"], Category=cat, CapexType=cat_types.get(cat, "Growth"),
                PlannedCapexUSD=round(month_capex_total * share, 0),
            ))
    return pd.DataFrame(rows)


def trailing_capex_intensity_denominator(trailing_capex):
    # Reconstruct trailing revenue total from the capex records' own month keys
    # by re-deriving from the global monthly revenue cache at call time.
    import os
    base = os.path.dirname(os.path.abspath(__file__)) + os.sep
    rev = pd.read_csv(base + "_cache_revenue.csv")
    rev["Month"] = pd.to_datetime(rev["Month"])
    monthly_rev = rev.groupby("Month")["RevenueUSD"].sum()
    months = trailing_capex["Month"].unique()
    return monthly_rev.reindex(months).sum()


# ----------------------------------------------------------------------
# 4. BUDGET OVERRUN RISK SCORE (per cost center, explainable weighted model)
# ----------------------------------------------------------------------
def score_budget_risk(budget_df):
    cc_stats = []
    for cc, grp in budget_df.groupby("CostCenter"):
        grp = grp.sort_values("Month")
        avg_variance_pct = grp["VariancePct"].mean()
        # Trend: is overspend getting worse? (slope of variance % over time)
        x = np.arange(len(grp))
        slope = np.polyfit(x, grp["VariancePct"].values, 1)[0] if len(grp) > 2 else 0
        volatility = grp["VariancePct"].std()
        avg_budget = grp["BudgetedUSD"].mean()
        latest_variance_pct = grp["VariancePct"].iloc[-1]
        cc_stats.append(dict(
            CostCenter=cc, AvgVariancePct=avg_variance_pct, VarianceTrendSlope=slope,
            VarianceVolatility=volatility, AvgMonthlyBudgetUSD=avg_budget,
            LatestVariancePct=latest_variance_pct,
        ))
    df = pd.DataFrame(cc_stats)

    def norm(s, invert=False):
        s = s.astype(float)
        rng = (s.max() - s.min()) or 1
        n = (s - s.min()) / rng
        return 1 - n if invert else n

    df["f_avg_overspend"] = norm(df["AvgVariancePct"].clip(lower=0))
    df["f_worsening_trend"] = norm(df["VarianceTrendSlope"].clip(lower=0))
    df["f_volatility"] = norm(df["VarianceVolatility"])
    df["f_budget_size"] = norm(df["AvgMonthlyBudgetUSD"])
    df["f_latest_overspend"] = norm(df["LatestVariancePct"].clip(lower=0))

    weights = dict(f_avg_overspend=0.32, f_worsening_trend=0.24, f_latest_overspend=0.20,
                   f_volatility=0.14, f_budget_size=0.10)

    raw_score = sum(df[f] * w for f, w in weights.items()) * 100
    lo, hi = raw_score.min(), raw_score.max()
    df["BudgetRiskScore"] = ((raw_score - lo) / (hi - lo) * 100).round(1)

    q50, q80, q93 = df["BudgetRiskScore"].quantile([0.50, 0.80, 0.93])

    def band(score):
        if score >= q93:
            return "Critical"
        elif score >= q80:
            return "High"
        elif score >= q50:
            return "Medium"
        return "Low"

    df["RiskBand"] = df["BudgetRiskScore"].apply(band)

    label_map = {
        "f_avg_overspend": "Persistent overspend vs. budget", "f_worsening_trend": "Overspend trend worsening",
        "f_latest_overspend": "Over budget last month", "f_volatility": "Highly volatile spend pattern",
        "f_budget_size": "Large absolute budget exposure",
    }
    top_drivers = []
    for _, row in df.iterrows():
        contribs = {f: row[f] * w for f, w in weights.items()}
        top2 = sorted(contribs.items(), key=lambda kv: kv[1], reverse=True)[:2]
        top_drivers.append(" & ".join(label_map[k] for k, _ in top2))
    df["TopRiskDrivers"] = top_drivers

    out_cols = ["CostCenter", "AvgVariancePct", "LatestVariancePct", "AvgMonthlyBudgetUSD",
                "BudgetRiskScore", "RiskBand", "TopRiskDrivers"]
    return df[out_cols].sort_values("BudgetRiskScore", ascending=False).reset_index(drop=True)


if __name__ == "__main__":
    import os
    base = os.path.dirname(os.path.abspath(__file__)) + os.sep

    pnl = pd.read_csv(base + "_cache_pnl.csv")
    cashflow = pd.read_csv(base + "_cache_cashflow.csv")
    balance = pd.read_csv(base + "_cache_balance.csv")
    capex = pd.read_csv(base + "_cache_capex.csv")
    budget = pd.read_csv(base + "_cache_budget.csv")

    revenue_fc, slope = forecast_revenue_ebitda(pnl)
    cashflow_fc = forecast_cash_flow(cashflow, balance)
    capex_fc = forecast_capex_plan(capex, revenue_fc)
    budget_risk = score_budget_risk(budget)

    revenue_fc.to_csv(base + "_cache_revenue_forecast.csv", index=False)
    cashflow_fc.to_csv(base + "_cache_cashflow_forecast.csv", index=False)
    capex_fc.to_csv(base + "_cache_capex_forecast.csv", index=False)
    budget_risk.to_csv(base + "_cache_budget_risk.csv", index=False)

    print("Forecasting complete.")
    print(f"  Revenue trend slope: {slope:+,.0f} USD/month")
    print(f"  12-month forecast revenue (last month): {revenue_fc['ForecastRevenue_Blended'].iloc[-1]:,.0f}")
    print(f"  12-month forecast EBITDA (last month): {revenue_fc['ForecastEBITDA'].iloc[-1]:,.0f}")
    print(f"  Projected cash balance in 12 months: {cashflow_fc['ProjectedCashBalance'].iloc[-1]:,.0f}")
    print(f"  Total planned capex (12mo): {capex_fc['PlannedCapexUSD'].sum():,.0f}")
    print(f"  Budget risk bands: {budget_risk['RiskBand'].value_counts().to_dict()}")
