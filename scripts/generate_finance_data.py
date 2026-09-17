"""
TelNova Communications - Finance Analytics
Synthetic Financial Data Generation Engine
=================================================
Generates a realistic, internally-consistent set of financial statements
and operating metrics for the same fictional ISP/telecom operator used in
the companion HR Analytics Dashboard project (~1,047,500 subscribers).

Covers 48 months of history (2022-10 .. 2026-09) across:
    - Segment-level revenue & ARPU (Residential Fiber, Residential Mobile,
      Residential TV/Bundles, Business & Enterprise, Wholesale)
    - A full monthly P&L (COGS, OPEX by category, EBITDA, D&A, EBIT,
      interest, tax, net income)
    - A monthly balance sheet
    - A monthly cash flow statement
    - A capital project portfolio (fiber build-out, 5G, data centers, IT,
      fleet, maintenance)
    - A multi-tranche debt schedule
    - Department-level budget vs. actual spend
    - Segment-level customer economics (CAC, LTV, churn, payback period)

All figures are FICTIONAL and generated with a fixed random seed for full
reproducibility. No real company's financials are represented.

Author: Milad Shabani
Project: TelNova Finance Analytics
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random

# ----------------------------------------------------------------------
# 0. GLOBAL CONFIG
# ----------------------------------------------------------------------
SEED = 7741
np.random.seed(SEED)
random.seed(SEED)

TODAY = datetime(2026, 9, 1)
HISTORY_MONTHS = 48  # 4 years of monthly history
CURRENCY = "USD"
TOTAL_SUBSCRIBERS_LATEST = 1_047_500

# ----------------------------------------------------------------------
# 1. SEGMENTS
# ----------------------------------------------------------------------
SEGMENTS = {
    # name: (subscriber_share, base_arpu_usd, arpu_monthly_drift, subscriber_monthly_growth, gross_margin)
    "Residential Fiber":      dict(sub_share=0.45, arpu=25.0, arpu_drift=0.0009, sub_growth=0.0095, gross_margin=0.68),
    "Residential Mobile":     dict(sub_share=0.40, arpu=11.0, arpu_drift=-0.0006, sub_growth=0.0060, gross_margin=0.60),
    "Residential TV/Bundles": dict(sub_share=0.15, arpu=16.0, arpu_drift=-0.0018, sub_growth=-0.0030, gross_margin=0.52),
}
# Business & Wholesale are modeled as separate, much smaller account populations
# (a handful of large contracts) rather than a share of the residential base --
# treating them as "X% of 1M+ subscribers" would imply an implausible number
# of enterprise/carrier accounts.
B2B_SEGMENTS = {
    "Business & Enterprise":    dict(accounts=9_500, arpu=150.0, arpu_drift=0.0018, account_growth=0.0100, gross_margin=0.71),
    "Wholesale & Interconnect": dict(accounts=60, arpu=22_000.0, arpu_drift=0.0010, account_growth=0.0070, gross_margin=0.74),
}

OPEX_CATEGORIES = {
    # category: (share_of_revenue_base, monthly_drift, volatility)
    # Calibrated so blended OPEX ~= 26% of revenue -> ~39% EBITDA margin,
    # in line with a scaled fiber/mobile operator.
    "Network Operations":        dict(share=0.072, drift=-0.0004, vol=0.02),
    "Customer Care & Support":   dict(share=0.042, drift=-0.0006, vol=0.03),
    "Sales & Marketing":         dict(share=0.053, drift=0.0002, vol=0.05),
    "General & Administrative":  dict(share=0.030, drift=-0.0002, vol=0.02),
    "Personnel (non-COGS)":      dict(share=0.047, drift=0.0006, vol=0.015),
    "IT & Systems":               dict(share=0.017, drift=0.0010, vol=0.03),
}

CAPEX_CATEGORIES = [
    ("Fiber Network Expansion", "Growth", 0.40),
    ("5G Mobile Network Build-out", "Growth", 0.22),
    ("Data Center & Core Infrastructure", "Growth", 0.10),
    ("IT Systems & Digital Platforms", "Growth", 0.08),
    ("Network Maintenance & Upgrades", "Maintenance", 0.14),
    ("Fleet & Field Equipment", "Maintenance", 0.06),
]

REGIONS = ["Capital Region", "North Region", "South Region", "East Region"]

COST_CENTERS = [
    "Network Operations", "Customer Care & Call Center", "Field Operations & Installation",
    "IT & Software Engineering", "Sales & Business Development", "Marketing & Brand",
    "Billing & Revenue Assurance", "Human Resources", "Finance & Accounting",
    "Data & Cybersecurity", "Procurement & Supply Chain", "Legal & Regulatory Affairs",
]

DEBT_TRANCHES = [
    dict(id="TR-A", lender="Senior Bank Loan A", principal=78_000_000, rate=0.0625, issue="2021-06-01", maturity="2029-06-01", amort="Amortizing"),
    dict(id="TR-B", lender="Senior Bank Loan B", principal=52_000_000, rate=0.0690, issue="2023-03-01", maturity="2030-03-01", amort="Amortizing"),
    dict(id="TR-C", lender="Corporate Bond", principal=104_000_000, rate=0.0580, issue="2022-09-01", maturity="2032-09-01", amort="Bullet"),
    dict(id="TR-D", lender="Revolving Credit Facility", principal=26_000_000, rate=0.0710, issue="2024-01-01", maturity="2027-01-01", amort="Revolver"),
]


def month_range(n_months, end_month=TODAY):
    return pd.date_range(end=end_month, periods=n_months, freq="MS")


# ----------------------------------------------------------------------
# 2. REVENUE & SUBSCRIBER ECONOMICS BY SEGMENT
# ----------------------------------------------------------------------
def generate_revenue_by_segment():
    months = month_range(HISTORY_MONTHS)
    records = []

    # Residential segments: sized as a share of the total subscriber base
    for seg, cfg in SEGMENTS.items():
        latest_subs = TOTAL_SUBSCRIBERS_LATEST * cfg["sub_share"]
        start_subs = latest_subs / ((1 + cfg["sub_growth"]) ** (HISTORY_MONTHS - 1))
        start_arpu = cfg["arpu"] / ((1 + cfg["arpu_drift"]) ** (HISTORY_MONTHS - 1))

        subs = start_subs
        arpu = start_arpu
        for i, m in enumerate(months):
            noise_subs = np.random.normal(1.0, 0.006)
            noise_arpu = np.random.normal(1.0, 0.012)
            subs = subs * (1 + cfg["sub_growth"]) * noise_subs
            arpu = arpu * (1 + cfg["arpu_drift"]) * noise_arpu
            revenue = subs * arpu
            records.append(dict(
                Month=m.date(), Segment=seg, Subscribers=int(round(subs)),
                ARPU_USD=round(arpu, 2), RevenueUSD=round(revenue, 0),
                GrossMarginPct=round(cfg["gross_margin"] * np.random.normal(1.0, 0.015), 4),
            ))

    # B2B segments: sized as their own small account population (not a share
    # of the residential subscriber base -- a handful of large contracts).
    for seg, cfg in B2B_SEGMENTS.items():
        latest_accounts = cfg["accounts"]
        start_accounts = latest_accounts / ((1 + cfg["account_growth"]) ** (HISTORY_MONTHS - 1))
        start_arpu = cfg["arpu"] / ((1 + cfg["arpu_drift"]) ** (HISTORY_MONTHS - 1))

        accounts = start_accounts
        arpu = start_arpu
        for i, m in enumerate(months):
            noise_accounts = np.random.normal(1.0, 0.008)
            noise_arpu = np.random.normal(1.0, 0.015)
            accounts = accounts * (1 + cfg["account_growth"]) * noise_accounts
            arpu = arpu * (1 + cfg["arpu_drift"]) * noise_arpu
            revenue = accounts * arpu
            records.append(dict(
                Month=m.date(), Segment=seg, Subscribers=int(round(accounts)),
                ARPU_USD=round(arpu, 2), RevenueUSD=round(revenue, 0),
                GrossMarginPct=round(cfg["gross_margin"] * np.random.normal(1.0, 0.015), 4),
            ))

    df = pd.DataFrame(records)
    return df


# ----------------------------------------------------------------------
# 3. MONTHLY CONSOLIDATED P&L
# ----------------------------------------------------------------------
def generate_pnl(revenue_df, debt_df):
    months = month_range(HISTORY_MONTHS)
    monthly_revenue = revenue_df.groupby("Month")["RevenueUSD"].sum()
    monthly_cogs = revenue_df.assign(COGS=lambda d: d["RevenueUSD"] * (1 - d["GrossMarginPct"])) \
                              .groupby("Month")["COGS"].sum()
    # Actual weighted interest expense from the real debt schedule, so the
    # P&L, balance sheet and debt schedule all tie to the same numbers.
    debt_df = debt_df.copy()
    debt_df["MonthlyInterestUSD"] = debt_df["OutstandingBalanceUSD"] * debt_df["InterestRatePct"] / 12
    monthly_interest = debt_df.groupby("Month")["MonthlyInterestUSD"].sum()

    records = []
    for i, m in enumerate(months):
        md = m.date()
        revenue = monthly_revenue[md]
        cogs = monthly_cogs[md]
        gross_profit = revenue - cogs

        opex_total = 0
        opex_breakdown = {}
        for cat, cfg in OPEX_CATEGORIES.items():
            base = revenue * cfg["share"] * ((1 + cfg["drift"]) ** i)
            val = max(base * np.random.normal(1.0, cfg["vol"]), 0)
            opex_breakdown[cat] = val
            opex_total += val

        ebitda = gross_profit - opex_total
        da = revenue * np.random.normal(0.085, 0.006)  # depreciation & amortization, capital-intensive telecom
        ebit = ebitda - da

        interest = monthly_interest.get(md, 0)

        pretax_income = ebit - interest
        tax_rate = 0.24
        tax = max(pretax_income, 0) * tax_rate
        net_income = pretax_income - tax

        rec = dict(Month=md, RevenueUSD=round(revenue, 0), COGSUSD=round(cogs, 0),
                   GrossProfitUSD=round(gross_profit, 0))
        for cat, val in opex_breakdown.items():
            rec[f"OPEX_{cat.replace(' ', '_').replace('&', 'and')}"] = round(val, 0)
        rec.update(dict(
            TotalOPEXUSD=round(opex_total, 0), EBITDA_USD=round(ebitda, 0),
            EBITDA_MarginPct=round(ebitda / revenue, 4),
            DepreciationAmortizationUSD=round(da, 0), EBIT_USD=round(ebit, 0),
            InterestExpenseUSD=round(interest, 0), PretaxIncomeUSD=round(pretax_income, 0),
            TaxExpenseUSD=round(tax, 0), NetIncomeUSD=round(net_income, 0),
            NetMarginPct=round(net_income / revenue, 4),
        ))
        records.append(rec)
    return pd.DataFrame(records)


# ----------------------------------------------------------------------
# 4. CAPITAL PROJECTS (CAPEX PORTFOLIO)
# ----------------------------------------------------------------------
def generate_capex_projects(revenue_df):
    months = month_range(HISTORY_MONTHS)
    monthly_revenue = revenue_df.groupby("Month")["RevenueUSD"].sum()
    records = []
    proj_id = 1
    for i, m in enumerate(months):
        revenue = monthly_revenue[m.date()]
        capex_intensity = np.random.normal(0.145, 0.018)  # ~14.5% of revenue, typical capital-intensive telecom
        month_capex_budget = revenue * capex_intensity

        for cat, capex_type, share in CAPEX_CATEGORIES:
            planned = month_capex_budget * share * np.random.normal(1.0, 0.10)
            actual = planned * np.random.normal(1.0, 0.09)
            region = random.choice(REGIONS)
            status = "Completed" if i < HISTORY_MONTHS - 3 else random.choice(["In Progress", "In Progress", "Completed"])
            records.append(dict(
                ProjectID=f"CPX-{proj_id:04d}", Month=m.date(), Category=cat, CapexType=capex_type,
                Region=region, PlannedBudgetUSD=round(planned, 0), ActualSpendUSD=round(actual, 0),
                VarianceUSD=round(actual - planned, 0), Status=status,
            ))
            proj_id += 1
    return pd.DataFrame(records)


# ----------------------------------------------------------------------
# 5. DEBT SCHEDULE
# ----------------------------------------------------------------------
def generate_debt_schedule():
    months = month_range(HISTORY_MONTHS)
    records = []
    for t in DEBT_TRANCHES:
        issue = pd.Timestamp(t["issue"])
        maturity = pd.Timestamp(t["maturity"])
        total_term_months = max((maturity.year - issue.year) * 12 + (maturity.month - issue.month), 1)

        for m in months:
            if m < issue:
                outstanding = 0
            elif t["amort"] == "Bullet":
                outstanding = t["principal"] if m < maturity else 0
            elif t["amort"] == "Revolver":
                # Fluctuating drawn balance
                outstanding = t["principal"] * np.clip(np.random.normal(0.55, 0.20), 0.1, 1.0)
            else:  # Amortizing
                months_elapsed = (m.year - issue.year) * 12 + (m.month - issue.month)
                pct_remaining = max(0, 1 - months_elapsed / total_term_months)
                outstanding = t["principal"] * pct_remaining

            records.append(dict(
                TrancheID=t["id"], Lender=t["lender"], Month=m.date(),
                InterestRatePct=t["rate"], AmortizationType=t["amort"],
                OriginalPrincipalUSD=t["principal"], OutstandingBalanceUSD=round(outstanding, 0),
                MaturityDate=maturity.date(),
            ))
    return pd.DataFrame(records)


# ----------------------------------------------------------------------
# 6/7. BALANCE SHEET + CASH FLOW (built together in one pass so the
#      balance sheet balances EXACTLY by construction -- see derivation
#      in the project README. Cash is the model's plug, tied out through
#      the cash flow statement, which is standard 3-statement-model practice.)
# ----------------------------------------------------------------------
def generate_balance_sheet_and_cashflow(pnl_df, capex_df, debt_df):
    months = month_range(HISTORY_MONTHS)
    monthly_capex_total = capex_df.groupby("Month")["ActualSpendUSD"].sum()
    monthly_debt_total = debt_df.groupby("Month")["OutstandingBalanceUSD"].sum()

    OTHER_CURRENT_ASSETS = 8_000_000  # held constant -> zero delta, no cash-flow leakage
    COMMON_EQUITY = 140_000_000       # held constant -> all equity movement flows through retained earnings

    bs_records, cf_records = [], []
    prev_ar = prev_ap = prev_debt = prev_ppe = prev_intangibles = prev_cash = prev_re = None

    for i, m in enumerate(months):
        md = m.date()
        pnl = pnl_df.loc[pnl_df["Month"] == md].iloc[0]
        revenue, net_income, da = pnl["RevenueUSD"], pnl["NetIncomeUSD"], pnl["DepreciationAmortizationUSD"]
        capex = monthly_capex_total.get(md, 0)
        debt_total = monthly_debt_total.get(md, 0)

        ar = revenue * np.random.normal(1.15, 0.03)          # ~35 days sales outstanding
        ap = pnl["TotalOPEXUSD"] * np.random.normal(0.55, 0.04)
        dep_ppe = da * 0.90
        amort_intangibles = da * 0.10
        dividends = max(net_income, 0) * 0.35

        if i == 0:
            # Seed the very first month's balances so Assets0 = Liabilities0 + Equity0
            # exactly; every subsequent month balances automatically via the roll-forward.
            cash = 12_000_000
            ppe_net = 310_000_000
            intangibles = 48_000_000
            total_assets_0 = cash + ar + OTHER_CURRENT_ASSETS + ppe_net + intangibles
            total_liabilities_0 = ap + debt_total
            retained_earnings = total_assets_0 - total_liabilities_0 - COMMON_EQUITY
            cfo = cfi = cff = net_change_cash = float("nan")  # no prior period to diff against
        else:
            d_ar = ar - prev_ar
            d_ap = ap - prev_ap
            d_debt = debt_total - prev_debt

            cfo = net_income + da - d_ar + d_ap
            cfi = -capex
            cff = d_debt - dividends
            net_change_cash = cfo + cfi + cff

            cash = prev_cash + net_change_cash
            ppe_net = prev_ppe + capex - dep_ppe
            intangibles = prev_intangibles - amort_intangibles
            retained_earnings = prev_re + net_income - dividends

        current_assets = cash + ar + OTHER_CURRENT_ASSETS
        non_current_assets = ppe_net + intangibles
        total_assets = current_assets + non_current_assets

        current_portion_debt = debt_total * 0.08
        long_term_debt = debt_total * 0.92
        current_liabilities = ap + current_portion_debt
        total_liabilities = current_liabilities + long_term_debt

        total_equity = COMMON_EQUITY + retained_earnings
        balance_check = total_assets - (total_liabilities + total_equity)

        bs_records.append(dict(
            Month=md, CashUSD=round(cash, 0), AccountsReceivableUSD=round(ar, 0),
            OtherCurrentAssetsUSD=OTHER_CURRENT_ASSETS, CurrentAssetsUSD=round(current_assets, 0),
            PPE_NetUSD=round(ppe_net, 0), IntangiblesUSD=round(intangibles, 0),
            NonCurrentAssetsUSD=round(non_current_assets, 0), TotalAssetsUSD=round(total_assets, 0),
            AccountsPayableUSD=round(ap, 0), CurrentPortionDebtUSD=round(current_portion_debt, 0),
            CurrentLiabilitiesUSD=round(current_liabilities, 0),
            LongTermDebtUSD=round(long_term_debt, 0), TotalLiabilitiesUSD=round(total_liabilities, 0),
            CommonEquityUSD=COMMON_EQUITY, RetainedEarningsUSD=round(retained_earnings, 0),
            TotalEquityUSD=round(total_equity, 0), BalanceCheckUSD=round(balance_check, 2),
        ))

        if i > 0:
            fcf = cfo - capex
            cf_records.append(dict(
                Month=md, CashFromOperationsUSD=round(cfo, 0), CashFromInvestingUSD=round(cfi, 0),
                CashFromFinancingUSD=round(cff, 0), NetChangeInCashUSD=round(net_change_cash, 0),
                EndingCashUSD=round(cash, 0), FreeCashFlowUSD=round(fcf, 0),
                DividendsPaidUSD=round(dividends, 0),
            ))

        prev_ar, prev_ap, prev_debt = ar, ap, debt_total
        prev_ppe, prev_intangibles, prev_cash, prev_re = ppe_net, intangibles, cash, retained_earnings

    return pd.DataFrame(bs_records), pd.DataFrame(cf_records)


# ----------------------------------------------------------------------
# 8. BUDGET VS ACTUAL (by cost center, monthly, last 24 months)
# ----------------------------------------------------------------------
def generate_budget_vs_actual(pnl_df, months_back=24):
    months = month_range(months_back)
    records = []
    # Each cost center gets a persistent "discipline" trait so some run hot, some run cold
    discipline = {cc: np.random.normal(1.0, 0.05) for cc in COST_CENTERS}
    drift = {cc: np.random.uniform(-0.003, 0.006) for cc in COST_CENTERS}

    for i, m in enumerate(months):
        md = m.date()
        revenue = pnl_df.loc[pnl_df["Month"] == md, "RevenueUSD"].values[0]
        for cc in COST_CENTERS:
            base_budget = revenue * np.random.uniform(0.015, 0.045)
            budget = base_budget
            actual = budget * discipline[cc] * (1 + drift[cc] * i) * np.random.normal(1.0, 0.06)
            records.append(dict(
                Month=md, CostCenter=cc, BudgetedUSD=round(budget, 0), ActualUSD=round(actual, 0),
                VarianceUSD=round(actual - budget, 0), VariancePct=round((actual - budget) / budget, 4),
            ))
    return pd.DataFrame(records)


# ----------------------------------------------------------------------
# 9. CUSTOMER ECONOMICS BY SEGMENT
# ----------------------------------------------------------------------
def generate_customer_economics(revenue_df):
    latest_month = revenue_df["Month"].max()
    records = []
    all_segments = {**SEGMENTS, **B2B_SEGMENTS}
    for seg, cfg in all_segments.items():
        latest = revenue_df[(revenue_df["Segment"] == seg) & (revenue_df["Month"] == latest_month)].iloc[0]
        arpu = latest["ARPU_USD"]
        gross_margin = latest["GrossMarginPct"]

        monthly_gross_profit_per_sub = arpu * gross_margin
        churn_rate_monthly = {
            "Residential Fiber": 0.011, "Residential Mobile": 0.019, "Residential TV/Bundles": 0.026,
            "Business & Enterprise": 0.007, "Wholesale & Interconnect": 0.004,
        }[seg]
        # Cap the assumed average customer lifetime at 60 months (5 years) --
        # a standard practical adjustment in customer economics: extrapolating
        # 1/churn indefinitely overstates LTV for very low-churn segments
        # (e.g. wholesale carrier contracts would otherwise imply 20+ year
        # lifetimes at full profit certainty, which no finance team would
        # actually underwrite an LTV model on).
        avg_lifetime_months = min(1 / churn_rate_monthly, 60)
        ltv = monthly_gross_profit_per_sub * avg_lifetime_months

        cac = {
            "Residential Fiber": 165, "Residential Mobile": 60, "Residential TV/Bundles": 95,
            "Business & Enterprise": 2400, "Wholesale & Interconnect": 8500,
        }[seg]
        ltv_cac_ratio = ltv / cac
        payback_months = cac / monthly_gross_profit_per_sub

        records.append(dict(
            Segment=seg, ARPU_USD=arpu, GrossMarginPct=gross_margin,
            MonthlyChurnRatePct=churn_rate_monthly, AvgCustomerLifetimeMonths=round(avg_lifetime_months, 1),
            CAC_USD=cac, LTV_USD=round(ltv, 0), LTV_CAC_Ratio=round(ltv_cac_ratio, 2),
            PaybackPeriodMonths=round(payback_months, 1),
        ))
    return pd.DataFrame(records)


if __name__ == "__main__":
    import os
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    print("Generating TelNova Communications synthetic finance dataset...")

    revenue = generate_revenue_by_segment()
    print(f"  Revenue records: {len(revenue)} ({HISTORY_MONTHS} months x {len(SEGMENTS) + len(B2B_SEGMENTS)} segments)")

    debt = generate_debt_schedule()
    print(f"  Debt schedule records: {len(debt)}")

    pnl = generate_pnl(revenue, debt)
    print(f"  P&L records: {len(pnl)} months")

    capex = generate_capex_projects(revenue)
    print(f"  Capex project records: {len(capex)}")

    balance, cashflow = generate_balance_sheet_and_cashflow(pnl, capex, debt)
    print(f"  Balance sheet records: {len(balance)} months")
    print(f"  Cash flow records: {len(cashflow)} months")

    budget = generate_budget_vs_actual(pnl)
    print(f"  Budget vs actual records: {len(budget)}")

    cust_econ = generate_customer_economics(revenue)
    print(f"  Customer economics records: {len(cust_econ)}")

    revenue.to_csv(os.path.join(SCRIPT_DIR, "_cache_revenue.csv"), index=False)
    pnl.to_csv(os.path.join(SCRIPT_DIR, "_cache_pnl.csv"), index=False)
    capex.to_csv(os.path.join(SCRIPT_DIR, "_cache_capex.csv"), index=False)
    debt.to_csv(os.path.join(SCRIPT_DIR, "_cache_debt.csv"), index=False)
    balance.to_csv(os.path.join(SCRIPT_DIR, "_cache_balance.csv"), index=False)
    cashflow.to_csv(os.path.join(SCRIPT_DIR, "_cache_cashflow.csv"), index=False)
    budget.to_csv(os.path.join(SCRIPT_DIR, "_cache_budget.csv"), index=False)
    cust_econ.to_csv(os.path.join(SCRIPT_DIR, "_cache_customer_econ.csv"), index=False)
    print("Cached intermediate CSVs. Ready for forecast_engine.py and build_workbook.py")
