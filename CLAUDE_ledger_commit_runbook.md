# CLAUDE.md — Ledger Commit Runbook (ZCS-6 Phase 4 Completion)

**Repo:** zandbox · **Owner:** A. Khaalis Wooden, Sr. / Visionblox LLC / Zuup Innovation Lab
**Goal of this runbook:** complete Phase 4 (deterministic defense) for `proteus-bench-v1.0.1` so the project may enter Phase 5. Tools: `zil_sign.py`, `cryptography`, `ots` (opentimestamps-client), `git`.

You are an AI collaborator (Claude Code / Cursor). Execute the AGENT tasks autonomously. STOP at every gate marked **HUMAN-ONLY** and surface the exact command for the operator to run. Do not attempt to work around a gate.

---

## 0. Hard boundaries (non-negotiable)

1. **Never generate, read, request, store, echo, or log a private key or its passphrase.** `visionblox-release-key-v1.pem` and its passphrase are operator-only. If any task seems to require them, STOP and hand off.
2. **Never run `zil_sign.py keygen` or `zil_sign.py sign` yourself.** Both prompt for the passphrase interactively; the operator runs them. You prepare inputs and verify outputs.
3. **Never commit a `*.pem` or any file matching `*key*.pem` / `*private*`.** Verify `.gitignore` blocks them before any `git add`.
4. **Never silently edit a committed, OTS-stamped bundle.** Changes require a versioned re-commit with a delta record (this is how v1.0.1 came to exist).
5. If a manifest hash you recompute does not match the expected value, STOP. Do not sign, do not commit. Report the mismatch.

---

## 1. Prerequisites — verify before doing anything (AGENT)

Run and report a checklist:

```bash
python3 -c "import cryptography; print('cryptography', cryptography.__version__)"
which ots && ots --version            # for upgrade/verify of .ots files
test -f zil_sign.py && echo "zil_sign.py present"
ls -d proteus-bench-v1.0.1 && echo "bundle present"
grep -qE '(\*\.pem|key.*\.pem)' .gitignore && echo ".gitignore blocks pem" || echo "ADD *.pem TO .gitignore FIRST"
```

If `.gitignore` does not block `*.pem`, add this and commit it **before** any key exists:
```
# secrets — never commit
*.pem
*private*
~/zil-keys/
```

**Locate the existing ledger chain.** Find prior entries `LEDGER_0001..0003` (or the documents that define their canonical payloads). Report what exists:
```bash
git ls-files | grep -iE 'ledger|LEDGER' || echo "no ledger files tracked"
```
- If canonical payloads for #0001–#0003 exist → step 3 can proceed.
- If only manifest hashes exist in prose (no `aletheia-ledger-entry-v1` payloads) → **flag it**: step 3 requires constructing those payloads now. Surface this to the operator as a decision, do not invent historical metadata.

---

## 2. Task 1 — Key ceremony  ⛔ HUMAN-ONLY

The operator creates the signing identity once. **You do not run this.** Present these instructions and wait:

```bash
mkdir -p ~/zil-keys && cd ~/zil-keys
cp /path/to/zil_sign.py .
pip install cryptography
python3 zil_sign.py keygen          # prompts for passphrase twice
```

Outputs: `visionblox-release-key-v1.pem` (PRIVATE, stays in ~/zil-keys + offline backup) and `visionblox-release-key-v1.pub` (PUBLIC).

**AGENT resumes when** the operator confirms `visionblox-release-key-v1.pub` exists. Then:
- Copy ONLY the `.pub` into the repo (e.g. `keys/visionblox-release-key-v1.pub`).
- Record its fingerprint in `keys/README.md`:
  ```bash
  python3 -c "import hashlib;print(hashlib.sha256(open('keys/visionblox-release-key-v1.pub','rb').read()).hexdigest()[:16])"
  ```
- Confirm `git status` shows no `.pem`. Commit the `.pub` + fingerprint.

---

## 3. Task 2 — Resolve the #0004 entry-number collision (AGENT decision-record)

Two candidates claim #0004: **PROTEUS-002** (ready now) and **CADUCEUS-004** (held pending 5 Category A tightenings + practitioner review).

**Default resolution (apply unless operator overrides):** Proteus takes **#0004** (it is signing-ready); Caduceus becomes **#0005** when its tightenings land.

Record the decision in `LEDGER_CHAIN.md` (create if absent): entry number, document ID, manifest hash, date, rationale. This file is the human-readable index of the chain. Commit it.

---

## 4. Task 3 — Prepare (and operator-sign) the chain  ⛔ SIGNING IS HUMAN-ONLY

**Key fact that makes this safe and easy:** `prev_ledger_hash` is the SHA-256 of the *previous entry's canonical payload*, which is independent of any signature. So you can compute the entire forward chain deterministically; the operator only enters the passphrase to attach signatures.

**3a. AGENT — assemble payloads in order (GENESIS → 0001 → 0002 → 0003 → 0004).**
For each entry, build the `aletheia-ledger-entry-v1` payload (schema in `zil_sign.py`). For #0001–#0003 use their real committed metadata (located in step 1); if those payloads must be constructed for the first time, STOP and get operator confirmation of each historical manifest hash before proceeding — do not guess.

Compute each payload's `payload_sha256` and set the next entry's `prev_ledger_hash` to it. The first entry in the chain uses `prev_ledger_hash = "GENESIS"`. Produce a table the operator can eyeball:

