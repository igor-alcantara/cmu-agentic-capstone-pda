# Sample plan: E007

## Context packet (as rendered for the Planner and Critic)

```
Employee: Priya Tanaka (E007), Data Engineer, Data Platforms.
Data snapshot date: 2026-09-01. Weekly study limit: 5 hours.
Profile summary: Priya Tanaka is a Data Engineer with a study budget of 5 hours. Against the role requirements the gaps are Apache Spark 2 -> 3; Snowflake 3 -> 4. SQL sits above the required level. Certifications: SnowPro Core expires 2026-10-01 (30 days), renewal credits 18/30; AWS Certified Cloud Practitioner expires 2027-11-15 (440 days), renewal credits 0/0.
Skill gaps (current -> required):
  - Apache Spark: 2 -> 3
  - Snowflake: 3 -> 4
Certifications:
  - SnowPro Core (Snowflake), expires 2026-10-01, renewal credits 18/30
  - AWS Certified Cloud Practitioner (Amazon Web Services), expires 2027-11-15, renewal credits 0/0
Role document passages (verified relevant):
  [data_engineer_gap_guide / Closing the most common gaps] The gaps we see most often for the Data Engineer role are the platform-specific ones, because platform features move faster than fundamentals. The guidance below pairs each with a practical route: a structured course for the concepts, a hands-on lab for the mechanics, and delivery work with a reviewer for the judgment. Plan for the largest gap first; small gaps close on their own during delivery, large ones do not.
  [data_engineer_gap_guide / Closing a gap in Apache Spark] Apache Spark handles workloads that do not fit a single warehouse query. The role expects a working understanding of partitioning, shuffles, and joins at scale, the ability to read the Spark UI to find a skewed stage, and experience running jobs on a managed service rather than a laptop. A practitioner one level below the requirement should budget roughly 18 to 30 hours: a course or certification preparation path for the concepts, then a hands-on lab, then a piece of delivery work reviewed by someone at level 3 or above. Two levels below usually means a full quarter with a mentor.
  [data_engineer_role_profile / Role purpose] A Data Engineer at IPC Global builds and operates the pipelines that feed client analytics. The work runs from ingestion through modeled marts on Snowflake, orchestrated with Airflow and transformed with dbt, with Spark for the workloads that outgrow a warehouse query. The role is hands-on: engineers write the code, review each other's code, and own the pipelines in production.
  [data_engineer_competency_matrix / Required levels by skill] SQL: required level 4. SQL remains the working language of every engagement.
Python: required level 4. Python is the glue for ingestion, transformation, and testing.
Snowflake: required level 4. Snowflake is the primary warehouse for most client work.
dbt: required level 3. dbt is the transformation standard.
Data Modeling: required level 4. Data modeling underpins everything downstream.
Apache Airflow: required level 3. Apache Airflow orchestrates scheduled pipelines.
Apache Spark: required level 3. Apache Spark handles workloads that do not fit a single warehouse query.
Talend: required level 3. Talend is still in production at several long-standing clients.
Git: required level 3. Git is the collaboration baseline.
  [data_engineer_gap_guide / Closing a gap in Snowflake] Snowflake is the primary warehouse for most client work. Expected competence covers warehouse sizing, clustering and micro-partition pruning, role based access control, secure views, and cost monitoring through the account usage schema. Renewal of the SnowPro Core certification is expected while the platform is in the role's scope. A practitioner one level below the requirement should budget roughly 24 to 40 hours: a course or certification preparation path for the concepts, then a hands-on lab, then a piece of delivery work reviewed by someone at level 4 or above. Two levels below usually means a full quarter with a mentor.
  [data_engineer_gap_guide / Closing a gap in Apache Airflow] Apache Airflow orchestrates scheduled pipelines. Expected skills include writing idempotent tasks, using sensors and task groups sensibly, handling backfills, and configuring alerts so a failed DAG is noticed before the business notices. A practitioner one level below the requirement should budget roughly 18 to 30 hours: a course or certification preparation path for the concepts, then a hands-on lab, then a piece of delivery work reviewed by someone at level 3 or above. Two levels below usually means a full quarter with a mentor.
  [data_engineer_role_profile / Python and data modeling standards] Python and data modeling are the two skills this role is measured on most. Python code in a pipeline follows the practice standard: a package with a pyproject file, type hints on every public function, pandas or polars for tabular work, pytest for unit tests, and a linter in continuous integration. Notebooks are for exploration and are not merged. Data modeling follows the same discipline: every model states its grain in a comment before the first select, dimensions and facts are named by a convention, slowly changing dimensions are typed explicitly, and a wide denormalized table is a conscious modeling decision documented in the model, never an accident. Python and data modeling expectations are reviewed together in code review because a modeling mistake usually shows up first as a Python transformation doing too much. A Data Engineer at level four writes Python that other engineers extend and data models that analysts trust without asking.
Verified learning resources (cite by id only):
  - R007: "Snowflake Course" by Nimbus Learning, 18 h, 0 USD, covers Snowflake
  - R008: "Snowflake Hands-On Lab" by Nimbus Learning, 5 h, 120 USD, covers Snowflake
  - R009: "Snowflake Certification Preparation Path" by DataCraft Institute, 32 h, 300 USD, covers Snowflake
  - R020: "Apache Spark Course" by Nimbus Learning, 16 h, 300 USD, covers Apache Spark
  - R021: "Apache Spark Hands-On Lab" by Open Course Commons, 9 h, 120 USD, covers Apache Spark
  - R022: "Apache Spark Certification Preparation Path" by Nimbus Learning, 35 h, 500 USD, covers Apache Spark
  - R085: "Apache Spark Accelerated Workshop 2" by Community Uploads, 7 h, 0 USD, covers Apache Spark
  - R087: "Apache Spark Accelerated Workshop 4" by Community Uploads, 9 h, 0 USD, covers Apache Spark
Previously rejected by this employee (do not propose again):
  - Weekend study blocks on Saturdays
  - Talend certification track (not relevant to my current project)
Previously accepted (build on these):
  - Pairing sessions with the platform team on Snowflake performance
```

