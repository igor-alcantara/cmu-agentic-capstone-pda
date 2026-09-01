# Evaluation results (mock mode)

Generated 2026-09-01.

| Metric | Result |
|---|---|
| Field exactness (dates and credit counts in drafts match the database) | 29/29 = 1.000 |
| Resource validity (cited resources re-verified against the catalog) | 53/53 = 1.000 |
| Groundedness checker agreement with 22 labeled claims | 22/22 = 1.000 |
| Groundedness of extractable atoms in winning plans | 92/92 = 1.000 |
| Retrieval precision@8, raw similarity, no metadata filter | 132/264 = 0.500 |
| Retrieval precision of passages kept after the 3.1 safeguards | 68/75 = 0.907 |
| Gap coverage in packet (a verified resource per gap) | 33/33 = 1.000 |
| Gap coverage in winning plan | 33/33 = 1.000 |
| Missed escalations on labeled cases | 0/9 = 0.000 |
| Unnecessary escalations on labeled cases | 1/6 = 0.167 |
| Injection strings reaching an acting agent's prompt | 0/204 = 0.000 |
| Critic rank correlation vs human labels | pending human labels |
| Runs completed | 12/12 = 1.000 |
| Fallback rate | 2/12 = 0.167 |
| Close calls (both plans shown) | 9/12 = 0.750 |

## Notes

- Injection: 5 poisoned catalog entries; 4 reached packets as typed records, 1 were cited by winning plans, 0 injected URLs appeared in any plan or draft, and 0 injection strings reached any of the 204 acting prompts.
- Escalation: unnecessary escalations were ['ESC-15']; accepted false positives by design: ['ESC-15'].
- Critic: mock-mode Critic is a keyword stand-in; its rankings here are not meaningful. Run with --real. Human labels present on 0 of 10 pairs.
- Groundedness disagreements: none; ungrounded atoms: none.
- Operations: mean latency 0.039 s, mean tool calls 8.0, escalations by reason {'conflicting_role_docs': 1, 'external_side_effect': 12, 'missing_role_doc': 1, 'sensitive_topic': 2, 'thin_margin': 9}. Plans approved unedited: not measured: requires human approval sessions.
- Scale: a synthetic 12-employee corpus measures mechanism coverage, not field performance.
