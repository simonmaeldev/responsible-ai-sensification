# Ossia Native Inference Decision

## Decision

- **Date:** 2026-08-18
- **Execution machine:** Ubuntu GPU PC
- **Outcome:** no-go for a native ONNX/Avendish inference implementation now.
- **Recommended route:** keep the verified FastAPI/PyTorch Gemma, Gemma Scope
  SAE, and Neuronpedia backend connected to ossia score through the existing
  WebSocket device.

This completes Slice 5 as an investigation. It does not authorize an inference
port, add an Avendish bridge, or change the browser, score interface, inference
architecture, `/rai/v1`, OSCQuery, or Windows receiver. No dependencies were
installed, no large model was downloaded, and no source build was created.

## Evaluated Baseline

The installed score is 3.8.2 and carries ONNX Runtime 1.24.1. The investigation
also inspected these upstream source revisions rather than treating the
installed process as the latest implementation:

| Component | Revision inspected |
| --- | --- |
| ossia score | `05abddc9986a8d19d7123d2962568de4b00048ac` |
| score-addon-onnx | `cd1ac8dfc9a19c67ca62fca037df8eca6167c545` |
| Avendish | `bf9b721e5cd543179f827ce1052f2208ca60873b` |
| Cached `google/gemma-3-1b-pt` | `fcf18a2a879aab110ca39f8bffbccd5d49d8eb29` |
| Cached Gemma Scope layer-22 65k SAE | `b738dc06961818c011fb2e44a316352ca0f4e873` |

The current score add-on describes support for decoder families including
Gemma, but its Language Model node boundary exposes response text, token rate,
generation state, and optional partial text. It does not expose token IDs,
hidden states, SAE evidence, or the provenance contract used by this project.
Its internal per-step token ID is decoded to text before reaching a node output.

## Required-Parity Findings

| Requirement | Measured or source-inspected finding | Decision impact |
| --- | --- | --- |
| Exact prompt semantics | The project tokenizer encodes `The future of AI` as `[2, 818, 3402, 529, 12498]`, decoded as `'<bos>The future of AI'`. The cached PT tokenizer has no chat template. The add-on applies a chat template and falls back to Qwen ChatML when none exists. | The two paths do not currently present the same model input. |
| Exact token identity | The add-on exposes decoded strings, not the integer token ID required by token history and provenance. | Interface parity cannot be established. |
| Layer-22 residual | The helper consumes logits and KV-cache outputs; it has no port or graph contract for the exact `resid_post` tensor used by the backend. | The SAE input and dense observation cannot be reproduced. |
| SAE parity | The add-on has no Gemma Scope JumpReLU path. The cached SAE has a 1,152-by-65,536 encoder plus bias and threshold; the backend applies it to the float32 layer-22 residual. | Active feature indices and raw activations cannot be compared. |
| Neuronpedia evidence and provenance | No model revision, token ID, observation site, layer, module path, shape, dtype, representation, or feature-description outputs exist at the node boundary. | The research evidence contract would be lost. |
| Cancellation | The worker callback always continues and the node exposes no cancellation input. Removing the process can discard a result but does not establish termination of an in-flight inference call. | Stop behavior is not equivalent to the current backend. |
| One-token backpressure and live changes | Inputs are snapshotted when a run starts. A worker generates into an unbounded string queue, while the process thread drains queued tokens and emits at most one partial segment per tick. | There is no acknowledgment boundary at which live layer/probe edits can affect the next token. |
| GPU runtime | The installed add-on's ONNX Runtime CUDA provider requires CUDA 13 libraries that are not available to the host loader. The host has CUDA 12.3, while PyTorch uses its bundled CUDA 12.8 runtime. | The immediately usable ONNX path is CPU fallback, not a comparable GPU path. |
| Build readiness | Current score-addon-onnx requires CMake 3.24 and C++23; the host has CMake 3.22.1 and GCC 11.4, with no score SDK found. Its build also fetches ONNX Runtime, ONNX Runtime Extensions, Avendish, and other dependencies. | A native trial first requires a separately approved toolchain, dependency, and build task. |
| Exact export | No ONNX export of the cached PT checkpoint is present. The available ONNX Community Gemma 3 1B artifact inspected is the instruction-tuned model, not `google/gemma-3-1b-pt`. | A like-for-like native benchmark is not yet possible. |

