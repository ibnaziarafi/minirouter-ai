# MiniRouter v0.1.0-alpha.1 release record

**Readiness: experimental local alpha; production readiness blocked.** The package is a reproducible way to inspect the selected model and try its local API and web page. It does not claim production quality.

## Model artifact

- Source frozen model: `artifacts/trained-v3-bundle/model.onnx`, SHA-256 `6c369081c5b9a58b10c944b394c4139cf6309fb334c6489be9ef98e3a07f545f`.
- Source calibration: SHA-256 `69ed4ff3ef0b2485ef5426d9103cb9d7657ff60ebf5a032206c7a5b3ef09ea76`.
- Source policy: SHA-256 `35e4662e46631c1662fc2f50f798b4bac37f8c31ed179e72f09f32ee48243f54`.
- Parameter count: 16,831,497 unique learned parameters.
- Bundle cap: 15,000,000 uncompressed bytes. From the source project root, run `python scripts/package_release.py` to build `artifacts/releases/minirouter-v0.1.0-alpha.1/`, its deterministic zip, and SHA-256 sidecar. The generated package directory/zip contains the app, runtime lock, docs, and model assets; it does not include the original frozen training bundle needed to rebuild that package.
- Run `python scripts/package_release.py --check-only` from the source project root to verify the generated package against the local source tree. The check covers frozen model/calibration/policy hashes, allowlisted contents, all member hashes, and the complete inference bundle size.
- Original frozen V3 bundle: 13,436,702 bytes. Documentation-complete model copy: **13,444,659 bytes**. The ONNX model, calibration, and policy hashes remain identical to the frozen inputs above.

## Evaluation evidence

Only partial locked aggregate evidence is available because report serialization failed after the one-use inference reservation was consumed. The inference was not repeated. The 500-row main split produced 495/500 (99.0%) quantized primary accuracy and 0.989936 macro-F1. Supporting capability macro-F1 was 0.725422, including database capability recall of 1/100, which fails the predeclared gate. The linear control scored 0.992028 macro-F1; the neural model did not meet its predeclared comparative-gain target. The policy selected 402/500 rows with 2 observed errors. All 100 narrow typed-calculator cases were selected correctly, with exact 95% interval [0.9638, 1.0]; this does not establish broad no-LLM precision.

The report lacks full per-row outputs and later challenge backend metrics. These missing values are not inferred. See `paired-locked-v3-partial.json` for the recoverable data and `STOP_CHECKPOINT.md` for the one-shot boundary. The full challenge corpus and training assets are excluded from the release package.

## Runtime and recovery

1. Check the archive digest using the generated `.sha256` sidecar.
2. Extract the archive into a clean directory. The server verifies every model member against its bundled manifest during startup. To recheck the ZIP from the source repository, run `python scripts/package_release.py --check-only`. These checks verify package bytes, not model quality.
3. Create a Python 3.12 virtual environment, install the pinned `requirements-runtime.lock.txt`, and run `scripts/serve_preview.py --port 8767`.
4. Stop the foreground server with Ctrl+C. It binds to loopback only.

If a package check fails, preserve the release directory and error output. Rebuild from the source tree and the unchanged frozen `artifacts/trained-v3-bundle`; do not replace the frozen source files or rerun locked inference. If the frozen source artifact is unavailable or its recorded hash differs, stop and restore from the saved local checkpoint before packaging.

## Scope

The public project Git push is owned by the manager and is separate from the release package build. No public model hosting or deployment was performed here. This alpha contains no real traffic evidence, downstream outcome measurements, cost study, or production approval.
