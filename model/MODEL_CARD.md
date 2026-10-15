# MiniRouter v0.1.0-alpha.1 model card

**Status:** experimental alpha; not production-ready.

## Intended use

Recommend a next route for short English requests: `coding`, `reasoning`, `search`, `database`, or a narrowly defined `no_llm` calculator route. Four capability scores indicate coding, reasoning, search, and database needs. The caller decides whether to act, validate the request, and run any downstream system. Abstention is a supported output.

The model does not execute code, evaluate arbitrary expressions, search the web, query a database, or call another model. The deterministic path accepts only the documented bounded `calc:` grammar when a trusted calculator handler is explicitly enabled. It must not be treated as a general guarantee that a request needs no model.

## Model and size

- Backbone: `jhu-clsp/ettin-encoder-17m`, pinned revision `987607455c61e7a5bbc85f7758e0512ea6d0ae4c`.
- Encoder: 7 layers, hidden width 256, 4 attention heads, intermediate width 384, RoPE and GeGLU.
- Heads: five-way primary route and four independent capability outputs.
- Unique learned parameters: **16,831,497** (16,797,440 encoder; 34,057 heads).
- Export: ONNX CPU inference with mixed INT4 embedding and INT8 matrix quantization; tokenizer, calibration, policy, configuration, license notices, and manifest are included.
- Bundle limit: 15,000,000 uncompressed bytes. The package builder measures the actual release copy and records every member hash.
- Python/ONNX Runtime dependencies and process memory are separate from this model asset size.

## Training and data

The encoder was fine-tuned on internally curated examples with fixed train/development/calibration splits. Candidate source prompts were adapted from MBPP (Apache-2.0), GSM8K (MIT), and SQL Create Context (CC-BY-4.0; its card identifies WikiSQL/Spider-derived material), plus internally authored synthetic examples. Source references, pinned revisions, and checksums are recorded in `reports/DATA_SOURCES.json`; license texts and attribution are in `data/licenses/` and `THIRD_PARTY_NOTICES.md`. No raw datasets are part of the release package.

The collection is an internal bootstrap corpus, not user traffic. Some rows were reviewed internally and many were not; source-group separation does not establish semantic near-duplicate or pretraining-contamination separation. Synthetic unsupported-request examples do not measure real-world traffic coverage.

## Evaluation and limitations

The one-use locked inference report was only partially recovered after a serialization error. On the 500-row internal main split, the quantized bundle achieved 495/500 primary accuracy (99.0%) and macro-F1 0.989936. The supporting-capability macro-F1 was 0.725422; database capability recall was 1/100. These fail the predeclared supporting-capability target. The calibrated policy routed 402/500 rows with 2 errors. It selected all 100 narrow typed-calculator examples correctly, with exact 95% interval [0.9638, 1.0]; that small grammar-specific sample does not establish general no-LLM precision.

The evaluation-only linear control scored macro-F1 0.992028 against 0.989936 for the quantized neural model. The paired neural-minus-control interval was [-0.011498, 0.006529], so the predeclared comparative-gain target was not met. The challenge section is incomplete and no missing outcomes were reconstructed. The single-use marker remains consumed; the pass was not repeated.

These results describe the supplied internal examples only. They do not establish general accuracy, representative coverage, production readiness, demand, cost savings, or superiority over other routers. Language coverage is English only. Unsupported domains, ambiguous or contradictory requests, and requests beyond the input limits may be abstained or misrouted; a caller must retain its own safeguards and fallback path.

## Ethical and operational considerations

Routing can expose sensitive requests to downstream services. This package itself makes no external calls, but a caller may. Validate privacy, authorization, destination availability, and downstream behavior before routing. Avoid sending sensitive prompts to the local demo unless the environment is trusted. Do not rely on model scores as proof that a route is safe.

## License

MiniRouter's own code is MIT licensed. The upstream Ettin license and training-source attributions are reproduced in `THIRD_PARTY_NOTICES.md` and packaged alongside the model.
