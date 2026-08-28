import dexa_taper_lookup as L
days = ["2026-05-06","2026-08-11","2026-08-12","2026-08-25","2026-08-26",
        "2026-09-08","2026-09-09","2026-10-20","2026-10-21","2026-11-03",
        "2026-11-04","2026-11-17","2026-11-18","2026-12-01","2027-01-12","2027-01-13"]
print(f"{'date':<12} {'B':>3} {'C':>3} {'D':>3} {'F':>3} | sum")
for d in days:
    row = {s: L.get_dexa_dose(s, d) for s in ["B","C","D","F"]}
    vals = [v for v in row.values() if v is not None]
    total = sum(vals)
    print(f"{d:<12} {row['B']!s:>3} {row['C']!s:>3} {row['D']!s:>3} {row['F']!s:>3} | {total}")
