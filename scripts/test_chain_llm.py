import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chain_llm

class TestChainLLMProviderAdapter(unittest.TestCase):
    def test_reminder_format_accepts_natural_template(self):
        text = (
            "‼️ Waktu Ubat (Malam) ‼️\n\n"
            "Morning boss, Levetiracetam 500mg belum makan lagi, now dah 8pm ni. "
            "Take asap ya, nanti update saya.\n\n"
            "[E:1-260720]"
        )
        self.assertTrue(chain_llm.validate_reminder_text(text, "E", [
            {"drug": "Levetiracetam", "dosage": "500mg"},
        ]))

    def test_reminder_format_rejects_robotic_ready_since(self):
        text = (
            "‼️ Waktu Ubat (Malam) ‼️\n\n"
            "Morning boss, Levetiracetam belum makan lagi — dah ready sejak 8pm.\n\n"
            "[E:1-260720]"
        )
        self.assertFalse(chain_llm.validate_reminder_text(text, "E", [
            {"drug": "Levetiracetam", "dosage": "500mg"},
        ]))

    def test_reminder_format_rejects_generic_drug_name(self):
        text = (
            "‼️ Waktu Ubat (Malam) ‼️\n\n"
            "Hai boss, ubat malam belum makan lagi, dah lewat ni. Take asap ya.\n\n"
            "[E:1-260720]"
        )
        self.assertFalse(chain_llm.validate_reminder_text(text, "E", [
            {"drug": "Levetiracetam", "dosage": "500mg"},
        ]))
    def test_deterministic_renderer_obeys_contract_for_partial_c(self):
        chain = {
            "now": "13:22",
            "reminder_counts": {"C": 1},
        }
        slot_meta = {
            "pending_drugs": [
                {"drug": "Calcium Carbonate", "dosage": "500mg"},
                {"drug": "Calcitriol", "dosage": "1 tablet"},
            ],
        }
        text = chain_llm.render_reminder("C", chain, slot_meta, date_code="260722")
        self.assertTrue(chain_llm.validate_reminder_text(text, "C", slot_meta["pending_drugs"]))
        self.assertIn("Calcium Carbonate 500mg", text)
        self.assertIn("Calcitriol 1 tablet", text)
        self.assertNotIn("Dexamethasone", text)
        self.assertIn("[C:2-260722]", text)

    def test_deterministic_renderer_rejects_missing_pending_drugs(self):
        with self.assertRaises(ValueError):
            chain_llm.render_reminder("C", {"now": "13:22"}, {"pending_drugs": []}, date_code="260722")

    def test_renderer_heads_up_when_not_yet_ready(self):
        chain = {"now": "08:55", "reminder_counts": {"B": 1}}
        slot_meta = {
            "pending_drugs": [
                {"drug": "Levetiracetam", "dosage": "500mg (1 tab)"},
                {"drug": "Dexamethasone", "dosage": "5mg"},
            ],
            "ready_time": "09:10",
            "status": "ready",  # flips at ready-15 even before actually due
        }
        text = chain_llm.render_reminder("B", chain, slot_meta, date_code="260802")
        self.assertTrue(chain_llm.validate_reminder_text(text, "B", slot_meta["pending_drugs"]))
        self.assertIn("boleh ambil lepas 09:10", text)
        self.assertNotIn("belum ambil lagi", text)
        self.assertIn("[B:2-260802]", text)

    def test_renderer_normal_reminder_when_ready(self):
        chain = {"now": "09:10", "reminder_counts": {"B": 1}}
        slot_meta = {
            "pending_drugs": [
                {"drug": "Levetiracetam", "dosage": "500mg (1 tab)"},
                {"drug": "Dexamethasone", "dosage": "5mg"},
            ],
            "ready_time": "09:10",
        }
        text = chain_llm.render_reminder("B", chain, slot_meta, date_code="260802")
        self.assertTrue(chain_llm.validate_reminder_text(text, "B", slot_meta["pending_drugs"]))
        self.assertIn("belum ambil lagi", text)
        self.assertNotIn("boleh ambil lepas", text)
        self.assertIn("[B:2-260802]", text)

    def test_escalation_gentle_for_low_counts(self):
        for prior in (0, 1):  # reminder #1 and #2
            chain = {"now": "09:25", "reminder_counts": {"B": prior}}
            slot_meta = {"pending_drugs": [{"drug": "Levetiracetam", "dosage": "500mg"}]}
            text = chain_llm.render_reminder("B", chain, slot_meta, date_code="260802")
            self.assertTrue(chain_llm.validate_reminder_text(text, "B", slot_meta["pending_drugs"]))
            self.assertIn("belum ambil lagi. Dah pukul 09:25", text)
            self.assertNotIn("kali ke-", text)

    def test_escalation_push_for_mid_counts(self):
        chain = {"now": "09:55", "reminder_counts": {"B": 3}}
        slot_meta = {"pending_drugs": [{"drug": "Levetiracetam", "dosage": "500mg"}]}
        text = chain_llm.render_reminder("B", chain, slot_meta, date_code="260802")
        self.assertTrue(chain_llm.validate_reminder_text(text, "B", slot_meta["pending_drugs"]))
        self.assertIn("ini kali ke-4", text)
        self.assertIn("jangan lupa", text)
        self.assertNotIn("ambil sekarang", text)

    def test_escalation_urgent_for_high_counts(self):
        chain = {"now": "10:55", "reminder_counts": {"B": 5}}
        slot_meta = {"pending_drugs": [{"drug": "Levetiracetam", "dosage": "500mg"}]}
        text = chain_llm.render_reminder("B", chain, slot_meta, date_code="260802")
        self.assertTrue(chain_llm.validate_reminder_text(text, "B", slot_meta["pending_drugs"]))
        self.assertIn("Hai boss!!", text)
        self.assertIn("dah 6 kali saya ingatkan", text)
        self.assertIn("ambil sekarang", text)

if __name__ == "__main__":
    unittest.main()
