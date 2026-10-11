"""
Aegis Systems: Does low attrition mean a team is healthy? — Streamlit app.

Fits Kaplan-Meier and Cox proportional hazards live from the panel data
(cheap at 800 subjects), shows survival curves by team, and lets the viewer
simulate a company-wide shift in AI anxiety, psychological safety, or
downsizing exposure, scored by the same fitted hazard ratios.
"""

import numpy as np
import pandas as pd
import streamlit as st
from lifelines import KaplanMeierFitter, CoxPHFitter

st.set_page_config(page_title="Aegis Systems: Quiet Quitting", page_icon="🧭", layout="wide")

TEAM_MOBILITY = {
    "Platform Infrastructure": 0.28,
    "DevOps / SRE": 0.34,
    "Backend Engineering": 0.46,
    "Data Engineering": 0.50,
    "ML Platform": 0.71,
}


@st.cache_data
def load_panel():
    return pd.read_csv("data/aegis_systems_clean.csv")


@st.cache_data
def build_subjects(panel: pd.DataFrame) -> pd.DataFrame:
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
            event = 0
        rows.append({
            "employee_id": emp_id,
            "team": first["team"],
            "mobility": TEAM_MOBILITY[first["team"]],
            "tenure_at_start": int(first["tenure_months"]) - 1,
            "duration": duration,
            "event": event,
            "start_ai_anxiety": float(first["ai_displacement_anxiety"]),
            "start_psych_safety": float(first["psychological_safety_voice"]),
            "max_downsize_ratio": float(g["team_downsize_ratio"].max()),
            "any_reorg": int(g["management_layer_shift"].any()),
        })
    return pd.DataFrame(rows)


@st.cache_data
def fit_models(subjects: pd.DataFrame):
    # Evaluate every curve on the same monthly grid (0 to max duration), not
    # each stratum's own sparse event times. Kaplan-Meier is a step function;
    # without a shared grid, combining strata produces misaligned points that
    # a line chart would connect with straight diagonals, misrepresenting a
    # step function as a smooth decline.
    timeline = list(range(0, int(subjects["duration"].max()) + 1))

    kmf = KaplanMeierFitter()
    kmf.fit(subjects["duration"], event_observed=subjects["event"])
    overall_sf = kmf.survival_function_at_times(timeline)
    overall_sf.index.name = "month"

    by_team_sf = {}
    for team in TEAM_MOBILITY:
        sub = subjects[subjects["team"] == team]
        if len(sub) < 10:
            continue
        kmf_t = KaplanMeierFitter()
        kmf_t.fit(sub["duration"], event_observed=sub["event"])
        by_team_sf[team] = kmf_t.survival_function_at_times(timeline)

    cox_df = subjects[[
        "duration", "event", "mobility", "tenure_at_start",
        "start_ai_anxiety", "start_psych_safety", "max_downsize_ratio", "any_reorg",
    ]].copy()
    cph = CoxPHFitter()
    cph.fit(cox_df, duration_col="duration", event_col="event")

    return overall_sf, by_team_sf, cph


panel = load_panel()
subjects = build_subjects(panel)
overall_sf, by_team_sf, cph = fit_models(subjects)

baseline_survival_36 = float(overall_sf.iloc[-1])
baseline_quiet_quit_rate = 1 - baseline_survival_36

# ----------------------------------------------------------------------
# Header
# ----------------------------------------------------------------------

st.title("🧭 Aegis Systems: Does low attrition mean a team is healthy?")
st.caption(
    "A synthetic survival analysis on a fictional company going through AI driven "
    "restructuring. Inspired by the 225,000+ real tech layoffs tracked by SkillSyncer "
    "in 2026. All data below is synthetic; Aegis Systems is a fictional company."
)

c1, c2, c3 = st.columns(3)
c1.metric("Engineers modeled", f"{len(subjects):,}")
c2.metric("Crossed into quiet quitting by month 36", f"{baseline_quiet_quit_rate:.1%}")
c3.metric("Cox model fit (concordance)", f"{cph.concordance_index_:.2f}")

st.divider()

# ----------------------------------------------------------------------
# Survival curves by team
# ----------------------------------------------------------------------

st.subheader("Survival curves by team")
st.markdown(
    "Each line shows the share of engineers on that team who had not yet "
    "crossed into quiet quitting, month by month. Lower external mobility "
    "does not mean a flatter line. It often means a slower decline, not no "
    "decline at all."
)

team_curve_df = pd.DataFrame(by_team_sf)
team_curve_df.index.name = "month"
st.line_chart(team_curve_df)

