---
name: diet-tracker
description: Deterministic diet, nutrition macros, and caloric deficit tracking for Amirulhazym. Enforces ADHD-friendly 5-category visual reports on WhatsApp and counters Dexa-induced sodium retention.
disable-model-invocation: false
license: MIT
metadata:
  hermes:
    tags: [Diet, Nutrition, ADHD, Health, Dexa, Deficit]
    category: health
    related_skills: [med-tracker, i-have-adhd]
---

# Diet Tracker & ADHD Nutrition Protocol

## Domain Rules & Constraints
1. **ADHD Visual Formatting (WhatsApp):**
   - Strictly prohibit unstructured dense paragraphs or conversational rambling when discussing diet.
   - All diet and nutrition responses MUST follow the structured format:
     - 📋 1. LOG PEMAKANAN HARIAN (INTAKE)
     - 🧪 2. PROFIL NUTRISI (MACROS)
     - 🔬 3. KAJIAN BIOMEDIKAL: PROS & CONS (Khas Dexa & Pemulihan)
     - ⚖️ 4. TENAGA KELUAR & STATUS DEFISIT (BURN)
     - ⚡ 5. NEXT ACTION MALAM INI
2. **Clinical Dexa Taper Rules:**
   - Dexamethasone induces mineralocorticoid sodium retention, causing edema / water retention.
   - NEVER suggest adding salt/sodium to drinks or electrolytes post-workout. Prioritize potassium-rich sources (e.g. bananas, ulam) to promote natural renal sodium clearance.
   - Sparing lean muscle: prioritize high-biological-value protein (eggs, chicken, fish) to counteract steroid catabolism while maintaining calorie deficit.
   - Low-carb / zero rice preferred to prevent steroid-induced insulin resistance and visceral fat deposition.
3. **Execution Tool:**
   - Always update `~/.hermes/diet-log.json` when the user reports meal/exercise events.
   - Use `python3 scripts/diet_report.py [--mode eod|compact]` to generate deterministic formatted reports rather than constructing ad-hoc prose.
