import subprocess
import sys
from pathlib import Path

SCRIPT_PATH = Path("/home/ubuntu/hermes-agent-personal_assistant-work/scripts/mri_reminder.py")

def run_script(stage: str):
    cmd = [sys.executable, str(SCRIPT_PATH), "--stage", stage]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res

def test_mri_reminder_catchup():
    res = run_script("catchup")
    assert res.returncode == 0
    assert "MRI HKL — Isnin 19 Okt (Lagi 3 Hari)" in res.stdout
    assert "8:00 AM – 10:00 AM" in res.stdout
    assert "LRT IOI Puchong Jaya ➔ HKL" in res.stdout

def test_mri_reminder_day3_evening():
    res = run_script("day3_evening")
    assert res.returncode == 0
    assert "MRI HKL — Isnin 19 Okt (Lagi 3 Hari)" in res.stdout
    assert "8:00 AM – 10:00 AM" in res.stdout
    assert "LRT IOI Puchong Jaya ➔ HKL" in res.stdout

def test_mri_reminder_day2_morning():
    res = run_script("day2_morning")
    assert res.returncode == 0
    assert "MRI HKL — Isnin 19 Okt (Lagi 2 Hari)" in res.stdout
    assert "8:00 AM – 10:00 AM" in res.stdout

def test_mri_reminder_day2_evening():
    res = run_script("day2_evening")
    assert res.returncode == 0
    assert "MRI HKL — Isnin 19 Okt (Lagi 2 Hari)" in res.stdout
    assert "aksesori berlogam" in res.stdout

def test_mri_reminder_day1_morning():
    res = run_script("day1_morning")
    assert res.returncode == 0
    assert "ESOK PAGI" in res.stdout
    assert "LRT IOI Puchong Jaya ➔ HKL" in res.stdout

def test_mri_reminder_day1_evening():
    res = run_script("day1_evening")
    assert res.returncode == 0
    assert "ESOK PAGI!" in res.stdout
    assert "Checklist Malam Ini" in res.stdout
    assert "Kunci jam penggera" in res.stdout