## Chosen plan

`d3-d2-d1-root-0-1-1`, 5 h/week, 2026-09-01 to 2026-12-14

Gaps: Apache Spark, Snowflake. Resources: R009, R008, R020, R021.

Critic: Rank 1: covers 2 gap(s) with 4 resource(s), puts the hard deadline first, leaves room for slippage, 5 h/week.

Full plan (strategy: deadline-first, variant: standard). Start on the snapshot date and run 15 weeks at 5 hours a week on weekday evenings. Block 1: Snowflake, R009 (Snowflake Certification Preparation Path, 32 h) then R008 (Snowflake Hands-On Lab, 5 h), about 8 week(s) at 5 h/week; renewal credits are logged in this block. Block 2: Apache Spark, R020 (Apache Spark Course, 16 h) then R021 (Apache Spark Hands-On Lab, 9 h), about 5 week(s) at 5 h/week. Each block ends with delivery work reviewed at the required level, and the renewal reminder goes out before any of it starts. A two-week buffer closes the plan for catch-up. Avoid: Weekend study blocks on Saturdays; Talend certification track (not relevant to my current project).

## Runner-up (the Critic called it a close call, so the employee sees both)

`d3-d2-d1-root-0-0-1`, 4 h/week, 2026-09-01 to 2027-01-11

Gaps: Apache Spark, Snowflake. Resources: R008, R009, R021, R020.

Critic: Rank 2: covers 2 gap(s) with 4 resource(s), puts the hard deadline first, leaves room for slippage, 4 h/week.

Full plan (strategy: deadline-first, variant: lab-first). Start on the snapshot date and run 19 weeks at 4 hours a week on weekday evenings. Block 1: Snowflake, R008 (Snowflake Hands-On Lab, 5 h) then R009 (Snowflake Certification Preparation Path, 32 h), about 10 week(s) at 4 h/week; renewal credits are logged in this block. Block 2: Apache Spark, R021 (Apache Spark Hands-On Lab, 9 h) then R020 (Apache Spark Course, 16 h), about 7 week(s) at 4 h/week. Each block ends with delivery work reviewed at the required level, and the renewal reminder goes out before any of it starts. A two-week buffer closes the plan for catch-up. Avoid: Weekend study blocks on Saturdays; Talend certification track (not relevant to my current project).

## Drafted actions (not executed; approval happens in the CLI)

### [A1] renewal_reminder: Renewal reminder: SnowPro Core

```
To: Priya Tanaka
Subject: SnowPro Core renewal due 2026-10-01

Hi Priya Tanaka,

Your SnowPro Core certification from Snowflake expires on 2026-10-01, which is 30 days from the current data snapshot. You have logged 18 of the 30 renewal credits, so 12 remain. The development plan puts the renewal work first so the credits are complete before the expiry date.

This reminder was drafted by the Professional Development Assistant and sent only after you approved it.
```

### [A2] calendar_block: Study time calendar blocks

```
Calendar: recurring study block
Title: Development plan study time
Pattern: 5 hours per week on weekday evenings, from 2026-09-07 to 2026-12-20 (15 weeks, 75 hours in total).
Notes: split as two sessions per week. Weekend blocks are not proposed.
```

### [A3] note: Development plan note

```
Personal development note (draft, not filed to any formal record)
Employee: Priya Tanaka
Snapshot: 2026-09-01

Chosen plan:
Full plan (strategy: deadline-first, variant: standard). Start on the snapshot date and run 15 weeks at 5 hours a week on weekday evenings. Block 1: Snowflake, R009 (Snowflake Certification Preparation Path, 32 h) then R008 (Snowflake Hands-On Lab, 5 h), about 8 week(s) at 5 h/week; renewal credits are logged in this block. Block 2: Apache Spark, R020 (Apache Spark Course, 16 h) then R021 (Apache Spark Hands-On Lab, 9 h), about 5 week(s) at 5 h/week. Each block ends with delivery work reviewed at the required level, and the renewal reminder goes out before any of it starts. A two-week buffer closes the plan for catch-up. Avoid: Weekend study blocks on Saturdays; Talend certification track (not relevant to my current project).

Gaps addressed: Apache Spark, Snowflake
Resources: R009 (Snowflake Certification Preparation Path), R008 (Snowflake Hands-On Lab), R020 (Apache Spark Course), R021 (Apache Spark Hands-On Lab)
Weekly hours: 5
```