st.divider()

# ----------------------------------------------------------------------
# What predicts quiet quitting
# ----------------------------------------------------------------------

st.subheader("What predicts a faster slide into quiet quitting")

LABELS = {
    "mobility": "Team external mobility",
    "tenure_at_start": "Tenure at observation start (months)",
    "start_ai_anxiety": "AI displacement anxiety (1 to 5)",
    "start_psych_safety": "Psychological safety / voice (1 to 5)",
    "max_downsize_ratio": "Team downsizing exposure (0 to 1)",
    "any_reorg": "Experienced a management layer shift",
}

display_labels = []
log_hr_values = []
for c in cph.params_.index:
    beta = float(cph.params_[c])
    if c == "max_downsize_ratio":
        # Raw units are 0 to 1 (0 to 100 percentage points), so the raw
        # hazard ratio is "per 100 points," an unrealistic jump to show.
        # Rescale to a per-10-point basis for a readable, honest comparison.
        beta = beta * 0.1
        display_labels.append(LABELS[c] + " (per 10 points)")
    else:
        display_labels.append(LABELS[c])
    log_hr_values.append(beta)

hr_df = pd.DataFrame({
    "Factor": display_labels,
    "Log hazard ratio": log_hr_values,
}).set_index("Factor")

st.bar_chart(hr_df, horizontal=True)
st.caption(
    "Shown on a log scale so factors with very different units stay "
    "comparable: bars to the right speed up the slide into quiet quitting, "
    "bars to the left slow it down. AI displacement anxiety and "
    "psychological safety are the two strongest predictors here, not raw "
    "workload or tenure. Team downsizing exposure is rescaled to a per-10-"
    "percentage-point basis, since its raw hazard ratio is calibrated to a "
    "full 100-point jump, which never actually happens."
)

st.divider()

# ----------------------------------------------------------------------
# Simulator
# ----------------------------------------------------------------------

st.subheader("Simulate a company-wide change")
st.markdown(
    "Adjust what Aegis Systems could realistically change, applied uniformly "
    "across the whole engineering org, and see the predicted share of "
    "engineers who cross into quiet quitting by month 36 shift in response, "
    "scored by the same fitted hazard ratios."
)

sim_col, result_col = st.columns([3, 2])

HR = {c: float(np.exp(cph.params_[c])) for c in cph.params_.index}

with sim_col:
    anxiety_delta = st.slider(
        "Reduce AI displacement anxiety (points, 1 to 5 scale)",
        0.0, 2.0, 0.0, 0.1,
    )
    safety_delta = st.slider(
        "Improve psychological safety and voice (points, 1 to 5 scale)",
        0.0, 2.0, 0.0, 0.1,
    )
    downsize_delta = st.slider(
        "Reduce peak team downsizing exposure (percentage points)",
        0, 30, 0, 1,
    )

multiplier = (
    (HR["start_ai_anxiety"] ** -anxiety_delta)
    * (HR["start_psych_safety"] ** safety_delta)
    * (HR["max_downsize_ratio"] ** (-downsize_delta / 100))
)

new_survival = baseline_survival_36 ** multiplier
new_quiet_quit_rate = 1 - new_survival
delta = new_quiet_quit_rate - baseline_quiet_quit_rate

with result_col:
    st.metric(
        "Predicted quiet quitting rate under this scenario",
        f"{new_quiet_quit_rate:.1%}",
        delta=f"{delta:+.1%}",
        delta_color="inverse",
    )
    if abs(delta) < 0.001:
        st.info("Move a slider to see the model's prediction shift.")
    elif delta < 0:
        st.success(
            f"Projected to keep roughly {abs(delta) * len(subjects):.0f} more "
            f"engineers engaged in this population."
        )
    else:
        st.warning(
            f"Projected to push roughly {abs(delta) * len(subjects):.0f} more "
            f"engineers into quiet quitting in this population."
        )

st.caption(
    "Simplification stated plainly: this applies the fitted hazard ratios under "
    "a proportional hazards assumption to the observed baseline survival curve. "
    "It is a reasonable approximation for a what-if scenario, not a guarantee."
)

st.divider()

with st.expander("View the underlying synthetic data (person-month panel)"):
    st.dataframe(panel, use_container_width=True)

st.caption(
    "Methodology: synthetic panel data generated with Python Faker, "
    "Kaplan-Meier and Cox proportional hazards modeled with lifelines. "
    "Full pipeline and write-up in the repo README."
)
