# 04 — Protein dual floor, no false pass

Blocked by: none

## Why
A report claimed protein "mencapai lantai 70.8 g" at 67.3 g (3.5 g short), and
quoted only the 1.2 g/kg floor while the log already stores 1.6 g/kg (94.4 g).

## Slice
1. Render both: `lantai 70.8 g (1.2 g/kg)` and `optimum 94.4 g (1.6 g/kg)`.
2. Threshold wording: `>= floor` -> reached; `< floor` -> `BELUM capai (gap X g)`.
3. Never emit "mencapai" unless value >= floor.

## Done
- Unit test: 67.3 g renders "BELUM capai (gap 3.5 g)".
- Unit test: 71.0 g renders reached.
