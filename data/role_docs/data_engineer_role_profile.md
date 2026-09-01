---
role: Data Engineer
department: Data Platforms
kind: role_profile
updated: 2026-06-15
---
# Data Engineer: Role Profile

## Role purpose
A Data Engineer at IPC Global builds and operates the pipelines that feed client analytics. The work runs from ingestion through modeled marts on Snowflake, orchestrated with Airflow and transformed with dbt, with Spark for the workloads that outgrow a warehouse query. The role is hands-on: engineers write the code, review each other's code, and own the pipelines in production.

## Core competencies
SQL remains the working language of every engagement. At the expected level a practitioner writes window functions and common table expressions without reference material, reads an execution plan, and can explain why a query is slow before touching it. Query tuning on columnar warehouses is part of the role, not an extra. Expected level for this role: 4 of 5.
Python is the glue for ingestion, transformation, and testing. The expectation is idiomatic Python with type hints, pandas or polars for tabular work, packaging with a pyproject file, and unit tests that run in continuous integration. A practitioner at level four writes reusable modules, not notebooks that only run on one laptop. Expected level for this role: 4 of 5.
Snowflake is the primary warehouse for most client work. Expected competence covers warehouse sizing, clustering and micro-partition pruning, role based access control, secure views, and cost monitoring through the account usage schema. Renewal of the SnowPro Core certification is expected while the platform is in the role's scope. Expected level for this role: 4 of 5.
dbt is the transformation standard. A practitioner structures models in staging, intermediate, and mart layers, writes schema tests and documentation, uses incremental models where the data volume justifies them, and reviews others' pull requests for modeling mistakes. Expected level for this role: 3 of 5.
Data modeling underpins everything downstream. The role expects dimensional modeling with slowly changing dimensions, an understanding of when a wide table beats a star schema, and the discipline to write a model's grain down before writing SQL. Poor modeling is the most common root cause of slow dashboards. Expected level for this role: 4 of 5.
Apache Airflow orchestrates scheduled pipelines. Expected skills include writing idempotent tasks, using sensors and task groups sensibly, handling backfills, and configuring alerts so a failed DAG is noticed before the business notices. Expected level for this role: 3 of 5.
Apache Spark handles workloads that do not fit a single warehouse query. The role expects a working understanding of partitioning, shuffles, and joins at scale, the ability to read the Spark UI to find a skewed stage, and experience running jobs on a managed service rather than a laptop. Expected level for this role: 3 of 5.
Talend is still in production at several long-standing clients. A practitioner maintains existing jobs, understands the component model, and can plan a migration path off Talend where a client wants one. Expected level for this role: 3 of 5.
Git is the collaboration baseline. The role expects feature branches, small reviewable pull requests, a clean rebase when asked, and never a force push to a shared branch. Expected level for this role: 3 of 5.

## Level expectations
Skill levels run from one to five. Level one is awareness: the person knows what the tool is for. Level two is supervised use on delivery work. Level three is independent delivery on a typical engagement. Level four is the level expected of someone who leads that part of an engagement and reviews others. Level five is recognized expertise across the practice, the person others escalate to. Role requirements below name the level at which a practitioner is considered fully effective; a gap is any skill below that level.

## Certifications
SnowPro Core is expected while Snowflake is in scope, and its renewal credits must be earned before the expiry date; a lapsed certification is re-examined from scratch. The dbt Analytics Engineering certification is encouraged. AWS Cloud Practitioner is a useful baseline but not required.

## Python and data modeling standards
Python and data modeling are the two skills this role is measured on most. Python code in a pipeline follows the practice standard: a package with a pyproject file, type hints on every public function, pandas or polars for tabular work, pytest for unit tests, and a linter in continuous integration. Notebooks are for exploration and are not merged. Data modeling follows the same discipline: every model states its grain in a comment before the first select, dimensions and facts are named by a convention, slowly changing dimensions are typed explicitly, and a wide denormalized table is a conscious modeling decision documented in the model, never an accident. Python and data modeling expectations are reviewed together in code review because a modeling mistake usually shows up first as a Python transformation doing too much. A Data Engineer at level four writes Python that other engineers extend and data models that analysts trust without asking.
