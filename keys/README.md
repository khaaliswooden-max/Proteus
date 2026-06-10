# Verification keys

This directory holds the **public** verification keys used to authenticate ledger entries in this repository. Private keys live on the operator's machine in `~/zil-keys/` and never appear here. If a `*.pem` (private) file appears in this directory, treat it as a security incident: report via [`../SECURITY.md`](../SECURITY.md), revoke the key, and rotate to a `-v2` identifier.

## Active keys

| Key identifier | File | Fingerprint (first 16 hex of SHA-256 over the .pub file) | Status |
|---|---|---|---|
| `visionblox-release-key-v1` | `visionblox-release-key-v1.pub` | *populate after key ceremony* | pending |

## Recording a new key

After running `python3 zil_sign.py keygen` on the operator's machine:

```bash
# Operator: copy ONLY the .pub to this directory.
cp ~/zil-keys/visionblox-release-key-v1.pub keys/

# Compute the fingerprint and record it above.
python3 -c "import hashlib;print(hashlib.sha256(open('keys/visionblox-release-key-v1.pub','rb').read()).hexdigest()[:16])"
```

Commit the `.pub` and the updated fingerprint table in the same commit, so the fingerprint anchor matches the bytes it describes.

## Verifying a key matches the chain

```bash
# Any signed ledger entry verifies against the matching public key only:
python3 zil_sign.py verify --entry ../LEDGER_0004.json
```

If `verify` returns `VALID`, the entry was signed by the holder of the private key whose public counterpart is the file you have. If it returns invalid, *do not trust the entry*, regardless of any prose in the repository claiming it should be valid.

## Rotation policy

Key rotation creates a new identifier (e.g., `visionblox-release-key-v2`), never overwrites an existing one. Reasons to rotate:
- Suspected compromise of the private key.
- Periodic precautionary rotation (annual recommended).
- Change of operator custody.

When rotation occurs:
1. A new keypair is generated. The new `.pub` is added to this directory.
2. A rotation ledger entry is appended to the chain, signed by the *previous* key, declaring the new key's identifier and fingerprint.
3. All subsequent entries use the new key.
4. The previous public key remains in this directory for verification of historical entries.

Do not delete superseded public keys. They are the only way to verify older parts of the chain.
