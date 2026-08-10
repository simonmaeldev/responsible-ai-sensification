# responsible-ai-sensification

Sensification of the output of Gemma 3 — turns SAE feature activations into live generative audio via a browser UI.

Current project direction: this sensification work is being done with Professor Tegan Maharaj.

> **Requires a HuggingFace login** and acceptance of the [Gemma 3 license](https://huggingface.co/google/gemma-3-1b-pt) before first use.

## Quick Start (Web UI)

```bash
# Install system dependency for audio (only needed for CLI --live flag)
sudo apt install libportaudio2

# Start the server and open the Emitter in the default browser
./scripts/start.sh
```

The launcher waits for the server, then opens `http://127.0.0.1:8080`. For a
headless or remote session, use `./scripts/start.sh --no-browser` and open that
address manually.

```bash
# Stop the server
./scripts/stop.sh
```

The browser UI is the primary interface. Enter a prompt and click **Run prompt**.
The live surface keeps the exact current token, selectable token history, all
Gemma blocks, and the strongest active SAE/Neuronpedia directions together.
Open **Setup** for model, observation, sound, signal, and mapping controls;
optional Tonality and OSC remain separate. Live parameters affect subsequent
tokens without restarting.

Passive external-observer tooling is available for TouchDesigner and other
WebSocket clients. The server can mirror complete sparse activation events at
`/ws/activations`, and deterministic fixture replay supports host-side work
without loading the model. This rich observer feed is separate from the
optional, browser-configured `/rai/v1` OSC output used by the existing Max for
Live receiver. See `integrations/README.md`.

### External integration quick loop

```bash
# Terminal 1: server
./scripts/integration-dev.sh serve

# Terminal 2: replay passive WebSocket fixtures without loading Gemma/SAE
./scripts/integration-dev.sh replay 250 true

# Observer-contract and starter-asset checks
./scripts/integration-dev.sh check

# Exercise the established OSC v1 receiver separately
./scripts/integration-dev.sh osc-fixture 127.0.0.1 9000
```

### Parameters

| Parameter | Default | Description |
|---|---|---|
| **Prompt** | `Hello world` | Text prompt fed to the model |
| **Model** | `google/gemma-3-1b-pt` | HuggingFace model (`gemma-3-1b-pt` or `gemma-3-4b-pt`) |
| **Layer** | `22` | Transformer layer index to hook SAE onto |
| **Width** | `65k` | SAE width |
| **Strategy** | `identity` | `identity`: maps each feature directly to a frequency; `cluster`: groups features by semantic similarity (k-means on Neuronpedia embeddings) |
| **Clusters** | `8` | Number of k-means clusters (cluster strategy only) |
| **Mode** | `timed` | `timed`: notes play for a fixed BPM-derived duration; `sustain`: notes hold until the next token arrives |
| **BPM** | `120` | Tempo for timed mode |
| **Loop** | off | Replay generated tokens indefinitely after generation ends |

### Verbose logging

```bash
./scripts/start.sh --verbose
# or
VERBOSE=1 ./scripts/start.sh
```

---

## Prerequisites

```bash
sudo apt install libportaudio2   # required for CLI --live playback only
```

## Directory Layout

```
app/
  client/          # Vanilla-JS browser frontend
    index.html
    style.css
    main.js
  server/
    main.py        # FastAPI app factory
    session.py     # PipelineParams + PipelineSession
    pipeline/
      extract.py
      transform.py
      synthesize.py
      audio_utils.py
      export.py
    routers/
      config.py    # GET /api/config/defaults, GET /api/config/model-options
      stream.py    # WS /ws/stream
scripts/
  start.sh         # Start uvicorn and open the browser on port 8080
  stop.sh          # Kill uvicorn on port 8080
  integration-dev.sh # Serve/replay/check passive external observers
integrations/
  fixtures/        # Deterministic raw activation events
  ossia-score/     # Current OSC v1 monitoring notes and future scope
  touchdesigner/   # Passive WebSocket callbacks and receiver setup
specs/             # Feature specs + TODO backlog
```

---

## CLI Tools

The pipeline can also be used directly from the command line.

### extract.py

Loads a model + SAE + Neuronpedia explanations, generates tokens autoregressively, and writes a JSON file with per-token SAE feature activations.

```
uv run python app/server/pipeline/extract.py PROMPT [--model MODEL] [--layer LAYER] [--width WIDTH]
                                [--l0 L0] [--max-tokens N] [--output PATH] [--verbose]
                                [--stream] [--loop]
```

| Flag | Default | Description |
|---|---|---|
| `prompt` | *(required)* | Prompt string |
| `--model` | `google/gemma-3-1b-pt` | HuggingFace model ID |
| `--layer` | `22` | Transformer layer index |
| `--width` | `65k` | SAE width |
| `--l0` | `medium` | SAE L0 target |
| `--max-tokens` | `200` | Maximum new tokens |
| `--output` | `runs/analysis.json` | Output JSON path |
| `--verbose` | off | Print progress to stderr |
| `--stream` | off | Emit one NDJSON line per token to stdout (meta header first) |
| `--loop` | off | Replay recorded tokens indefinitely after generation (Ctrl+C to stop) |

### synthesize.py

Reads a `GenerationAnalysis` JSON and renders a WAV file, or plays live audio from a `MusicalEvent` NDJSON stream.

```
uv run python app/server/pipeline/synthesize.py [INPUT] [--method METHOD] [--output-dir DIR]
                             [--live] [--mode timed|sustain]
```

| Flag | Default | Description |
|---|---|---|
| `input` | *(required in batch mode)* | Path to JSON produced by `extract.py` |
| `--method` | `additive` | Synthesis method (`additive`) |
| `--output-dir` | `audio` | Output directory |
| `--live` | off | Play audio live from NDJSON stdin |
| `--mode` | `timed` | Live mode: `timed` (0.5 s/token) or `sustain` (hold until next token) |

### transform.py

Transforms a `TokenStream` NDJSON (from `extract.py --stream`) into a `MusicalEvent` NDJSON stream with frequency/amplitude/instrument assignments.

```
uv run python app/server/pipeline/transform.py [INPUT] [--strategy identity|cluster] [--clusters N] [--embed-model MODEL]
```

| Flag | Default | Description |
|---|---|---|
| `input` | *(stdin if omitted)* | Batch JSON file or omit to read NDJSON from stdin |
| `--strategy` | `identity` | `identity`: direct feature→freq; `cluster`: semantic clustering |
| `--clusters` | `8` | Number of k-means clusters (cluster strategy) |
| `--embed-model` | `all-MiniLM-L6-v2` | Sentence transformer model for embeddings |

### Basic pipeline

```bash
uv run python app/server/pipeline/extract.py "The law of conservation of energy" --layer 22 --width 65k --verbose
uv run python app/server/pipeline/synthesize.py runs/analysis.json --method additive
```

### Streaming live pipeline

```bash
# Identity strategy, timed mode (0.5 s per token):
uv run python app/server/pipeline/extract.py "hello world" --stream --max-tokens 20 \
  | uv run python app/server/pipeline/transform.py --strategy identity \
  | uv run python app/server/pipeline/synthesize.py --live --mode timed

# Cluster strategy, sustain mode (each note holds until next token arrives):
uv run python app/server/pipeline/extract.py "hello world" --stream --max-tokens 20 \
  | uv run python app/server/pipeline/transform.py --strategy cluster --clusters 8 \
  | uv run python app/server/pipeline/synthesize.py --live --mode sustain

# Loop mode — replay the generation indefinitely (Ctrl+C to stop):
uv run python app/server/pipeline/extract.py "hello world" --stream --loop --max-tokens 20 \
  | uv run python app/server/pipeline/transform.py --strategy identity \
  | uv run python app/server/pipeline/synthesize.py --live --mode timed

# Build cluster map first from a batch JSON, then stream it live:
uv run python app/server/pipeline/transform.py runs/analysis.json --strategy cluster --clusters 8 \
  | uv run python app/server/pipeline/synthesize.py --live --mode timed
```

---

Source: https://colab.research.google.com/drive/1NhWjg7n0nhfW--CjtsOdw5A5J_-Bzn4r#scrollTo=nOBcV4om7mrT
