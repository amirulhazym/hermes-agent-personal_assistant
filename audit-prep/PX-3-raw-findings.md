# PX-3 — Memory Architecture & WhatsApp Bridge Raw Findings

> **Source:** WhatsApp conversation analysis — 14 Jul 2026, 09:35 MYT
> **Status:** RAW — not yet actioned (Overhaul Freeze active)
> **Context:** Root cause analysis of 13-14 Jul memory alerts (bridge.js swap + Chromium contention on 2GB VPS)
> **Originator:** amirulhazym (primary analysis) + Hermes (secondary/corrective)
> **Fasa Klasifikasi:** Fasa 0 (Safety Guardrails) + Fasa 1 (Observability) — hybrid, concurrent

---

## Kesimpulan Utama

Masalah ini bukan sekadar threshold monitor terlalu tinggi. Ada tiga lapisan berasingan:

1. **Memory accounting/diagnosis masih belum lengkap.**
2. **Bridge atau komponennya pernah membina working set yang sangat besar.**
3. **Seni bina sekarang membenarkan workload "bursty" seperti Chromium bersaing dengan servis kritikal dalam VPS 2 GB.**

Penyelesaian jangka panjang bukan "tambah swap + restart bila penuh". Ia perlu menjadi sistem yang:
- mengehadkan setiap workload,
- melambatkan atau menolak kerja berat ketika host tertekan,
- memisahkan state kekal daripada worker yang boleh dibuang,
- dan memberi alert berdasarkan impak sebenar, bukan satu angka RAM.

---

## 1. Pembetulan Penting Terhadap Diagnosis Asal

### A. 2.1 GB VmSwap — bukan sekadar "swap allocation"

Jika nilai itu datang daripada `/proc/PID/status`, VmSwap biasanya menunjukkan anonymous memory proses yang benar-benar telah dipindahkan ke swap, bukan sekadar ruang swap yang ditempah.

Maksudnya: Bridge yang sekarang mempunyai RSS 102 MB + swap 2.1 GB kemungkinan pernah menyentuh sekurang-kurangnya sekitar 2.2 GB memory-backed pages.

Bridge mungkin tidak menggunakan banyak RAM sekarang, tetapi itu tidak membuktikan bridge sihat. Ia boleh bermaksud majoriti working set lamanya telah dibekukan dalam swap.

**Gunakan `/proc/PID/smaps_rollup`** untuk bacaan lebih tepat seperti Pss, Anonymous, Swap dan SwapPss; kernel sendiri mengesyorkan smaps/smaps_rollup apabila nilai tepat diperlukan.

### B. `--max-old-space-size` — bukan hard limit untuk seluruh Node.js

Flag itu hanya mengehadkan V8 old-generation heap. Ia tidak mengehadkan sepenuhnya:
- Buffer
- ArrayBuffer
- Media yang dibaca ke memory
- Native allocations
- TLS/WebSocket buffers
- zlib
- Library native
- Child processes
- Memory-mapped files

Node menyediakan `process.memoryUsage()` dengan pecahan `rss`, `heapTotal`, `heapUsed`, `external` dan `arrayBuffers` untuk membezakan kategori ini.

**Jadi:**
- Jika `heapUsed` membesar → kemungkinan object retention, cache atau history.
- Jika `external`/`arrayBuffers` membesar → kemungkinan buffer/media/network.
- Jika semuanya rendah tetapi RSS/swap tinggi → selidik allocator, native memory atau historical cold pages.

### C. Threshold 500 MB — bukan semestinya "salah"

500 MB bersamaan ~25% daripada VPS 2 GB. Ia mungkin konservatif, tetapi 259 MB MemAvailable memang situasi berisiko jika Chromium boleh bermula pada bila-bila masa.

Masalah sebenar ialah monitor menganggap:
```
MemAvailable < 500 MB = incident
```
Sedangkan yang patut ditanya ialah:
- Adakah proses sedang tersekat kerana memory reclaim?
- Adakah swap-in meningkat?
- Adakah latency/heartbeat gagal?
- Adakah OOM hampir berlaku?

Linux menyediakan **Pressure Stall Information (PSI)** untuk mengukur masa proses benar-benar tersekat akibat memory pressure.

---

## 2. Seni Bina Terbaik untuk VPS 2 GB: "Memory QoS + Disposable Workers"

