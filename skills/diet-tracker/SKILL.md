---
name: diet-tracker
description: Deterministic diet, nutrition macros, and caloric deficit tracking for Amirulhazym. Enforces natural Bahasa Melayu WhatsApp formatting, official label verification, and unit-complete step-by-step math.
disable-model-invocation: false
license: MIT
metadata:
  hermes:
    tags: [Diet, Nutrition, ADHD, Health, Dexa, Deficit]
    category: health
    related_skills: [med-tracker, i-have-adhd]
---

# Diet Tracker & Nutrition Protocol

## 1. Gaya Bahasa & Format Laporan WhatsApp (MANDATORY)
1. **Mula dengan Verdict:** Baris pertama jawapan mesti terus memberikan rumusan atau *verdict* utama (status kalori, protein, dan baki/defisit). Jangan mula dengan ayat defensif atau nota sistem.
2. **Bahasa Melayu Natural & Penuh:** Tulis menggunakan ayat Bahasa Melayu yang penuh, natural, sopan, dan mudah difahami. **DILARANG** menggunakan gaya nota fragment pendek sekerat-sekerat (`"Sekarang dah tak relevan"`, `"Data gap aku tak tutup"`), nada biadab, atau ayat yang berbunyi seperti terjemahan terus dari bahasa Inggeris.
3. **Setiap Angka Wajib Ada Unit:** Jangan tulis angka bogel seperti `P 8.7 · C 41.4 · F 3.9` atau `deficit 643`. Tulis dengan unit lengkap: `Protein: 8.7 g | Karbohidrat: 41.4 g | Lemak: 3.9 g` dan `Defisit: 643.2 kcal`.
4. **Susunan Visual & Kiraan Langkah Demi Langkah:**
   - Gunakan pembahagi `━━━`, emoji kategori, dan baris kosong antara seksyen supaya mudah dibaca di telefon.
   - Tunjukkan kiraan jumlah secara berperingkat (**Langkah 1, Langkah 2, Langkah 3**), bukan terus melompat ke jawapan akhir.
   - Struktur laporan diet WhatsApp:
     - 📋 **1. LOG PEMAKANAN HARIAN (INTAKE)**
     - 🧪 **2. PROFIL NUTRISI & MAKRO**
     - ⚖️ **3. TENAGA KELUAR & STATUS DEFISIT (BURN)**
     - ⚡ **4. TINDAKAN SETERUSNYA**
   - Fokus jawapan diet kepada **kalori, protein, makro, dan defisit**. Jangan selitkan syarahan perubatan Dexamethasone kecuali ditanya secara khusus, tetapi kekalkan prinsip pemakanan rendah garam, tanpa gula tambahan, dan tanpa kanji proses.

## 2. Protokol Pengesahan Label Rasmi & Ketepatan Kiraan
1. **Cari & Baca Sumber Rasmi Pengeluar Dahulu:** Untuk sebarang produk komersial (roti, tuna tin, susu, serbuk protein), wajib cari dan baca panel nutrisi rasmi laman web pengeluar Malaysia/Singapura menggunakan `web_search`, `web_extract` (dengan Jina Reader fallback), atau CLI `agent-reach web search` / `agent-reach read <url>` sebelum menggunakan sebarang anggaran generik. Jangan menyerah awal atau guna data komuniti tidak sahih jika laman rasmi boleh diakses.
2. **Sertakan Pautan Rujukan:** Letakkan URL sumber rasmi yang digunakan di bahagian akhir laporan.
3. **Jangan Double-Count Minyak Produk Tin:** Untuk produk tin dalam minyak (seperti *Tuna in Olive Oil*):
   - Jika pengguna menapis/membuang minyak atau membilas dengan air, kira nilai isi ikan *drained* sahaja tanpa menambah minyak bebas tambahan.
   - Jika pengguna makan habis tanpa membuang minyak, tolak lemak yang sudah terkandung dalam isi ikan *drained* daripada jumlah minyak dalam senarai bahan tin sebelum mengira baki minyak bebas — jangan kira dua kali.
4. **Integriti Matematik Defisit & Berat:**
   - Kekalkan kiraan sebenar `Defisit = TDEE - Intake` tanpa sebarang *clamp* atau pemotongan nombor. Tambah baris amaran `⚠️` jika protein jatuh bawah lantai `1.2 g/kg` (`70.8 g` pada `59.0 kg`) atau optimum `1.6 g/kg` (`94.4 g`).
   - Setiap paparan berat badan wajib menyertakan tarikh timbangan (`measured_date`), contohnya: `59.0 kg (rekod 2026-11-15)`.

## 3. Wearable Burn Inputs — 4 Mandatory Rules (Phase 6, 2026-11-16)
1. **Canonical file only — no ad-hoc cloud probes:** Baca data wearable dari `/home/ubuntu/hermes-huawei-sync/data/latest.json` (hari ini) atau `data/YYYY-MM-DD.json` (sejarah) dan nyatakan `fetched_at`.
2. **Settling window:** Semak `sync_settling` sebelum memetik angka jam tangan; label `[PRELIMINARY]` jika `sync_settling == true`.
3. **Modality provenance:** Nyatakan nama senaman hanya jika disahkan pengguna atau direkodkan dalam `workout_annotations.json`.
4. **One weight, one BMR, both dynamic:** Guna `body_weight_kg` + `body_weight_measured_date` daripada `latest.json` dan `tdee_calibration.bmr_kcal` (`1441 kcal` pada `59.0 kg`).
