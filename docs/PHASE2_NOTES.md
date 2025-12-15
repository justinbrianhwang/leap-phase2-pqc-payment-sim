# Notes from Project Leap Phase 2 (for this toy repo)

This file is a **reading aid** that explains which *specific* Phase-2 facts this repository tries to mirror at a high level.

This is **not** an official BIS document.

## Key facts used in this repo

### 1) Target: BAH digital signature in a TARGET2-style liquidity transfer flow

Project Leap Phase 2 focuses on the **Business Application Header (BAH)** signature used in a liquidity transfer workflow (ISO 20022 context).

This repo mirrors that by:
- Treating the message as `(BAH + LiquidityTransfer payload)`
- Signing **only the BAH** (like “signature-on-header” designs)

### 2) PQC algorithm family: Dilithium-like (lattice signatures)

The report describes using a **CRYSTALS-Dilithium** variant (NIST Round 3, security strength category 3) and notes that it was not possible to test the newer standardised name “ML-DSA” within the experiment timeframe.

In this repo:
- the default PQC mode is `MOCK-DILITHIUM3` (portable, runs everywhere)
- there is an optional real-PQC backend using **liboqs-python** if installed

### 3) Performance gap: verification time increases significantly

The report highlights a **large verification-time gap**, and provides a measured average (in their setup) of approximately:
- ~28.1 ms (traditional)
- ~209.9 ms (PQC)

This repo:
- measures verification time at the “gateway” verification point
- includes synthetic example charts that reflect this order-of-magnitude gap

## What this repo does *not* attempt

- Exact TARGET2 internal interfaces, ESMIG details, or SWIFT formats
- HSM integration, smartcards, certificate chain building, revocation
- Real operational risk analysis, regulatory constraints, or production readiness

## Suggested extensions (if you want to go deeper)

- Add an HSM / PKCS#11 verification step (and measure latency)
- Add certificate lifecycle simulation (key rotation, expiry, revocation)
- Implement interoperability tests across PQC libraries (key formats, OIDs)
- Add replay-protection / message sequencing constraints
- Add batching and “bulk” message modes (to see throughput collapse)