| entry | doc_id | manifest_hash (first 16) | prev_ledger_hash (first 16) |
|---|---|---|---|

Verify every bundle hash independently before listing it:
```bash
python3 zil_sign.py sign --help   # confirm flags; do NOT run 'sign'
# For hash verification only, recompute via the bundle_hash logic:
python3 - <<'PY'
import importlib.util,hashlib
from pathlib import Path
s=importlib.util.spec_from_file_location("zs","zil_sign.py");zs=importlib.util.module_from_spec(s);s.loader.exec_module(zs)
print(zs.bundle_hash(Path("proteus-bench-v1.0.1")))
PY
```

**3b. HUMAN-ONLY — operator signs, oldest first.** Hand over the exact commands. Retro-signing #0001–#0003 is RECOMMENDED for end-to-end authority but is NOT a Phase 5 blocker (the forward chain linkage is already intact via payload hashes). The Phase 5 blocker is the signed #0004 in Task 4. Example for one historical entry:
```bash
cd ~/zil-keys
python3 zil_sign.py sign \
  --bundle /path/to/<bundle> \
  --expected-hash <manifest_hash_from_table> \
  --entry-number <N> \
  --prev-hash <prev_ledger_hash_from_table> \
  --doc-id <DOC_ID> \
  --title "<title>"
# prompts for passphrase → writes LEDGER_000N.json
```

**AGENT resumes** after the operator returns each `LEDGER_000N.json`: verify it without the private key —
```bash
python3 zil_sign.py verify --entry LEDGER_000N.json   # expects 'VALID'
```
Only `verify: VALID` entries get committed.

---

## 5. Task 4 — Sign & commit proteus-bench v1.0.1  ⛔ SIGNING IS HUMAN-ONLY

**5a. AGENT — final pre-sign verification:**
- Recompute bundle hash; assert it equals `03e27b6284405adb3dcdae5587be7f58cdb28677a2556105f710284cb4355bb6`.
- Set `--prev-hash` = `payload_sha256` of the #0003 entry from the Task 3 table (or `GENESIS` if the operator elects Proteus as the first signed entry).
- Hand the operator this exact command (fill `<PREV_HASH>`):

```bash
cd ~/zil-keys
python3 zil_sign.py sign \
  --bundle /path/to/proteus-bench-v1.0.1 \
  --expected-hash 03e27b6284405adb3dcdae5587be7f58cdb28677a2556105f710284cb4355bb6 \
  --entry-number 4 \
  --prev-hash <PREV_HASH> \
  --doc-id PROTEUS-002 \
  --title "PROTEUS-Bench v1.0.1 — Online State Adaptation Benchmark (Sixth Road Candidate)"
```

**5b. HUMAN-ONLY** — operator runs it, enters passphrase, returns `LEDGER_0004.json`.

**5c. AGENT — verify, anchor, commit:**
```bash
python3 zil_sign.py verify --entry LEDGER_0004.json        # must print VALID
ots upgrade proteus-bench-v1.0.1/BUNDLE_HASH.txt.ots 2>/dev/null || echo "OTS not yet confirmed (Bitcoin block pending ~a few hrs); retry later"
ots verify proteus-bench-v1.0.1/BUNDLE_HASH.txt.ots 2>/dev/null || true
```
Then commit, in one logical commit:
- `LEDGER_0004.json`
- `proteus-bench-v1.0.1/` (bundle, incl. `MANIFEST.json`, `DELTA_v1.0.1.md`, `BUNDLE_HASH.txt`, `.ots`)
- updated `LEDGER_CHAIN.md` (append #0004 row)
- `keys/visionblox-release-key-v1.pub` (if not already committed)

Commit message:
```
ledger: commit PROTEUS-002 as entry #0004 (proteus-bench v1.0.1)

manifest 03e27b62…; supersedes PROTEUS-001 (F-B1 defect, see DELTA_v1.0.1.md).
Ed25519 signed (visionblox-release-key-v1); OTS-anchored.
```
Push. Confirm `git log` shows no `.pem` ever entered history (`git log --all -- '*.pem'` must be empty).

---

## 6. Definition of done → Phase 5 entry gate

Phase 4 is complete when ALL are true:
- [ ] `visionblox-release-key-v1.pub` committed; no `.pem` in repo or history.
- [ ] #0004/#0005 collision resolved and recorded in `LEDGER_CHAIN.md`.
- [ ] `LEDGER_0004.json` exists and `verify` → VALID.
- [ ] `proteus-bench-v1.0.1` bundle committed with its `.ots`; `ots upgrade` scheduled/done.
- [ ] (Recommended, not blocking) #0001–#0003 signed and verified.

**Only then** begin Phase 5, first action: **F0 baseline harness on Mistral-7B-Instruct-v0.3**, which pins the llama.cpp build hash that assertion B1b and the calibration band bind to. First Loop A v0.2 item: **F-A3 — graded nonconformity** for the ACI skill proxy (binary outcomes saturate it at the competence floor; see LOOP_A_RUN_REPORT.md).

## 7. Stop conditions (escalate to operator, do not improvise)

- Any hash mismatch.
- Historical payloads (#0001–#0003) not locatable and metadata uncertain.
- `verify` returns anything but VALID.
- A `.pem` appears in `git status`.
- Any instruction would require you to handle the passphrase.
