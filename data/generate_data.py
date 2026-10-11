"""
Aegis Systems: The Silent Restructuring Crisis — synthetic data generator.

Aegis Systems is a fictional company running a fictional 800-person engineering
department through a wave of AI-driven restructuring. This script generates
person-period panel data: one row per engineer per month observed, not one
row per engineer, because the project tests a survival question (time until
an engineer quietly disengages) rather than a single snapshot classification.

The real anchor behind the premise: SkillSyncer's tracker recorded 225,000+
tech layoffs in 2026 (skillsyncer.com, as of October 2026). That figure is
cited as context for why engineers in this dataset have limited external
options, which is the mechanism the whole case study is built on.

Core hypothesis this dataset is built to test: teams with the lowest
voluntary exit rate are not healthier, they are teams where people have
nowhere better to go. Low external job mobility doesn't prevent
disengagement, it just traps it in place instead of letting it walk out
the door. Teams with more external options show the opposite pattern:
higher voluntary exit, but less quiet quitting, because people who
disengage simply leave rather than linger.

Three-class monthly status: Productive_Retained, Quiet_Quitting, Voluntary_Exit.
Quiet_Quitting is sticky (once an engineer crosses that threshold, they stay
flagged); Voluntary_Exit is terminal (no further rows for that engineer).

Behavioral proxy columns (Slack response latency delta, off-hours commit
delta) are explicitly a hypothetical instrumented dataset for this fictional
company. They are not a claim that real engineering teams are monitored this
way, and the README says so directly.

Usage:
    python generate_data.py
Produces:
    aegis_systems_raw.csv
    aegis_systems_clean.csv
"""

import numpy as np
import pandas as pd
from faker import Faker

fake = Faker()
Faker.seed(None)  # unseeded on purpose, so names vary on every run
np.random.seed(42)  # stats stay reproducible and isolated from name generation

N_ENGINEERS = 800
N_MONTHS = 36

TEAMS = {
    # team name: external_mobility (0-1, how easy it is to find a comparable
    # role elsewhere right now, given the 2026 layoff environment)
    "Platform Infrastructure": 0.28,
    "DevOps / SRE": 0.34,
    "Backend Engineering": 0.46,
    "Data Engineering": 0.50,
    "ML Platform": 0.71,
}
TEAM_NAMES = list(TEAMS.keys())
TEAM_WEIGHTS = [0.24, 0.18, 0.26, 0.17, 0.15]

# Three company-wide layoff waves during the observation window (month index).
# Each wave raises team_downsize_ratio for every team, unevenly.
LAYOFF_WAVES = [9, 19, 28]

QUIET_QUIT_THRESHOLD = 0.78
BASE_MONTHLY_EXIT_PROB = 0.010


def clip(x, lo, hi):
    return float(np.clip(x, lo, hi))


