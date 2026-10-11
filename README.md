# Aegis Systems: Quiet Quitting Survival Analysis

**Does low attrition mean a team is healthy, or are people just stuck?**

[Live dashboard](https://aegis-systems-survival-analysis-tnnbzkort5zuxjsj8lkj67.streamlit.app/)

## Context

On March 31, 2026, Oracle began cutting jobs worldwide, with termination emails reportedly landing in employees' inboxes around 6 a.m. Early estimates put the number between 20,000 and 30,000 people, and SkillSyncer's layoffs tracker lists it as the largest single layoff of 2026 at 30,000. CNBC later put the final tally at 21,000, and Oracle started another round of cuts in September. The reductions were widely reported as tied to funding the company's AI infrastructure buildout. Sources: [Forbes](https://www.forbes.com/sites/maryroeloffs/2026/06/23/ai-cost-21000-jobs-at-oracle-this-year-and-more-layoffs-could-be-coming/), [Computerworld's 2026 layoffs timeline](https://www.computerworld.com/article/3816579/tech-layoffs-this-year-a-timeline.html), and the [SkillSyncer Layoffs Tracker](https://skillsyncer.com/layoffs-tracker).

Oracle is one name in a much larger wave. As of September 24, 2026, the SkillSyncer tracker, which counts announced cuts with a reported headcount, showed 519 layoff events affecting 225,122 workers across industries, 58,386 of them in software and tech. The tracker data is published under CC BY 4.0.

That event is the starting point for this case study, not its subject. I am not making any claim about Oracle's workforce or what its employees experienced after the cuts. What I wanted to test was the pattern behind it. When cuts this large are happening across the industry, the people who stay have fewer comparable roles to move to. A team with a low voluntary exit rate can look stable on a dashboard while some of its people have quietly stopped investing in the work, because leaving is a worse option than it was a few years ago.

**Aegis Systems** is a fictional 800 person engineering department going through three layoff waves, built to examine that question on synthetic data.

## The hypothesis

Two ideas shaped the variables in this dataset:

* **Job Demands Resources model.** Disengagement depends on whether people have enough support and control to meet the demands placed on them, not only on how much work they carry.
* **Psychological safety** (Amy Edmondson). Whether people believe speaking up will lead anywhere shapes whether they stay engaged, go silent, or leave.

The working hypothesis was that attrition on its own is a poor health signal. Teams with low external mobility, where people have little chance of finding a comparable role elsewhere, should show fewer voluntary exits, but disengagement should not disappear. It should stay on the team instead of walking out the door.

The model tests which factors speed up the slide into quiet quitting. How mobility affects disengagement is part of what it checks, and the result is reported honestly under Findings.

## Ask → Prepare → Analyze → Share → Act

**Ask:** What predicts how quickly an engineer crosses into quiet quitting, and can an organization act on those factors before it happens?

**Prepare:** `data/generate_data.py` builds an 800 engineer synthetic population with Python Faker and NumPy, observed over 36 months across five teams. It produces a person month panel, one row per engineer per month, with tenure, team downsizing exposure, management layer shifts, AI displacement anxiety, psychological safety, and two behavioral proxies (Slack response latency and off hours commits). Each engineer has one of three monthly statuses: Productive Retained, Quiet Quitting, or Voluntary Exit. Quiet quitting is sticky once crossed, and voluntary exit is terminal. A raw export is generated separately with duplicate rows, inconsistent team casing, and missing values, the way a real HR export would look.

**Analyze:** `analysis/clean_data.sql` documents the cleaning steps: deduplicating on employee and month, normalizing team names, and casting types. `analysis/model.py` collapses the panel to one row per engineer, then fits Kaplan Meier curves overall and by team, plus a Cox proportional hazards model. See the next section for why survival analysis.

**Share:** The [live dashboard](https://aegis-systems-survival-analysis-tnnbzkort5zuxjsj8lkj67.streamlit.app/) shows the survival curves by team and the ranked hazard ratios, and lets you simulate a company wide change in AI anxiety, psychological safety, or downsizing exposure and watch the predicted quiet quitting rate move.

**Act:** See [Findings](#findings) and [What this suggests an organization do](#what-this-suggests-an-organization-do) below.

## Why survival analysis, and what lifelines does

The question here is not whether someone quietly disengages, but when. A standard classifier would only look at a snapshot, and it would throw away the timing. It would also mishandle people who left before disengaging, or who were still engaged when the 36 months ended. Survival analysis is built for exactly this. Those engineers are treated as censored, meaning we know they stayed engaged up to a point but not what happened after.

[lifelines](https://lifelines.readthedocs.io/) is the Python library that does the fitting. It is used in two places:

* **Kaplan Meier estimator.** Gives the share of engineers who had not yet crossed into quiet quitting at each month, overall and for each team. These are the curves on the dashboard.
* **Cox proportional hazards model.** Estimates how much each factor raises or lowers the hazard (the instantaneous risk) of crossing into quiet quitting while holding the others constant. A hazard ratio above 1 speeds the slide, below 1 slows it. The concordance index measures how well the model ranks who crosses earlier.

Both the app and `analysis/model.py` depend on it, which is why `lifelines` is listed in `requirements.txt`.

## Findings

On this synthetic population, 311 of 800 engineers crossed into quiet quitting and 489 were censored. The Kaplan Meier estimate puts the share who have crossed by month 36 at 47.5%. The Cox model has a concordance of 0.79.

Hazard ratios from the Cox model:

* **Psychological safety:** 0.33 per point on the 1 to 5 scale. Strongest protective factor.
* **AI displacement anxiety:** 2.86 per point on the 1 to 5 scale. Strongest risk factor.
* **Team downsizing exposure:** 49.7 per full 100 point swing, which works out to about 1.48 per 10 percentage points. Significant, but see the limitations below.
* **Management layer shift:** 1.23. Not significant at the usual 0.05 level (p = 0.07).
* **Team external mobility:** 1.43. Not significant (p = 0.40).
* **Tenure at the start of observation:** 0.996 per month. Not significant (p = 0.24).

The clearest signal is that how safe people feel speaking up, and how anxious they are about being replaced by AI, matter far more than tenure or team. Mobility did not show a measurable effect on how fast people cross into quiet quitting, and the team curves overlap heavily. Only Backend Engineering reaches a median survival time inside the window, at 36 months. The other four teams never drop below 50% survival.

So the data does not show that low mobility teams disengage faster or slower. What it does show is that disengagement is widespread everywhere (nearly half the org by month 36), and that the factors driving it are psychological, not structural. Since the generator was written so that mobility affects exits rather than onset, this is the expected result and a useful sanity check on the pipeline.

## What this suggests an organization do

Grounded in the model, with the caveats below:

1. **Treat psychological safety as the first lever.** A one point improvement carries the largest protective hazard ratio in the model. Visible follow through on concerns that people raise matters more than an open door policy.
2. **Address AI displacement anxiety directly.** Clear communication about which roles are changing and how affects the second strongest factor. Silence leaves people to assume the worst.
3. **Do not read a low exit rate as a clean bill of health.** In a tight market, people stay because they have to. Pair attrition numbers with engagement signals before concluding a team is fine.

## Limitations

* **All effects are built in.** The generator drives quiet quitting from anxiety, safety, and downsizing by design, so the model recovering those effects confirms the pipeline works. It is not evidence about real workforces.
* **Look ahead bias.** Downsizing exposure and management layer shift are computed over each engineer's entire observed window, including months after they crossed into quiet quitting. This likely inflates the downsizing hazard ratio. A time varying covariate model would fix it.
* **Voluntary exits are treated as censored.** That fits a question about disengagement, but it means the Kaplan Meier rate is not the same as the raw 311 of 800 (38.9%).
* **The simulator is a what if tool, not a causal estimate.** It applies the fitted hazard ratios to the overall observed survival curve under a proportional hazards assumption.
* **The behavioral proxy columns are hypothetical.** Slack latency and off hours commits are part of a fictional instrumented dataset. They are not a claim that real engineering teams are monitored this way, and they are not used in the model.

## Run it locally

Prefer not to clone anything first? Try the [live dashboard](https://aegis-systems-survival-analysis-tnnbzkort5zuxjsj8lkj67.streamlit.app/) directly.

```bash
git clone https://github.com/professorpasqua-byte/aegis-systems-survival-analysis.git
cd aegis-systems-survival-analysis
pip install -r requirements.txt
streamlit run app.py
```

To regenerate the dataset or refit the model from scratch:

```bash
cd data && python generate_data.py
cd ../analysis && python model.py
```

## Repo structure

```
aegis-systems-survival-analysis/
├── data/
│   ├── generate_data.py                 # Faker based synthetic data generator
│   ├── aegis_systems_raw.csv            # messy export, as generated
│   └── aegis_systems_clean.csv          # analysis ready person month panel
├── analysis/
│   ├── clean_data.sql                   # documented dedup and normalize pipeline
│   ├── model.py                         # Kaplan Meier and Cox fit with lifelines
│   └── model_results.json               # fitted results
├── app.py                               # Streamlit app
├── requirements.txt
├── .gitignore
└── README.md
```

## Built with

Python, pandas, NumPy, Faker, lifelines, Streamlit, and SQL (DuckDB style syntax for the documented cleaning pipeline).

## A note on the data

Aegis Systems, every engineer in this dataset, and every figure from the model are synthetic. The only real facts in this project are the layoff events and tracker totals cited in the context, used to explain why the scenario matters. No real individual's data, survey responses, or employment history appears anywhere here. The cleaning pipeline is documented in SQL, while the clean file itself is written directly by `generate_data.py` before noise is added to the raw version.

---

**Nwafor Martins**, People Analytics Engineer & I-O Psychology Consultant
[Email](mailto:nwaforchubby@gmail.com)