```
                    ┌──────────────────────┐
WhatsApp ──────────►│ Bridge: sentiasa hidup│
                    │ kecil + bounded state │
                    └──────────┬───────────┘
                               │ queue
                    ┌──────────▼───────────┐
                    │ Gateway coordinator  │
                    │ context aktif terhad │
                    └──────────┬───────────┘
                               │ job request
              ┌────────────────▼────────────────┐
              │ Admission controller            │
              │ cukup RAM/PSI rendah?            │
              └───────┬─────────────────┬───────┘
                      │ ya              │ tidak
               ┌──────▼──────┐   ┌──────▼─────────┐
               │ Browser job │   │ HTTP/search/API │
               │ disposable  │   │ atau queue/defer│
               └─────────────┘   └────────────────┘
```

**Prinsipnya:**
- Bridge dan gateway ialah control plane.
- Chromium ialah burst worker, bukan sebahagian daripada baseline.
- Semua operasi berat melalui queue dan admission control.
- Worker berat boleh dibunuh tanpa merosakkan session kekal.
- State penting disimpan di disk/database, bukan hanya dalam RAM.

Ini lebih penting daripada apa-apa `sysctl`.

---

## 3. Cadangan Penyelesaian Mengikut Impak

### Cadangan 1 — Letakkan setiap servis dalam cgroup berasingan

Jangan biarkan bridge, gateway dan browser berkongsi satu memory pool tanpa sempadan.
Gunakan systemd/cgroup v2:

- **MemoryHigh**: soft boundary; proses akan diperlahankan dan memory direclaim.
- **MemoryMax**: last line of defence.
- **MemorySwapMax**: menghalang satu servis menimbus beberapa GB cold state dalam swap.

Kernel mengesyorkan `memory.high` sebagai mekanisme kawalan utama kerana ia throttling workload tanpa terus membunuhnya. Systemd turut menerangkan `MemoryMax` sebagai perlindungan terakhir apabila `MemoryHigh` tidak mencukupi.

**Nilai permulaan yang munasabah (starting profile, bukan angka mutlak):**

Contoh bridge:
```
[Service]
Environment="NODE_OPTIONS=--max-old-space-size=384"
MemoryAccounting=yes
MemoryHigh=350M
MemoryMax=500M
MemorySwapMax=384M
OOMPolicy=stop
Restart=on-failure
RestartSec=10s
```

**Penting:** Jangan terus menetapkan heap kepada 256 MB tanpa baseline. Mulakan 384 MB, ukur heapUsed p95/p99 selama seminggu, kemudian turunkan jika ada ruang.

**Mengapa ini lebih baik daripada restart script?**
- Jika bridge bocor, hanya bridge akan dihentikan.
- Gateway dan OS kekal hidup.
- Runaway swap tidak boleh mencapai 2.1 GB lagi.
- Punca masalah menjadi lebih mudah dikenal pasti melalui `memory.events`.

### Cadangan 2 — Implementasikan "pressure-aware admission control"

Ini solusi yang paling banyak menjimatkan VPS kecil.
Sebelum melancarkan Chromium, gateway perlu semak:
- MemAvailable
- `/proc/pressure/memory`
- swap-in rate
- browser job sedia ada
- jumlah context aktif

**Contoh polisi:**
```
Jika browser sedang berjalan:
    queue job baru

Jika MemAvailable < 800 MB:
    jangan mulakan Chromium

Jika memory PSI some avg10 > 2%:
    jangan mulakan Chromium

Jika memory PSI full avg10 > 1%:
    hentikan/nonaktifkan kerja bukan kritikal

Jika selamat:
    jalankan maksimum satu browser worker
```

Threshold PSI di atas ialah nilai permulaan untuk diuji, bukan standard universal.

**Gunakan escalation ladder:**
Untuk setiap web task:
1. Cuba HTTP fetch biasa.
2. Cuba API/endpoint JSON.
3. Cuba reader/extractor tanpa browser.
4. Hanya jika JavaScript benar-benar wajib, gunakan Chromium.
5. Tamatkan keseluruhan process tree selepas job selesai.

Ini boleh menghapuskan sebahagian besar penggunaan 700 MB–1.1 GB yang sekarang datang daripada browser.

