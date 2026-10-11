# Aegis Systems: Quiet Quitting Survival Analysis

**Does low attrition mean a team is healthy, or are people just stuck?**

[Live dashboard](https://aegis-systems-survival-analysis-tnnbzkort5zuxjsj8lkj67.streamlit.app/)

## Context

On March 31, 2026, Oracle began cutting jobs worldwide, with termination emails reportedly landing in employees' inboxes around 6 a.m. Early estimates put the number between 20,000 and 30,000 people, and SkillSyncer's layoffs tracker lists it as the largest single layoff of 2026 at 30,000. CNBC later put the final tally at 21,000, and Oracle started another round of cuts in September. The reductions were widely reported as tied to funding the company's AI infrastructure buildout. Sources: [Forbes](https://www.forbes.com/sites/maryroeloffs/2026/06/23/ai-cost-21000-jobs-at-oracle-this-year-and-more-layoffs-could-be-coming/), [Computerworld's 2026 layoffs timeline](https://www.computerworld.com/article/3816579/tech-layoffs-this-year-a-timeline.html), and the [SkillSyncer Layoffs Tracker](https://skillsyncer.com/layoffs-tracker).

Oracle is one name in a much larger wave. As of September 24, 2026, the SkillSyncer tracker, which counts announced cuts with a reported headcount, showed 519 layoff events affecting 225,122 workers across industries, 58,386 of them in software and tech. The tracker data is published under CC BY 4.0.

That event is the starting point for this case study, not its subject. I am not making any claim about Oracle's workforce or what its employees experienced after the cuts. What I wanted to test was the pattern behind it. When cuts this large are happening across the industry, the people who stay have fewer comparable roles to move to. A team with a low voluntary exit rate can look stable on a dashboard while some of its people have quietly stopped investing in the work, because leaving is a worse option than it was a few years ago.

## The psychology behind the question

The variables in this dataset come from established work and organizational psychology, not from guesswork. Five frameworks shaped them:

* **Layoff survivor syndrome and job insecurity.** Research going back to Joel Brockner and others shows that people who keep their jobs after layoffs often respond with lower commitment, lower trust, and less effort, and that a perceived threat to job security predicts withdrawal and poorer wellbeing. This is the premise of the whole study. It is the basis for the team downsizing exposure variable and for AI displacement anxiety, which stands in for anticipatory insecurity about being replaced.
* **Conservation of Resources theory** (Stevan Hobfoll). People work to protect resources such as security, status, and support, and they pull back effort when those resources feel under threat. Each layoff wave in the generator drains resources, so anxiety rises and psychological safety falls after every wave.
* **Job Demands Resources model** (Arnold Bakker and Evangelia Demerouti). Disengagement depends on whether people have enough support and control to meet the demands placed on them, not only on how much work they carry.
* **Psychological safety** (Amy Edmondson). Whether people believe speaking up will lead anywhere shapes whether they stay engaged, go silent, or leave.
* **Exit, Voice, Loyalty and Neglect.** Albert Hirschman's framework, extended by Caryl Rusbult and colleagues, describes how people respond to dissatisfaction: leave, speak up, wait it out, or quietly withdraw effort. Quiet quitting here is the neglect response. When exit is hard because external mobility is low, and voice feels unsafe, neglect is what is left.

**Quiet quitting as a construct.** In this project, quiet quitting means a drop in work engagement, in the sense used by William Kahn and Wilmar Schaufeli: the person stays, but withdraws discretionary effort and psychological investment and does only the minimum. In the dataset it is operationalized as a hidden disengagement score crossing a threshold. That is a modeling choice, not a validated measurement.

The working hypothesis: **attrition alone is a poor health signal.** Where people have little external mobility, exit is blocked, so disengagement should show up as neglect instead of resignation. The model tests which factors speed up that slide, and the result for mobility is reported honestly under [What the model found](#what-the-model-found).

## How the fictional company behaves

Aegis Systems has 800 engineers across five teams, followed for 36 months. Each team has an external mobility score from 0 to 1, meaning how easy it is to land a comparable role elsewhere in the current market:

* Platform Infrastructure: 0.28
* DevOps / SRE: 0.34
* Backend Engineering: 0.46
* Data Engineering: 0.50
* ML Platform: 0.71

Three company wide layoff waves hit at months 9, 19, and 28. Each wave permanently raises a team's downsizing ratio, pushes AI displacement anxiety up, and pulls psychological safety down. Between waves, scores drift a little each month, and a management layer shift (a reorg) can happen to anyone with a 2% chance in a given month.

Every month, each engineer has one of three statuses. **Productive Retained** is the default. **Quiet Quitting** is reached when a hidden disengagement score, built from anxiety, safety, downsizing, recent reorgs, and tenure, crosses a threshold. It is sticky, so once crossed, it stays. **Voluntary Exit** is terminal, and the engineer leaves the dataset. Exit odds rise with mobility, and an engineer who has already disengaged is more likely to leave only if their team has high mobility (ML Platform in this setup). Elsewhere they are more likely to stay and stay disengaged. That is the mechanism the whole case study is built to test.

The output is a person month panel, one row per engineer per month, about 25,000 rows in total. Two behavioral proxy columns, Slack response latency and off hours commits, are included as hypothetical signals but are not used in the model.

A messy raw export is generated alongside the clean file, with some team names in uppercase, about 2% duplicate rows, and scattered missing values in three columns. Deduplicating on employee and month takes the raw file from 25,696 rows to the clean 25,192.

## Why survival analysis, and what lifelines does

The question is not whether someone quietly disengages, but when. A standard classifier would only look at a snapshot and throw the timing away. It would also mishandle people who left before disengaging, or who were still engaged when the 36 months ended. Survival analysis is built for exactly this. Those engineers are treated as censored, meaning we know they stayed engaged up to a point but not what happened after.

[lifelines](https://lifelines.readthedocs.io/) is the Python library that does the fitting, in two places:

* **Kaplan Meier estimator.** Gives the share of engineers who had not yet crossed into quiet quitting at each month, overall and for each team.
* **Cox proportional hazards model.** Estimates how much each factor raises or lowers the hazard, which is the instantaneous risk of crossing into quiet quitting, while holding the others constant. A hazard ratio above 1 speeds the slide and below 1 slows it. The concordance index measures how well the model ranks who crosses earlier.

## Reading the dashboard

The [live dashboard](https://aegis-systems-survival-analysis-tnnbzkort5zuxjsj8lkj67.streamlit.app/) has three parts, and each one answers a different question.

**Survival curves by team.** Each line starts at 1.0, meaning everyone is still engaged, and falls as engineers cross into quiet quitting. A steeper drop means a faster slide. If low mobility teams were the hidden problem, their lines would sit visibly lower. They do not, and that is itself a result.

**What predicts a faster slide.** A bar chart of hazard ratios on a log scale. Bars to the right speed up quiet quitting and bars to the left slow it down. Downsizing exposure is rescaled to a per 10 percentage point basis, because its raw hazard ratio describes a full 100 point jump that never happens.

**Simulate a company wide change.** Three sliders: reduce AI displacement anxiety, improve psychological safety, and reduce peak downsizing exposure. Each applies its fitted hazard ratio to the overall survival curve, and the predicted quiet quitting rate at month 36 moves in response. It starts at the observed 47.5%.

## What the model found

Of 800 engineers, 311 crossed into quiet quitting and 489 were censored. The Kaplan Meier estimate puts the share who have crossed by month 36 at 47.5%, and the Cox model has a concordance of 0.79.

Hazard ratios:

* **Psychological safety:** 0.33 per point on the 1 to 5 scale. Strongest protective factor.
* **AI displacement anxiety:** 2.86 per point on the 1 to 5 scale. Strongest risk factor.
* **Team downsizing exposure:** 49.7 per full 100 point swing, about 1.48 per 10 percentage points. Significant, with a caveat covered below.
* **Management layer shift:** 1.23. Not significant at the usual 0.05 level (p = 0.07).
* **Team external mobility:** 1.43. Not significant (p = 0.40).
* **Tenure at the start of observation:** 0.996 per month. Not significant (p = 0.24).

How safe people feel speaking up, and how anxious they are about being replaced by AI, matter far more than tenure or team. Mobility showed no measurable effect on how fast people cross into quiet quitting, and the team curves overlap heavily. Only Backend Engineering reaches a median survival time inside the window, at 36 months. The other four teams never fall below 50% survival.

So the data does not show that low mobility teams disengage faster or slower. It shows that disengagement is widespread everywhere, nearly half the org by month 36, and that psychological factors drive it more than team structure. Because the generator was written so that mobility affects exits and not the onset of disengagement, this is the expected result and a useful check that the pipeline behaves.

## If Aegis were a real company

* **Treat psychological safety as the first lever.** A one point improvement carries the largest protective hazard ratio. In Hirschman's terms, people need a voice channel that works, with visible follow through on concerns, or neglect becomes the only outlet left.
* **Address AI displacement anxiety directly.** The job insecurity research points to uncertainty as the driver. Clear communication about which roles are changing and how targets the second strongest factor, while silence leaves people to assume the worst.
* **Do not read a low exit rate as a clean bill of health.** In a tight market, people stay because they have to. Pair attrition numbers with engagement signals before concluding a team is fine.

## Where this breaks

* **All effects are built in.** The generator drives quiet quitting from anxiety, safety, and downsizing by design, so the model recovering those effects confirms the pipeline works. It is not evidence about real workforces.
* **Look ahead bias.** Downsizing exposure and management layer shift are computed over each engineer's entire observed window, including months after they crossed into quiet quitting. This likely inflates the downsizing hazard ratio. A time varying covariate model would fix it.
* **Voluntary exits are treated as censored.** That fits a question about disengagement, but it means the Kaplan Meier rate differs from the raw 311 of 800 (38.9%).
* **The simulator is a what if tool, not a causal estimate.** It applies the fitted hazard ratios to the overall observed survival curve under a proportional hazards assumption.
* **The psychological scales are simulated.** AI displacement anxiety and psychological safety are generated on 1 to 5 survey style scales. No validated instrument was administered, so the scores are not validated measures of those constructs.
* **The behavioral proxy columns are hypothetical.** They are not a claim that real engineering teams are monitored this way.

## Run it locally

```bash
git clone https://github.com/professorpasqua-byte/aegis-systems-survival-analysis.git
cd aegis-systems-survival-analysis
pip install -r requirements.txt
streamlit run app.py
```

To regenerate the data or refit the model:

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

Built with Python, pandas, NumPy, Faker, lifelines, Streamlit, and SQL (DuckDB style syntax for the documented cleaning pipeline).

## What is real and what is not

Aegis Systems, its engineers, and every model figure are synthetic. The only real facts here are the layoff events and tracker totals cited in the context. No real individual's data, survey responses, or employment history appears anywhere in this project. The cleaning steps are documented in SQL, while the clean file itself is written directly by `generate_data.py` before noise is added to the raw version.

---

**Nwafor Martins**, People Analytics Engineer & I-O Psychology Consultant
[Email](mailto:nwaforchubby@gmail.com)
