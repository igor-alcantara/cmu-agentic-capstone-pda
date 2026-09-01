---
role: Data Engineer
department: Data Platforms
kind: gap_guide
updated: 2026-05-20
---
# Data Engineer: Gap Guide

## Closing the most common gaps
The gaps we see most often for the Data Engineer role are the platform-specific ones, because platform features move faster than fundamentals. The guidance below pairs each with a practical route: a structured course for the concepts, a hands-on lab for the mechanics, and delivery work with a reviewer for the judgment. Plan for the largest gap first; small gaps close on their own during delivery, large ones do not.

## Closing a gap in SQL
SQL remains the working language of every engagement. At the expected level a practitioner writes window functions and common table expressions without reference material, reads an execution plan, and can explain why a query is slow before touching it. Query tuning on columnar warehouses is part of the role, not an extra. A practitioner one level below the requirement should budget roughly 24 to 40 hours: a course or certification preparation path for the concepts, then a hands-on lab, then a piece of delivery work reviewed by someone at level 4 or above. Two levels below usually means a full quarter with a mentor.

## Closing a gap in Python
Python is the glue for ingestion, transformation, and testing. The expectation is idiomatic Python with type hints, pandas or polars for tabular work, packaging with a pyproject file, and unit tests that run in continuous integration. A practitioner at level four writes reusable modules, not notebooks that only run on one laptop. A practitioner one level below the requirement should budget roughly 24 to 40 hours: a course or certification preparation path for the concepts, then a hands-on lab, then a piece of delivery work reviewed by someone at level 4 or above. Two levels below usually means a full quarter with a mentor.

## Closing a gap in Snowflake
Snowflake is the primary warehouse for most client work. Expected competence covers warehouse sizing, clustering and micro-partition pruning, role based access control, secure views, and cost monitoring through the account usage schema. Renewal of the SnowPro Core certification is expected while the platform is in the role's scope. A practitioner one level below the requirement should budget roughly 24 to 40 hours: a course or certification preparation path for the concepts, then a hands-on lab, then a piece of delivery work reviewed by someone at level 4 or above. Two levels below usually means a full quarter with a mentor.

## Closing a gap in dbt
dbt is the transformation standard. A practitioner structures models in staging, intermediate, and mart layers, writes schema tests and documentation, uses incremental models where the data volume justifies them, and reviews others' pull requests for modeling mistakes. A practitioner one level below the requirement should budget roughly 18 to 30 hours: a course or certification preparation path for the concepts, then a hands-on lab, then a piece of delivery work reviewed by someone at level 3 or above. Two levels below usually means a full quarter with a mentor.

## Closing a gap in Data Modeling
Data modeling underpins everything downstream. The role expects dimensional modeling with slowly changing dimensions, an understanding of when a wide table beats a star schema, and the discipline to write a model's grain down before writing SQL. Poor modeling is the most common root cause of slow dashboards. A practitioner one level below the requirement should budget roughly 24 to 40 hours: a course or certification preparation path for the concepts, then a hands-on lab, then a piece of delivery work reviewed by someone at level 4 or above. Two levels below usually means a full quarter with a mentor.

## Closing a gap in Apache Airflow
Apache Airflow orchestrates scheduled pipelines. Expected skills include writing idempotent tasks, using sensors and task groups sensibly, handling backfills, and configuring alerts so a failed DAG is noticed before the business notices. A practitioner one level below the requirement should budget roughly 18 to 30 hours: a course or certification preparation path for the concepts, then a hands-on lab, then a piece of delivery work reviewed by someone at level 3 or above. Two levels below usually means a full quarter with a mentor.

## Closing a gap in Apache Spark
Apache Spark handles workloads that do not fit a single warehouse query. The role expects a working understanding of partitioning, shuffles, and joins at scale, the ability to read the Spark UI to find a skewed stage, and experience running jobs on a managed service rather than a laptop. A practitioner one level below the requirement should budget roughly 18 to 30 hours: a course or certification preparation path for the concepts, then a hands-on lab, then a piece of delivery work reviewed by someone at level 3 or above. Two levels below usually means a full quarter with a mentor.

## Closing a gap in Talend
Talend is still in production at several long-standing clients. A practitioner maintains existing jobs, understands the component model, and can plan a migration path off Talend where a client wants one. A practitioner one level below the requirement should budget roughly 18 to 30 hours: a course or certification preparation path for the concepts, then a hands-on lab, then a piece of delivery work reviewed by someone at level 3 or above. Two levels below usually means a full quarter with a mentor.

## Closing a gap in Git
Git is the collaboration baseline. The role expects feature branches, small reviewable pull requests, a clean rebase when asked, and never a force push to a shared branch. A practitioner one level below the requirement should budget roughly 18 to 30 hours: a course or certification preparation path for the concepts, then a hands-on lab, then a piece of delivery work reviewed by someone at level 3 or above. Two levels below usually means a full quarter with a mentor.
