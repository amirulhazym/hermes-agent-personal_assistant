#!/usr/bin/env python3
"""Import one GPG-encrypted API key into a Hermes .env file.

The ciphertext may traverse Telegram. The plaintext is never printed or
written outside the destination .env file.
"""
import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ALLOWED_VARIABLES = {
    "OPENROUTER_API_KEY",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "DEEPSEEK_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "XAI_API_KEY",
    "HF_TOKEN",
    "DASHSCOPE_API_KEY",
    "GLM_API_KEY",
    "MINIMAX_API_KEY",
    "KIMI_API_KEY",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--var", required=True, dest="variable")
    parser.add_argument("--ciphertext", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, default=Path.home() / ".hermes" / ".env")
    parser.add_argument("--gpg-bin", default="gpg")
    return parser.parse_args()


def decrypt(ciphertext: Path, gpg_bin: str) -> str:
    result = subprocess.run(
        [gpg_bin, "--batch", "--quiet", "--decrypt", str(ciphertext)],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode:
        raise ValueError("Could not decrypt ciphertext")
    value = result.stdout.decode("utf-8").rstrip("\r\n")
    if not value or "\n" in value or "\r" in value or "\x00" in value:
        raise ValueError("Decrypted value must be one non-empty line")
    return value


def replace_env_value(existing: str, variable: str, value: str) -> str:
    prefix = f"{variable}="
    lines = [line for line in existing.splitlines() if not line.startswith(prefix)]
    lines.append(prefix + value)
    return "\n".join(lines) + "\n"


def atomic_write(path: Path, data: str) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".env.", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def main() -> int:
    args = parse_args()
    if args.variable not in ALLOWED_VARIABLES:
        print("Refused: variable is not allowlisted", file=sys.stderr)
        return 2
    if not args.ciphertext.is_file():
        print("Refused: ciphertext file does not exist", file=sys.stderr)
        return 2
    try:
        value = decrypt(args.ciphertext, args.gpg_bin)
        existing = args.env_file.read_text(encoding="utf-8") if args.env_file.exists() else ""
        atomic_write(args.env_file, replace_env_value(existing, args.variable, value))
        args.ciphertext.unlink()
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        print(f"Import failed: {exc}", file=sys.stderr)
        return 1
    print(f"Imported {args.variable}; ciphertext removed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())