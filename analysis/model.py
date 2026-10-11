"""
Aegis Systems: survival analysis on time to quiet quitting.

Converts the person-month panel data into one row per engineer (duration,
event observed), then fits:
  1. Kaplan-Meier curves, overall and split by team, to show how survival
     to "still engaged" differs by external mobility.
  2. A Cox proportional hazards model to quantify which covariates raise
     or lower the hazard of quiet quitting, holding others constant.

"Event" here = crossing into Quiet_Quitting. Voluntary_Exit before that
point is treated as censored (we never observed them disengage, because
they left first) rather than as the event itself. That's a deliberate
choice: this analysis is about disengagement, not departure.

Usage:
    python model.py
Produces:
    model_results.json
"""

import json

import numpy as np
import pandas as pd
from lifelines import KaplanMeierFitter, CoxPHFitter

TEAM_MOBILITY = {
    "Platform Infrastructure": 0.28,
    "DevOps / SRE": 0.34,
    "Backend Engineering": 0.46,
    "Data Engineering": 0.50,
    "ML Platform": 0.71,
}


def build_subject_table(panel):
    """Collapse person-month rows into one row per engineer: duration until
    quiet quitting (event=1) or last observed month, censored (event=0) if
    they never crossed into quiet quitting before the window ended or they
    voluntarily exited first."""

    rows = []
    for emp_id, g in panel.groupby("employee_id"):
        g = g.sort_values("month_index")
        first = g.iloc[0]
        qq_rows = g[g["status"] == "Quiet_Quitting"]

        if len(qq_rows) > 0:
            duration = int(qq_rows.iloc[0]["month_index"])
            event = 1
        else:
            duration = int(g.iloc[-1]["month_index"])
            event = 0  # censored: window ended or they voluntarily exited first

        rows.append({
            "employee_id": emp_id,
            "team": first["team"],
            "mobility": TEAM_MOBILITY[first["team"]],
            "tenure_at_start": int(first["tenure_months"]) - 1,
            "duration": duration,
            "event": event,
            # covariates at time of entry, as baseline predictors
            "start_ai_anxiety": float(first["ai_displacement_anxiety"]),
            "start_psych_safety": float(first["psychological_safety_voice"]),
            "max_downsize_ratio": float(g["team_downsize_ratio"].max()),
            "any_reorg": bool(g["management_layer_shift"].any()),
        })

    return pd.DataFrame(rows)


def main():
    panel = pd.read_csv("../data/aegis_systems_clean.csv")
    subjects = build_subject_table(panel)

    print(f"Subjects: {len(subjects)}")
    print(f"Events (crossed into quiet quitting): {subjects['event'].sum()}")
    print(f"Censored: {(subjects['event'] == 0).sum()}")

    # --- Kaplan-Meier, overall ---
    kmf = KaplanMeierFitter()
    kmf.fit(subjects["duration"], event_observed=subjects["event"], label="All engineers")
    median_survival = kmf.median_survival_time_

    # --- Kaplan-Meier, by team ---
    km_by_team = {}
    for team in TEAM_MOBILITY:
        sub = subjects[subjects["team"] == team]
        if len(sub) < 10:
            continue
        kmf_team = KaplanMeierFitter()
        kmf_team.fit(sub["duration"], event_observed=sub["event"], label=team)
        km_by_team[team] = {
            "median_survival_months": None
            if pd.isna(kmf_team.median_survival_time_)
            else float(kmf_team.median_survival_time_),
            "n": int(len(sub)),
        }

    # --- Cox proportional hazards ---
    cox_df = subjects[[
        "duration", "event", "mobility", "tenure_at_start",
        "start_ai_anxiety", "start_psych_safety", "max_downsize_ratio", "any_reorg",
    ]].copy()
    cox_df["any_reorg"] = cox_df["any_reorg"].astype(int)

    cph = CoxPHFitter()
    cph.fit(cox_df, duration_col="duration", event_col="event")

    hazard_ratios = {}
    for covariate in cph.params_.index:
        hazard_ratios[covariate] = {
            "hazard_ratio": float(np.exp(cph.params_[covariate])),
            "p_value": float(cph.summary.loc[covariate, "p"]),
        }

    print("\nCox model hazard ratios (>1 raises risk of quiet quitting, <1 lowers it):")
    for cov, vals in hazard_ratios.items():
        print(f"  {cov:22s} HR={vals['hazard_ratio']:.3f}  p={vals['p_value']:.4f}")

    output = {
        "n_subjects": int(len(subjects)),
        "n_events": int(subjects["event"].sum()),
        "n_censored": int((subjects["event"] == 0).sum()),
        "overall_median_survival_months": None
        if pd.isna(median_survival)
        else float(median_survival),
        "km_by_team": km_by_team,
        "cox_hazard_ratios": hazard_ratios,
        "cox_concordance": float(cph.concordance_index_),
    }

    with open("model_results.json", "w") as f:
        json.dump(output, f, indent=2)

    print("\nSaved model_results.json")


if __name__ == "__main__":
    main()