def main():
    raw_rows = []

    for i in range(N_ENGINEERS):
        employee_id = f"AE-{20000 + i}"
        team = np.random.choice(TEAM_NAMES, p=TEAM_WEIGHTS)
        mobility = TEAMS[team]

        # Tenure at the start of the observation window (months already
        # worked before month 1). Right-skewed, most engineers mid-career
        # at this company.
        tenure_at_start = int(clip(np.random.exponential(scale=18), 0, 96))

        # Starting psychometrics: somewhat healthier in low-downsize-history
        # teams, noisier everywhere.
        ai_anxiety = clip(np.random.normal(2.6, 0.9), 1, 5)
        psych_safety = clip(np.random.normal(3.2, 0.9), 1, 5)

        disengagement = clip(np.random.normal(0.2, 0.1), 0, 1)
        team_downsize_ratio = 0.0
        quiet_quitting = False
        last_reorg_month = None

        for month in range(1, N_MONTHS + 1):
            # Layoff waves raise this team's downsize ratio permanently.
            if month in LAYOFF_WAVES:
                team_downsize_ratio = clip(
                    team_downsize_ratio + np.random.uniform(0.04, 0.14), 0, 0.6
                )
                # Survivors' anxiety rises, trust in speaking up drops.
                ai_anxiety = clip(ai_anxiety + np.random.uniform(0.3, 0.8), 1, 5)
                psych_safety = clip(psych_safety - np.random.uniform(0.2, 0.6), 1, 5)

            # Occasional management layer shift (reorg), rare, independent of waves.
            reorg_this_month = np.random.random() < 0.02
            if reorg_this_month:
                last_reorg_month = month
            recent_reorg = (
                last_reorg_month is not None and month - last_reorg_month <= 2
            )

            # Slow natural drift in psychometrics month to month.
            ai_anxiety = clip(ai_anxiety + np.random.normal(0, 0.12), 1, 5)
            psych_safety = clip(psych_safety + np.random.normal(0, 0.12), 1, 5)

            # Disengagement signal this month from current covariates.
            signal = (
                0.35 * ((ai_anxiety - 3) / 2)
                - 0.35 * ((psych_safety - 3) / 2)
                + 0.25 * team_downsize_ratio
                + (0.15 if recent_reorg else 0.0)
                - 0.05 * min(tenure_at_start + month, 60) / 60
            )
            signal = clip(signal, -1, 1.3)

            # AR(1)-style persistence: disengagement doesn't reset each month,
            # it carries forward with new signal blended in.
            disengagement = clip(
                0.65 * disengagement
                + 0.35 * ((signal + 1) / 2)
                + np.random.normal(0, 0.05),
                0, 1,
            )

            if not quiet_quitting and disengagement > QUIET_QUIT_THRESHOLD:
                quiet_quitting = True

            status = "Quiet_Quitting" if quiet_quitting else "Productive_Retained"

            # Monthly voluntary exit probability. Mobility raises it.
            # Quiet quitters with real external options leave; quiet quitters
            # with few options stay disengaged instead, which is the whole
            # point of the dataset.
            exit_prob = BASE_MONTHLY_EXIT_PROB * (0.5 + mobility)
            if quiet_quitting:
                exit_prob *= (1.7 if mobility > 0.55 else 0.55)

            voluntary_exit = np.random.random() < exit_prob

            # Behavioral proxies: noisy, hypothetical, correlated with the
            # underlying disengagement signal and current team pressure.
            slack_latency_delta = round(
                disengagement * 9 + np.random.normal(0, 2.5), 1
            )
            off_hours_commits_delta = round(
                -1.2 * disengagement + 1.1 * team_downsize_ratio
                + np.random.normal(0, 1.2),
                1,
            )

            final_status = "Voluntary_Exit" if voluntary_exit else status

            raw_rows.append({
                "employee_id": employee_id,
                "name": fake.name(),
                "team": team,
                "month_index": month,
                "tenure_months": tenure_at_start + month,
                "team_downsize_ratio": round(team_downsize_ratio, 3),
                "management_layer_shift": recent_reorg,
                "ai_displacement_anxiety": round(ai_anxiety, 2),
                "psychological_safety_voice": round(psych_safety, 2),
                "slack_response_latency_delta": slack_latency_delta,
                "off_hours_commits_delta": off_hours_commits_delta,
                "status": final_status,
            })

            if voluntary_exit:
                break  # terminal: no further rows for this engineer

    df = pd.DataFrame(raw_rows)
    df.to_csv("aegis_systems_clean.csv", index=False)

    # Messy raw version, matching the convention of the other case studies:
    # inconsistent casing, a few duplicate rows, scattered missing values.
    raw = df.copy()
    raw["team"] = raw["team"].apply(
        lambda t: t.upper() if np.random.random() < 0.12 else t
    )
    dupe_rows = raw.sample(frac=0.02, random_state=1)
    raw = pd.concat([raw, dupe_rows], ignore_index=True)
    for col in ["ai_displacement_anxiety", "psychological_safety_voice", "slack_response_latency_delta"]:
        null_idx = raw.sample(frac=0.03, random_state=2).index
        raw.loc[null_idx, col] = np.nan
    raw = raw.sample(frac=1, random_state=3).reset_index(drop=True)
    raw.to_csv("aegis_systems_raw.csv", index=False)

    print(f"Engineers: {N_ENGINEERS}")
    print(f"Clean rows (person-months): {len(df)}")
    print(f"Raw rows (incl. duplicates): {len(raw)}")
    print(f"Status breakdown:\n{df['status'].value_counts(normalize=True).round(3)}")

    # Quick sanity check on the core hypothesis: does low-mobility correlate
    # with lower voluntary exit but higher quiet-quitting prevalence?
    df["mobility"] = df["team"].map(TEAMS)
    last_row_per_emp = df.sort_values("month_index").groupby("employee_id").last()
    by_team = last_row_per_emp.groupby("team").agg(
        mobility=("mobility", "first"),
        voluntary_exit_rate=("status", lambda s: (s == "Voluntary_Exit").mean()),
        quiet_quitting_rate=("status", lambda s: (s == "Quiet_Quitting").mean()),
    ).sort_values("mobility")
    print("\nBy team (sorted by external mobility, low to high):")
    print(by_team)


if __name__ == "__main__":
    main()