**Jangan** cuba menjimatkan memory menggunakan `--single-process` atau mematikan sandbox secara sembarangan. Itu boleh menjejaskan kestabilan dan keselamatan. Hard limit melalui cgroup jauh lebih selamat.

### Cadangan 3 — Jadikan browser worker "ephemeral"

Jangan simpan Chromium hidup sepanjang sesi panjang.
Setiap browser job patut mempunyai:
- Satu job pada satu masa
- Deadline 2–5 minit
- Page limit
- Tab limit
- Download size limit
- Process-tree cleanup
- Temporary profile yang dipadam selepas tamat

**Contoh pola:**
```
spawn browser scope
    → buka maksimum 1–2 tab
    → lakukan kerja
    → tutup context
    → kill seluruh cgroup
    → padam temporary profile
```

Jika browser hang atau child renderer tertinggal, membunuh parent sahaja kadangkala tidak cukup. Membunuh keseluruhan cgroup memastikan tiada renderer/GPU/network subprocess tertinggal.

**Versi jangka lebih panjang:** Pisahkan browser kepada burst worker luaran — VPS 2 GB kekal sebagai control plane; job browser dihantar melalui queue; worker dijalankan pada mesin berasingan/on-demand (kos dan RAM worker hampir sifar apabila tiada job).

### Cadangan 4 — Ubah gateway kepada "bounded-context worker"

Enam context compactions menunjukkan masalah bukan hanya RAM, tetapi model lifecycle.

Jangan simpan satu sesi Python tanpa had. Pisahkan kepada:

**A. Durable conversation state** — simpan di SQLite/disk:
- Ringkasan conversation
- Keputusan penting
- User preferences
- References kepada artifacts
- Status task
- Beberapa mesej terkini sahaja

**B. Disposable execution context** — worker Python hanya memuatkan:
- Ringkasan
- N mesej terkini
- Data yang diperlukan untuk task semasa

**Selepas:**
- 50–100 turns
- 2–4 compactions
- RSS melebihi budget
- Atau task besar selesai

Buat graceful context rotation:
1. Tulis checkpoint/ringkasan.
2. Tamatkan worker lama.
3. Mulakan worker baru.
4. Hydrate daripada state minimum.

Ini bukan "restart sebab rosak"; ini **generational lifecycle design**, seperti worker recycling dalam server production.

### Cadangan 5 — Kurangkan state Baileys secara fundamental

Dokumentasi Baileys sendiri memberi amaran bahawa menyimpan keseluruhan chat history dalam in-memory store ialah pembaziran RAM dan mengesyorkan custom data store.

**Semak sama ada bridge menggunakan:**
- `makeInMemoryStore`
- full-history sync
- unbounded message map
- contact/group cache tanpa TTL
- message retry cache tanpa had
- media buffer yang dibaca sepenuhnya
- event listeners yang bertambah selepas reconnect
- timer atau pending promises yang tidak dibersihkan

**Reka bentuk yang disyorkan:**
- Auth keys: persistent store
- Messages: SQLite dengan retention
- Hot cache: bounded LRU sahaja
- Media: stream terus ke file/object storage
- History sync: minimum yang diperlukan
- Duplicate/retry cache: TTL + maximum entries
- Reconnect: pastikan socket lama, listener dan timer ditutup dahulu

**Contoh budget cache:**
- Recent messages: 500–2,000 entries
- Retry cache: TTL 15–30 minit
- Contact/group cache: TTL beberapa jam
- Media buffers: maksimum 10–25 MB serentak

