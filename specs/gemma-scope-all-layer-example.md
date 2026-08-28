# Gemma Scope 2 All-Layer Example

## Machine And Scope

- **Execution machine:** Ubuntu GPU PC.
- **Emitter model:** official pretrained `google/gemma-3-270m`.
- **SAE source:** official pretrained `google/gemma-scope-2-270m-pt`.
- **SAE family:** `resid_post_all`, width `16k`, target L0 `small`.
- **Covered layers:** every Gemma 3 270M decoder block, 0 through 17.

This is a complete small-model example of moving sparse observation across the
model. It uses a distinct SAE trained for each layer; it never applies one
layer's SAE to another layer's activations.

## Required Behavior

1. The model catalogue exposes Gemma 3 270M, its real 18-block architecture,
   and all 18 matching SAE layers.
2. The browser lets a user move both the dense observation and the SAE
   observation across the block map. A live SAE-layer change affects the next
   generated token without restarting the run.
3. The backend resolves the exact layer-specific SAE before each forward pass,
   captures the matching post-block residual, and reports the actual SAE layer,
   category, width, L0 target, repository, revision, module path, shape, dtype,
   and representation with the token.
4. The score interface can start the 270M example, change its requested SAE
   layer during generation, and continue receiving synchronized token history,
   probes, and unchanged patchable scalar values.
5. The current 1B/4B choices and all existing browser, score, connector, and
   receiver behavior remain compatible.

## Interpretation Boundary

- Feature indices belong to a specific model, site, layer, SAE family, width,
  L0 target, and revision. The same integer at two layers is not the same
  feature and is not a cross-layer semantic trajectory.
- The `resid_post_all` 16k series is used because it covers every layer. It is
  distinct from the richer four-layer `resid_post` series currently indexed by
  Neuronpedia. Missing descriptions must remain visibly unavailable; the app
  must not borrow descriptions, clusters, or semantic labels from another SAE.
- Browser sound and visual mappings remain optional transformations of the
  selected layer's raw observations. They do not alter or relabel the source.

## Loading And Caching

- Download only official model and SAE artifacts authorized by the user.
- Keep generated caches and weights out of Git.
- Cache layer-specific SAE runtimes by the complete model/repository/category/
  layer/width/L0 identity. A first visit may pause to load a local weight file;
  revisiting that layer reuses the runtime cache.
- Pre-cache all 18 official weight files for the completed GPU acceptance run
  so layer movement is not measuring network delay.

## Non-Goals

- Training or modifying an SAE.
- Treating feature indices as comparable across layers.
- Adding Q/K/V, individual-head, gradient, or arbitrary-hook support.
- Expanding `/rai/v1`, OSCQuery, the Windows receiver, or raw-vector transport.
- Moving inference into ossia score or implementing the rejected native ONNX
  route.

## Test-First Acceptance

1. Failing catalogue and loader tests prove all 18 exact pretrained SAE paths
   are advertised and selected.
2. A failing generation test proves a live layer change uses two distinct SAE
   runtimes, residuals, descriptions, and provenance on consecutive tokens.
3. Browser tests prove selecting an SAE layer emits a live `update_params`
   message and does not conflate dense and sparse layer selection.
4. Score adapter/QML/document tests prove model selection, live requested SAE
   layer, synchronized history, and existing scalar patchability.
5. Run complete server, browser, adapter, QML/document, normal/debug installed-
   score, and example-removal checks.
6. Run a real cached GPU generation that visits at least layers 0, 8, and 17 on
   consecutive tokens. Compare every emitted layer/module/shape/value field
   with the browser WebSocket event and confirm the matching official SAE is
   used at each layer.

## Completion Record

Completed on the Ubuntu GPU PC on 2026-08-28. The cached official model snapshot
is `9b0cfec892e2bc2afd938c98eabe4e4a7b1e0ca1`; the 18 SAE files resolve to
official snapshot `b218cd5d69dc2fa71cff448b68d625e6c9702d49`.

The real RTX 4060 Ti acceptance generated tokens `" of"`, `" a"`, and
`" glass"` at requested layers 0, 8, and 17. The corresponding events used
`gemma_scope.resid_post_all.layer_{0,8,17}.width_16k`, shapes `[16384]`, empty
descriptions, and the same exact SAE snapshot. Tensor RMS values
`3.6739234924316406`, `205.93753051757812`, and `1512.407958984375`, plus each
SAE top activation/index, were identical between backend probe fields,
patchable score values, and synchronized token history. The normal Float
example received the exact final RMS. Existing normal/debug/removal and real 1B
regression checks also passed; no connector, receiver, or native-inference path
changed.
