# V10 — Python AI (object API)

Sources live in `src/` (numbered for bundle order); `python3 tools/v10_build.py`
concatenates them (plus the generated value-model weights) into `V10/v10.py`,
the single file that runs locally (polyglot generator) and on prod
(`10.0/V10/v10.py`).

Only the OBJECT API is used (`Fight`, `Field`, `Cell`, `Weapon`, `Chip`,
`Effect`...): prod Python AIs do not expose the flat LeekScript functions.
`00_compat.py` bridges the two differences found so far: the ops counter
(`System.operations` on prod, flat `getOperations()` locally) and logging
(`Debug.log` on prod, flat `debug()` locally).

Design: engine-faithful item rules read from the item's own features (no hand
database), a simulator that applies a plan to a state copy, a search over
(attack cell x attack packing x self prefix x final reposition), and the prod
value model (data/prod/value_mono.json) as the evaluator.
