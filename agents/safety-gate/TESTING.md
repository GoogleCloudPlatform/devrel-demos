# Testing

`safety-gate` includes over 640 automated checks across two test suites. Dangerous commands are evaluated strictly as strings and JSON payloads inside a temporary directory and are never executed on your machine.

## Running the Test Suites

```bash
# 1. Unit and integration tests (under 1s offline)
python3 -m unittest test_safety_gate.py

# 2. 300 realistic and adversarial tool-call test cases in parallel
python3 test_corpus.py --workers 8
```

- **Unit & install tests ([`test_safety_gate.py`](./test_safety_gate.py)):** Tests Stage 1, 2, and 3 routing, decision caching, fail-closed timeouts, CLI commands, and symlink or prompt-injection defenses.
- **300-case benchmark corpus ([`test_corpus.py`](./test_corpus.py) + [`test_corpus.json`](./test_corpus.json)):** Evaluates `190` safe commands (`allow`) and `110` dangerous commands (`deny`) end-to-end with conversation transcripts.
- **41,010-call historical replay:** Evaluated on `40,998` safe and `12` dangerous tool calls from real coding-agent sessions before and after hardening (see [README.md](./README.md)).

## Cross-Platform Verification

- [x] **Linux:** Verified `install`, `setup-key`, `doctor`, live hook execution, unit tests, and the 300-case corpus.
- [x] **macOS:** Verified `install`, Keychain setup, live `agy` CLI hooks, `uninstall`, unit tests, and the 300-case corpus.
- [x] **Windows:** Verified `install`, `setup-key`, `doctor`, `cmd.exe` hooks, backslash path rules, unit tests, and the 300-case corpus.