## Measured Backend Reference

A real local-cache RTX 4060 Ti run used the current project path with the prompt
`The future of AI`, four greedy tokens, the layer-22 residual, and the matching
65k SAE:

| Token | ID | Text | Step time | Active SAE features |
| ---: | ---: | --- | ---: | ---: |
| 1 | 563 | `' is'` | 365 ms, including warm-up | 54 |
| 2 | 1590 | `' here'` | 37 ms | 65 |
| 3 | 236761 | `'.'` | 37 ms | 54 |
| 4 | 108 | `'\n\n'` | 37 ms | 42 |

Model loading took 3.297 seconds and SAE loading took 0.098 seconds. Mean
generation including warm-up was 8.403 tokens/second; the last three steps were
about 27.0 tokens/second. PyTorch reported 2,500 MiB peak allocated and 2,518
MiB peak reserved GPU memory. These figures are a reproducible backend
reference, not a claim that native ONNX is slower: no equivalent native graph
could be run without changing the environment and first producing the exact
export described above.

## Options Considered

1. **Keep the backend — selected.** It already preserves exact PT tokenization,
   greedy token IDs, layer-22 residuals, raw SAE indices/activations,
   Neuronpedia evidence, cancellation, one-token backpressure, live probe edits,
   and full provenance. Slices 1–4 prove the score interface can control and
   patch this path without changing it.
2. **Add an Avendish bridge — not selected.** A bridge would duplicate the
   working WebSocket adapter while leaving inference and evidence generation in
   the external backend. No measured reliability, latency, or research benefit
   currently offsets that extra interface and maintenance surface.
3. **Write a native ONNX process — no-go now.** Current add-on ports and runtime
   behavior do not meet the research contract, and the machine lacks a
   compatible GPU-provider/build baseline for a fair prototype.

## Gate To Reopen Native Work

Reopen this decision only for a concrete measured need and a newly approved
spec. That task must first:

1. Produce and pin an exact `google/gemma-3-1b-pt` decoder-with-past export that
   also exposes the named layer-22 `resid_post` tensor.
2. Prove plain-prompt input IDs and each generated token ID against the pinned
   Hugging Face tokenizer and greedy PyTorch path.
3. Define native ports for raw token ID/text and every required model, token,
   site, layer, module-path, shape, dtype, and representation provenance field.
4. Implement the exact cached JumpReLU encoder equation and compare feature
   indices and activation values under an explicitly approved numeric tolerance.
5. Preserve Neuronpedia lookup as evidence rather than model state.
6. Demonstrate prompt cancellation that terminates in-flight work, bounded
   one-token delivery with acknowledgment, and live controls that affect the
   expected subsequent token.
7. Establish an approved compatible GPU runtime, either by rebuilding against
   the host CUDA line or by a separately approved CUDA/toolchain update.
8. Build as an isolated add-on against the matching continuous score SDK and
   compare the same prompt, token sequence, memory use, and steady-state timing
   with the backend reference.

Until those gates are met, there is no native implementation spec and no Phase
6. The durable interface decision remains: score is the visible research and
patching environment; the verified Python backend owns inference and evidence.

## Primary Upstream References

- [ossia score revision](https://github.com/ossia/score/tree/05abddc9986a8d19d7123d2962568de4b00048ac)
- [score-addon-onnx revision](https://github.com/ossia/score-addon-onnx/tree/cd1ac8dfc9a19c67ca62fca037df8eca6167c545)
- [Avendish revision](https://github.com/celtera/avendish/tree/bf9b721e5cd543179f827ce1052f2208ca60873b)
- [Optimum ONNX Gemma3-Text support](https://github.com/huggingface/optimum-onnx/releases/tag/v0.1.0)
- [Optimum ONNX export guide](https://huggingface.co/docs/optimum-onnx/en/onnx/usage_guides/export_a_model)
- [ONNX Community Gemma 3 1B IT artifact](https://huggingface.co/onnx-community/gemma-3-1b-it-ONNX)
