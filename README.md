# Professional Development Assistant (PDA)

A multi-agent personal assistant that builds a grounded, verified, approval-gated development plan for one employee at a consulting firm. It reads the employee's skill and certification data, retrieves role and competency documents, finds learning resources, synthesizes a plan with Tree-of-Thought search, and drafts actions (a renewal reminder, calendar blocks, a note) that execute only after explicit human approval.

Capstone project for the CMU Agentic AI Program, by Igor Alcantara. All data is synthetic.

**Status: gathering phases complete.** The typed models, state store, guardrails, retrieval safeguards, escalation rules, prompts, synthetic data generator, and labeled evaluation sets are in place and tested. The three gathering agents and the Orchestrator ReAct loop run end to end in mock mode through the frozen packet, including a scripted failure the loop notices and retries once. Tree-of-Thought synthesis, drafting with the confirm gate, the CLI, and the evaluation harness are next. This README will be completed with the full walkthrough when they land.

## Quickstart (so far)

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows; on macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python data/build_synthetic.py --seed 42
pytest -q
```

No API key is needed for anything above.

## Repository map

```
pda/
  models.py              typed payloads (closed schemas; no field for rating or compensation)
  config.py              caps, beam parameters, model name, paths
  llm.py                 Anthropic client wrapper + deterministic MockLLM, both budget-charged
  state.py               shared state store with freeze() and the JSONL run log
  prompts.py             every prompt sent to a model, plus the typed-only packet renderer
  mock_handlers.py       deterministic stand-ins per model task for keyless runs
  orchestrator.py        the ReAct loop; phase order enforced in code, JSONL run log, memory
  escalation.py          categorical, deterministic, classifier, and judgment triggers
  guardrails/            each module's docstring names the failure it removes
  retrieval/             TF-IDF index over role docs + the checkpoint 3.1 safeguards
  agents/                profile_analyst, context_researcher, resource_scout (planner, critic follow)
data/
  build_synthetic.py     seeded generator for everything below
  pda.db                 SQLite standing in for Snowflake
  role_docs/             13 synthetic role/competency documents with frontmatter
  resource_catalog.json  88 learning resources, 5 of them carrying injection strings
  memory/                long-term memory per employee
eval/labeled/            groundedness claims, escalation cases, critic pairs
tests/                   one test per guardrail, named for the failure it removes
```

## License

MIT.
