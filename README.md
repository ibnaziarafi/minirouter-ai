# MiniRouter v0.1.0-alpha.1

MiniRouter is an experimental English request router. It recommends one of five next routes—coding, reasoning, search, database, or a supported no-LLM calculator path—and can abstain. It never executes a route or contacts a model, search service, or database.

This alpha includes a **16,831,497-parameter** fine-tuned Ettin encoder and a complete 13,444,659-byte inference bundle under the 15,000,000-byte limit. Read [the model card](MODEL_CARD.md), [how the model works](reports/HOW_MINIROUTER_WORKS.md), and [release evidence](reports/RELEASE_V3.md) before using results. The held-out report was only partially recovered: primary accuracy was high, but database capability recall and the comparative-gain target failed. This is for local experimentation, not production decisions or cost-savings claims.

## Run locally

Requirements: Python 3.12. From this project directory:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-runtime.lock.txt
.venv/bin/python scripts/serve_preview.py --port 8767
```

Open <http://127.0.0.1:8767/>. Stop the foreground server with **Ctrl+C**. The server binds to loopback only. Do not enter sensitive text; requests are sent to the local process.

You can also call the local API:

```sh
curl -s http://127.0.0.1:8767/api/route \
  -H 'content-type: application/json' \
  -d '{"text":"Find the latest filing for Acme and summarize its revenue."}'
```

The response is a recommendation, capability scores, and an abstain status/reason where applicable. The only supported no-LLM task is the bounded `calc:` grammar when the caller enables the trusted calculator handler. All tool execution remains the caller's responsibility.

## Package contents

- `model/`: quantized ONNX model, tokenizer, calibration, policy, and manifest.
- `src/minirouter/`: local serializer, policy, runtime, API, and route contract.
- `web/`: single-page test interface.
- `scripts/serve_preview.py`: loopback FastAPI server.
- `requirements-runtime.txt`: pinned inference and preview dependencies. Training dependencies are separate.

The release model directory is 13,444,659 bytes: the original frozen V3 inference bundle was 13,436,702 bytes, and the release copy adds updated model and license documentation. Python dependencies and runtime memory are outside its 15,000,000-byte cap. The measured benchmark process peak RSS was 152,436,736 bytes.

## License and provenance

MiniRouter code is MIT licensed. The Ettin-derived weights and tokenizer retain their upstream MIT notice. The training corpus includes reviewed/adapted examples from MBPP (Apache-2.0), GSM8K (MIT), and SQL Create Context (CC-BY-4.0), along with internally authored synthetic examples. See [third-party notices](THIRD_PARTY_NOTICES.md). No raw source datasets are included in this release package.