Terdapat beberapa laporan memory growth dalam versi Baileys tertentu — termasuk semasa menerima mesej, long-running sessions dan media handling (GitHub issues #2090, #745). Ini tidak membuktikan versi semasa bocor, tetapi cukup kuat untuk:
- Pin versi yang diketahui stabil
- Jangan auto-upgrade
- Jalankan canary selama 24–72 jam
- Bandingkan slope memory sebelum rollout

---

## 4. Cara Membuktikan Komponen Sebenar yang Membesar

### Bridge telemetry (setiap 60 saat)

```javascript
const v8 = require('node:v8')

setInterval(() => {
  const m = process.memoryUsage()
  const h = v8.getHeapStatistics()

  console.log(JSON.stringify({
    type: 'memory',
    ts: new Date().toISOString(),
    rss_mb: Math.round(m.rss / 1048576),
    heap_used_mb: Math.round(m.heapUsed / 1048576),
    heap_total_mb: Math.round(m.heapTotal / 1048576),
    external_mb: Math.round(m.external / 1048576),
    array_buffers_mb: Math.round(m.arrayBuffers / 1048576),
    heap_limit_mb: Math.round(h.heap_size_limit / 1048576),
    handles: process.getActiveResourcesInfo?.().length
  }))
}, 60_000).unref()
```

**Tambahkan application counters:**
- Jumlah message cache
- Jumlah auth/session keys
- Jumlah active sockets
- Jumlah reconnect
- Jumlah event listeners
- Jumlah pending requests
- Jumlah queued jobs
- Byte media diproses
- Jumlah messages sejak start

**Cara membaca hasil:** Node menyarankan pemantauan memory dari masa ke masa kerana heapUsed yang terus berkembang boleh menunjukkan leak.

**Heap snapshot:** Ambil snapshot (1) selepas clean start, (2) selepas load terkawal, (3) selepas memory meningkat. Bandingkan retained objects dan retaining paths. Namun snapshot boleh sendiri memerlukan memory besar dan menyebabkan proses terhenti, jadi buat pada clone/canary atau ketika terdapat headroom.

---

## 5. Ganti Health Monitor dengan Sistem Alert Berperingkat

### Jangan alert hanya berdasarkan MemAvailable

**INFO** — direkod, tidak dihantar malam:
- MemAvailable < 25%
- bridge swap > 256 MB
- context sudah compact beberapa kali

**WARNING** — satu notifikasi, kemudian deduplicate:
- MemAvailable < 15% selama 10 minit AND (memory PSI meningkat OR swap-in aktif)
- ATAU memory usage sesuatu servis > MemoryHigh selama 10 minit

**CRITICAL** — hantar walaupun waktu malam:
- Heartbeat bridge gagal
- Message delivery gagal
- OOM kill berlaku
- Memory PSI full tinggi beberapa minit
- MemAvailable < 5% dan swap-in thrashing
- Browser/gateway tidak dapat memberi respons

Google SRE mengesyorkan alert yang actionable dan berkait dengan simptom/SLO, bukan setiap internal anomaly, kerana alert yang tidak actionable hanya menghasilkan alert fatigue.

### State-based notification

Jangan hantar setiap 30 minit. Gunakan incident state machine:

```
NORMAL → WARNING:     hantar sekali
WARNING berterusan:   simpan log sahaja
WARNING → CRITICAL:   hantar escalation sekali
CRITICAL berterusan:  maksimum satu reminder selepas beberapa jam
WARNING/CRITICAL → RECOVERED: hantar satu recovery summary
```

### Quiet hours yang betul

Bukan sekadar "matikan notification waktu tidur":
- **INFO:** digest pagi
- **WARNING:** simpan dan digest pagi
- **CRITICAL/user-visible outage:** hantar serta-merta
- **Recovery:** gabungkan dengan incident asal

---

## 6. Strategi Swap yang Lebih Sihat

- **Jangan buat `swapoff`** ketika 2.1 GB masih digunakan — memaksa 2.1 GB kembali ke RAM boleh mencetuskan OOM atau freeze.
- **Restart bridge secara terkawal** memang akan membuang swap miliknya, tetapi itu hanya reset, bukan penyelesaian.
- **Pertimbangkan zswap:** menyimpan swap pages yang boleh dimampatkan dalam compressed RAM cache sebelum menulis ke disk. Menukar sedikit CPU untuk mengurangkan swap I/O dan latency.
  - Untuk VPS kecil: kekalkan disk swap sebagai fallback; gunakan zswap dengan pool kecil (15–20% RAM); monitor compression ratio dan CPU.
  - Jika VPS hanya ada satu/dua vCPU yang lemah, uji dahulu — compression juga mempunyai kos.
- **Jangan terlalu bergantung pada `vm.swappiness`:** Menurunkannya kepada 1 atau 10 bukan magic fix. Ia mungkin mengurangkan swap-out, tetapi membiarkan anonymous memory menekan file cache dan menghasilkan OOM lebih awal. Per-service `MemorySwapMax` dan admission control lebih tepat daripada tuning global yang agresif.

---

## 7. Pengoptimuman Host yang Berbaloi

### QCloud Agents (YunJing/barad)
~57 MB — kecil tetapi masih 2–3% daripada RAM.
- Semak sama ada kedua-duanya diwajibkan oleh provider.
- Jika salah satu optional, nilai manfaat security/monitoring sebelum disable.
- Jangan matikan blindly jika ia menyediakan vulnerability detection atau provider monitoring.

### Docker
39 MB bukan punca utama. Jangan lakukan migrasi besar semata-mata untuk menjimatkan 39 MB.
- Jika hanya ada dua servis mudah: systemd native boleh mengurangkan overhead, lebih mudah guna cgroup limits secara terus, lebih sedikit daemon dan log layer.
- Jika Docker memudahkan deployment/recovery, kekalkan. Reliability mungkin lebih bernilai daripada penjimatan kecil.

### Logging
- Pastikan journal mempunyai size cap.
- Log JSON tidak menyimpan payload/message penuh.
- Tiada debug logging Baileys berterusan.
- Child-process output tidak dikumpulkan dalam Python list.
- Rotation dan retention jelas.

---

## 8. Pelan Rollout: 4 Fasa

### Fasa 0 — Safety Guardrails (SEKARANG, tanpa data)

1. **Browser concurrency maksimum 1** — semaphore/queue. Browser job kedua tidak boleh spawn sehingga job pertama selesai.
2. **Browser timeout + whole-cgroup cleanup** — pastikan seluruh process tree dibersihkan.
3. **Health monitor deduplication** — satu notification WARNING, tiada ulang setiap 30 minit, satu escalation jika CRITICAL, satu recovery.
4. **Quiet-hour suppression** — untuk WARNING sahaja; CRITICAL masih dihantar.
5. **Aktifkan `MemoryAccounting=yes`** — tetapi jangan tetapkan `MemoryMax` dahulu.

Browser concurrency satu ialah **safety invariant**, bukan tuning berdasarkan guesswork, jadi tak perlu tunggu 48 jam.

### Fasa 1 — 48 jam: Observability

1. Log `process.memoryUsage()` bridge setiap 60 saat.
2. Rekod `/proc/PID/smaps_rollup`.
3. Rekod:
   - `memory.current`
   - `memory.swap.current`
   - `memory.events`
   - `/proc/pressure/memory`
   - `pswpin/pswpout`
   - OOM events
4. Tambah counters cache/listener/socket/reconnect.
5. Tukar alert kepada state-based deduplication.

**Matlamat:** tentukan sama ada 2.1 GB datang daripada JS heap, external buffer, cache, media atau historical cold pages.

### Fasa 2 — Minggu pertama: Containment

1. Pisahkan bridge, gateway dan browser kepada cgroup berasingan.
2. Tetapkan `MemoryHigh`, `MemoryMax`, `MemorySwapMax`.
3. Tetapkan browser concurrency = 1 (done in Fasa 0).
4. Gunakan timeout dan whole-cgroup cleanup.
5. Mulakan Node heap pada 384 MB.
6. Pin versi Baileys.

**Matlamat:** tiada satu komponen boleh menjatuhkan seluruh VPS.

### Fasa 3 — Minggu 2–4: Kurangkan working set

1. Gantikan unbounded/in-memory store dengan SQLite + bounded LRU.
2. Matikan unnecessary full-history sync.
3. Stream media; jangan buffer keseluruhan file.
4. Implementasikan pressure-aware admission control.
5. Gunakan HTTP/API-first sebelum browser.
6. Rotate gateway worker selepas context threshold.

**Matlamat:** baseline stabil walaupun sesi panjang.

### Fasa 4 — Jangka panjang

1. Jadikan VPS 2 GB sebagai control plane sahaja.
2. Hantar browser/code-heavy jobs kepada disposable worker.
3. Simpan conversation state secara durable dan ringkas.
4. Gunakan SLO:
   - Bridge uptime
   - Message delivery latency
   - Gateway response success
   - Job completion rate
5. Alert hanya apabila SLO atau survivability benar-benar terancam.

---

## 9. Cara Menetapkan cgroup Limit Kemudian

Jangan guna angka raw peak secara terus. Gunakan:

```
MemoryHigh ≈ p99 normal workload × 1.20 hingga 1.30
MemoryMax  ≈ MemoryHigh × 1.20 hingga 1.30
```

Contoh jika selepas clean run bridge menunjukkan:
- normal p99: 220 MB
- reconnect peak: 280 MB
- stable selepas reconnect: 230 MB

Maka permulaan lebih defensible:
```
MemoryHigh=320M
MemoryMax=420M
MemorySwapMax=256M
```

Bukan terus 500 MB hanya kerana itu nombor cadangan awal.

Untuk Node heap pula, jika:
- heapUsed p99 = 120 MB
- external p99 = 40 MB
- RSS p99 = 210 MB

heap limit 256–320 MB mungkin cukup. Tetapi jika `heapUsed` sendiri normalnya 300 MB, limit 384 MB terlalu rapat.

---

## 10. Cara Menentukan Tindakan Selepas 48 Jam

### Senario A — `heapUsed` meningkat berterusan
**Kemungkinan:** Baileys in-memory store, object retention, unbounded map/cache, reconnect listener leak.
**Tindakan:** Heap snapshot pada canary → audit retaining paths → bounded LRU/TTL → custom persistent store → kemudian aktifkan V8 heap limit sebagai containment.

### Senario B — `external` atau `arrayBuffers` meningkat
**Kemungkinan:** media buffering, WebSocket/TLS buffers, native library, file dibaca sepenuhnya ke RAM.
**Tindakan:** Tukar kepada streaming → hadkan media size → pastikan buffer references dilepaskan. `--max-old-space-size` BUKAN penyelesaian utama.

### Senario C — Semua metric Node stabil tetapi swap meningkat ketika browser aktif
**Kemungkinan:** Host-level memory pressure.
**Tindakan:** Browser admission control → browser disposable cgroup → `MemorySwapMax` per servis → pertimbangkan remote burst worker → selepas itu baru nilai zswap.

### Senario D — Memory melonjak setiap reconnect
**Audit:** socket lama tidak ditutup, event listeners bertindih, timers tertinggal, retry promises, store baharu dicipta tetapi store lama masih retained.

### Senario E — Gateway sahaja berkembang selepas compaction
**Tindakan:** Teruskan generational context design — durable checkpoint, disposable worker, rotation selepas compaction/RSS threshold, worker baru hydrate daripada summary minimum.

---

## 11. Satu Pembetulan Teknikal

**Original claim (Hermes):**
> "2.1 GB of real data that was once in RAM… evidence bridge historically needed that much working set."

**Versi lebih tepat:**
VmSwap=2.1 GB menunjukkan kira-kira 2.1 GB anonymous pages milik proses itu sedang berada dalam swap pada masa bacaan dibuat. Pages tersebut pernah disentuh/resident, tetapi tidak semestinya kesemua 2.1 GB pernah berada dalam physical RAM secara serentak.

Kesimpulan: bridge mempunyai current anonymous footprint yang sangat besar, tetapi belum boleh menyimpulkan peak concurrent RSS bridge ialah 2.1 GB tanpa data sejarah.

Ini penting agar forensic report tidak bertukar daripada satu overstatement kepada overstatement lain.

---

## 12. Arahan Eksekutif: Hybrid Rollout

### Jangan pilih antara "observe dahulu" dan "implement terus"

**Implement sekarang (Fasa 0 + Fasa 1 serentak):**
- Telemetry (bridge instrumentation)
- smaps_rollup, PSI dan cgroup logging
- Browser concurrency maksimum satu + queue
- Browser timeout + whole-cgroup cleanup
- Alert deduplication/state machine
- Bounded log rotation
- `MemoryAccounting=yes` tanpa hard limit dahulu

**Perlu tunggu data sebelum diaktifkan:**
- Nilai sebenar `MemoryHigh`
- Nilai `MemoryMax` dan `MemorySwapMax`
- `--max-old-space-size=384`
- Migration Baileys store
- Gateway context rotation
- zswap dan global kernel tuning

**Sebab:** Observability tanpa safety masih membenarkan insiden berulang, tetapi hard memory limit tanpa baseline pula boleh menyebabkan bridge crash secara tidak perlu.

### Jangan buat dahulu
- Jangan aktifkan `--max-old-space-size=384` sebelum clean baseline direkod
- Jangan set `MemoryMax`/`MemorySwapMax` secara agresif
- Jangan enable zswap
- Jangan tukar Baileys store kepada SQLite sekaligus
- Jangan disable QCloud agents
- Jangan ubah `vm.swappiness`
- Jangan implement gateway context rotation dalam deployment yang sama

Kita mahu satu perubahan observability/safety dahulu supaya attribution kekal jelas.

### Selepas 48 jam — hasilkan report berdasarkan:
- MB/jam untuk heapUsed, external, RSS dan swap
- Perubahan per 1,000 mesej
- Perubahan setiap reconnect
- Perubahan setiap browser job
- Memory sebelum/selepas compaction
- PSI dan swap-in ketika latency meningkat
- Sama ada memory kembali turun selepas workload reda

Kemudian baru cadangkan cgroup limits berdasarkan p95/p99 clean workload dengan headroom, bukan nombor andaian.

---

## 13. Step-by-Step Execution Sequence (untuk OpenCode / executor nanti)

### Step 1 — Preserve forensic evidence SEBELUM restart

Capture:
- `/proc/$BRIDGE_PID/status`
- `/proc/$BRIDGE_PID/smaps_rollup`
- `/proc/$GATEWAY_PID/status`
- `/proc/$GATEWAY_PID/smaps_rollup`
- `/proc/meminfo`
- `/proc/pressure/memory`
- `vmstat 1 10`
- `systemctl status` dan `systemctl show` untuk bridge/gateway
- cgroup `memory.current`, `memory.peak`, `memory.swap.current`, `memory.events` jika tersedia
- version Node.js, Python, Baileys, kernel dan systemd
- uptime setiap proses
- jumlah Chromium processes semasa

Simpan snapshot ini dengan timestamp sebagai **pre-reset forensic baseline**.

### Step 2 — Implement safety guardials segera

1. Browser concurrency maksimum 1 menggunakan semaphore/queue
2. Browser job kedua tidak boleh spawn sehingga job pertama selesai
3. Tambah browser timeout dan pastikan seluruh process tree dibersihkan
4. Health monitor deduplication: satu notification WARNING, tiada ulang setiap 30 minit, satu escalation jika CRITICAL, satu recovery
5. Tambah quiet-hour suppression untuk WARNING sahaja; CRITICAL masih dihantar
6. Aktifkan `MemoryAccounting=yes`, tetapi jangan tetapkan `MemoryMax` dahulu

### Step 3 — Instrument bridge

Log setiap 60 saat: `rss`, `heapUsed`, `heapTotal`, `external`, `arrayBuffers`, V8 `heap_size_limit`, process uptime, active resources/handles, reconnect count, listener count, cache/store entry counts, queued job count, jumlah mesej diproses, jumlah dan saiz media diproses.

Jangan log message content, credentials atau auth keys. Gunakan JSONL dengan rotation/size cap.

### Step 4 — Instrument host dan cgroup

Setiap 60 saat, rekod: `MemAvailable`, swap used, `pswpin`/`pswpout`, PSI memory `some`/`full`, process `Pss`/`Anonymous`/`Swap`/`SwapPss`, cgroup `memory.current`/`memory.peak`/`memory.swap.current`/`memory.events`, bilangan proses Chromium.

Ambil event snapshot tambahan: sebelum dan selepas browser job, selepas gateway compaction, selepas Baileys reconnect, selepas media besar, ketika alert bertukar state.

### Step 5 — Controlled clean restart

Selepas forensic snapshot dan instrumentation siap:
1. Restart bridge secara terkawal
2. Verify WhatsApp reconnect/session recovery
3. Jangan buat `swapoff`
4. Rekod clean-start baseline pada: minit 1, minit 5, minit 30, selepas mesej pertama, selepas browser job pertama

Restart diperlukan supaya data 24–48 jam selepas itu menunjukkan growth daripada clean state, bukan sekadar 2.1 GB cold pages daripada workload lama.

### Step 6 — Observe selama 48 jam

Observation mesti merangkumi workload sebenar, bukan idle sahaja: long conversation, beberapa web searches, sekurang-kurangnya satu browser job, media kecil/sederhana jika biasa digunakan, reconnect jika berlaku secara natural.

Jangan sengaja stress production sehingga berisiko.

---

*End of PX-3 raw findings. This document is a reference for future overhaul execution when the freeze is lifted.*
