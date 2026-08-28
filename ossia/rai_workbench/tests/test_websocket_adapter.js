const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const workbenchDir = path.resolve(__dirname, "..");

function loadAdapter() {
  const source = fs.readFileSync(
    path.join(workbenchDir, "websocket-adapter.js"),
    "utf8",
  );
  const context = vm.createContext({});
  vm.runInContext(source, context, { filename: "websocket-adapter.js" });
  return context;
}

function valuesByAddress(result) {
  return Object.fromEntries(
    Array.from(result.updates, (update) => [update.address, update.value]),
  );
}

test("start and stop controls produce backend-compatible requests", () => {
  const adapter = loadAdapter();
  const probeRack = [
    {
      id: "residual",
      site: "residual_post",
      layer: 7,
      capture: "summary",
      enabled: true,
      publish: true,
    },
  ];
  const start = JSON.parse(
    adapter.startMessage(
      "A glass bell in winter",
      7,
      7,
      probeRack,
      "google/gemma-3-270m",
      8,
      "16k",
      "small",
    ),
  );

  assert.equal(start.action, "start");
  assert.equal(start.params.prompt, "A glass bell in winter");
  assert.equal(start.params.max_tokens, 7);
  assert.deepEqual(Array.from(start.params.emitter_signal_keys), [
    "model.layer_profile",
    "model.residual.vector",
    "sae.active_features",
  ]);
  assert.equal(start.params.observation_layer, 7);
  assert.equal(start.params.model, "google/gemma-3-270m");
  assert.equal(start.params.layer, 8);
  assert.equal(start.params.width, "16k");
  assert.equal(start.params.l0, "small");
  assert.deepEqual(JSON.parse(JSON.stringify(start.params.probe_rack)), probeRack);
  assert.deepEqual(
    JSON.parse(adapter.updateParamsMessage({ observation_layer: 12 })),
    { action: "update_params", params: { observation_layer: 12 } },
  );
  assert.deepEqual(JSON.parse(adapter.stopMessage()), { action: "stop" });
  assert.deepEqual(JSON.parse(adapter.saeLayerMessage(17)), {
    action: "update_params",
    params: { layer: 17 },
  });
});

test("connection and ready events initialize the fixed workbench state", () => {
  const adapter = loadAdapter();
  const connected = Object.fromEntries(
    Array.from(adapter.connectedUpdates(), (update) => [
      update.address,
      update.value,
    ]),
  );
  assert.equal(connected["/connection/state"], "connected");
  assert.equal(connected["/run/state"], "idle");

  const result = adapter.decodeEvent(
    JSON.stringify({
      type: "ready",
      params: {
        prompt: "Ready prompt",
        model: "google/gemma-3-1b-it",
        observation_layer: 17,
        layer: 8,
        width: "16k",
        l0: "small",
        max_tokens: 200,
        probe_rack: [
          {
            id: "residual",
            site: "residual_post",
            layer: 17,
            capture: "summary",
            enabled: true,
            publish: false,
          },
        ],
      },
    }),
    99,
  );
  const values = valuesByAddress(result);

  assert.equal(result.tokenIndex, -1);
  assert.equal(result.prompt, "Ready prompt");
  assert.equal(values["/connection/state"], "ready");
  assert.equal(values["/run/state"], "idle");
  assert.equal(values["/run/prompt"], "Ready prompt");
  assert.equal(values["/run/max_tokens"], 200);
  assert.equal(values["/run/model"], "google/gemma-3-1b-it");
  assert.equal(values["/run/sae_width"], "16k");
  assert.equal(values["/run/sae_l0"], "small");
  assert.equal(values["/model/name"], "google/gemma-3-1b-it");
  assert.equal(values["/observation/layer"], 17);
  assert.equal(values["/observation/sae_layer"], 8);
  assert.equal(values["/observation/requested_sae_layer"], 8);
  assert.equal(values["/observation/requested_layer"], undefined);
  assert.equal(values["/probe_controls/1/id"], undefined);
});

test("runtime model structure becomes a fixed truthful Gemma block map", () => {
  const adapter = loadAdapter();
  const layerTypes = Array.from(
    { length: 26 },
    (_value, index) => ((index + 1) % 6 === 0 ? "full_attention" : "sliding_attention"),
  );
  const values = valuesByAddress(
    adapter.decodeEvent(
      {
        type: "model_structure",
        model: "google/gemma-3-1b-pt",
        architecture: {
          model_type: "gemma3_text",
          layer_count: 26,
          hidden_size: 1152,
          intermediate_size: 6912,
          attention_heads: 4,
          key_value_heads: 1,
          head_dim: 256,
          sliding_window: 512,
          max_position_embeddings: 32768,
          layer_types: layerTypes,
        },
      },
      -1,
    ),
  );

  assert.equal(values["/model/name"], "google/gemma-3-1b-pt");
  assert.equal(values["/model/type"], "gemma3_text");
  assert.equal(values["/model/layer_count"], 26);
  assert.equal(values["/model/hidden_size"], 1152);
  assert.equal(values["/model/intermediate_size"], 6912);
  assert.equal(values["/model/attention_heads"], 4);
  assert.equal(values["/model/key_value_heads"], 1);
  assert.equal(values["/model/head_dim"], 256);
  assert.equal(values["/model/sliding_window"], 512);
  assert.equal(values["/model/max_position_embeddings"], 32768);
  assert.equal(values["/blocks/1/enabled"], true);
  assert.equal(values["/blocks/1/attention_type"], "sliding_attention");
  assert.equal(values["/blocks/6/attention_type"], "full_attention");
  assert.equal(values["/blocks/26/enabled"], true);
  assert.equal(values["/blocks/27/enabled"], false);
});

test("structured loading events remain structured in score", () => {
  const adapter = loadAdapter();
  const result = adapter.decodeEvent(
    {
      type: "loading",
      label: "Loading SAE",
      detail: "Loading parameters",
      progress: 0.375,
    },
    -1,
  );
  const values = valuesByAddress(result);

  assert.equal(values["/run/state"], "loading");
  assert.equal(values["/loading/label"], "Loading SAE");
  assert.equal(values["/loading/detail"], "Loading parameters");
  assert.equal(values["/loading/progress"], 0.375);
});

test("token events expose bounded probes and strongest SAE features", () => {
  const adapter = loadAdapter();
  const result = adapter.decodeEvent(
    {
      type: "token",
      token: " bell",
      token_id: 420,
      elapsed_ms: 12.5,
      observation: {
        model: "google/gemma-3-1b-it",
        site: "residual_post",
        layer: 17,
        module_path: "model.language_model.layers.17",
        shape: [1152],
        dtype: "float32",
        representation: "dense_residual",
        sae_layer: 22,
        sae_module_path: "gemma_scope.resid_post.layer_22.width_65k",
        sae_shape: [65000],
        sae_dtype: "sparse_float32",
        sae_representation: "sparse_sae",
        sae_width: "16k",
        sae_l0: "small",
        sae_category: "resid_post_all",
        sae_repo_id: "google/gemma-scope-2-270m-pt",
        sae_revision: "2109a1868ae2a3b699123d290e8944cfd43d8ed1",
      },
      probes: [
        {
          id: "residual-17",
          site: "residual",
          layer: 17,
          module_path: "model.language_model.layers.17",
          capture: "output",
          publish: "summary",
          shape: [1, 1, 1152],
          token_index: 4,
          model: "google/gemma-3-1b-it",
          dtype: "float32",
          summary: {
            rms: 0.75,
            max_abs: 2.5,
            mean: -0.125,
            active_count: 6,
            top_index: 91,
            top_activation: 3.25,
          },
        },
      ],
      emitter: {
        streams: {
          "sae.active_features": {
            value: [
              { index: 8, activation: 0.5, description: "glass" },
              { index: 3, activation: 2.25, description: "bells" },
            ],
          },
          "model.layer_profile": {
            value: {
              layers: [
                {
                  layer: 0,
                  rms: 0.25,
                  max_abs: 0.75,
                  delta_rms: null,
                  cosine_to_previous: null,
                },
                {
                  layer: 1,
                  rms: 0.5,
                  max_abs: 1.25,
                  delta_rms: 0.125,
                  cosine_to_previous: 0.875,
                },
              ],
            },
          },
        },
      },
    },
    2,
  );
  const values = valuesByAddress(result);

  assert.equal(result.tokenIndex, 4);
  assert.equal(values["/run/state"], "running");
  assert.equal(values["/token/index"], 4);
  assert.equal(values["/token/id"], 420);
  assert.equal(values["/token/text"], " bell");
  assert.equal(values["/token/elapsed_ms"], 12.5);
  assert.equal(values["/model/name"], "google/gemma-3-1b-it");
  assert.equal(values["/observation/layer"], 17);
  assert.equal(values["/observation/sae_layer"], 22);
  assert.equal(values["/observation/site"], "residual_post");
  assert.equal(values["/observation/module_path"], "model.language_model.layers.17");
  assert.equal(values["/observation/shape"], "[1152]");
  assert.equal(values["/observation/dtype"], "float32");
  assert.equal(values["/observation/representation"], "dense_residual");
  assert.equal(values["/observation/sae_module_path"], "gemma_scope.resid_post.layer_22.width_65k");
  assert.equal(values["/observation/sae_shape"], "[65000]");
  assert.equal(values["/observation/sae_dtype"], "sparse_float32");
  assert.equal(values["/observation/sae_representation"], "sparse_sae");
  assert.equal(values["/observation/sae_width"], "16k");
  assert.equal(values["/observation/sae_l0"], "small");
  assert.equal(values["/observation/sae_category"], "resid_post_all");
  assert.equal(values["/observation/sae_repo_id"], "google/gemma-scope-2-270m-pt");
  assert.equal(
    values["/observation/sae_revision"],
    "2109a1868ae2a3b699123d290e8944cfd43d8ed1",
  );

  assert.equal(values["/probes/1/enabled"], true);
  assert.equal(values["/probes/1/id"], "residual-17");
  assert.equal(values["/probes/1/model"], "google/gemma-3-1b-it");
  assert.equal(values["/probes/1/token_index"], 4);
  assert.equal(values["/probes/1/dtype"], "float32");
  assert.equal(values["/probes/1/representation"], "dense_tensor_summary");
  assert.equal(values["/probes/1/shape"], "[1,1,1152]");
  assert.equal(values["/probes/1/rms"], 0.75);
  assert.equal(values["/probes/1/top_index"], 91);
  assert.equal(values["/probes/2/enabled"], false);
  assert.equal(values["/probes/2/id"], "");

  assert.equal(values["/features/1/index"], 3);
  assert.equal(values["/features/1/activation"], 2.25);
  assert.equal(values["/features/1/description"], "bells");
  assert.equal(values["/features/2/index"], 8);
  assert.equal(values["/features/3/index"], -1);
  assert.equal(values["/features/3/activation"], 0);
  assert.equal(values["/features/3/description"], "");
  assert.equal(values["/blocks/1/profile_valid"], true);
  assert.equal(values["/blocks/1/rms"], 0.25);
  assert.equal(values["/blocks/1/has_previous"], false);
  assert.equal(values["/blocks/2/delta_rms"], 0.125);
  assert.equal(values["/blocks/2/cosine_to_previous"], 0.875);
  assert.equal(values["/blocks/3/profile_valid"], false);
  assert.equal(values["/token/revision"], 4);
  assert.equal(result.updates.at(-1).address, "/token/revision");
});

test("four patchable scalars preserve backend values and complete provenance", () => {
  const adapter = loadAdapter();
  const tensorSummary = {
    rms: 10.5,
    max_abs: 11.5,
    mean: 9.875,
  };
  const saeSummary = {
    active_count: 37,
    max_activation: 3.5,
    total_activation: 8.25,
    top_index: 8123,
    top_activation: 3.5,
  };
  const result = adapter.decodeEvent(
    {
      type: "token",
      token: " glass",
      token_id: 421,
      elapsed_ms: 12.0,
      probes: [
        {
          id: "attention-l7",
          model: "google/gemma-3-1b-pt",
          token_index: 2,
          site: "attention_output",
          layer: 7,
          module_path: "model.layers.7.self_attn",
          capture: "summary",
          publish: true,
          shape: [1152],
          dtype: "float32",
          summary: tensorSummary,
        },
        {
          id: "sae",
          model: "google/gemma-3-1b-pt",
          token_index: 2,
          site: "sae",
          layer: 22,
          module_path: "gemma_scope.resid_post.layer_22.width_65k",
          capture: "summary",
          publish: true,
          shape: [65536],
          dtype: "sparse_float32",
          summary: saeSummary,
        },
      ],
    },
    1,
  );
  const values = valuesByAddress(result);

  const expected = {
    tensor_rms: {
      value: tensorSummary.rms,
      metric: "summary.rms",
      probe_id: "attention-l7",
      source_slot: 1,
      feature_index: -1,
      site: "attention_output",
      layer: 7,
      module_path: "model.layers.7.self_attn",
      shape: "[1152]",
      dtype: "float32",
      representation: "dense_tensor_summary",
    },
    tensor_max_abs: {
      value: tensorSummary.max_abs,
      metric: "summary.max_abs",
      probe_id: "attention-l7",
      source_slot: 1,
      feature_index: -1,
      site: "attention_output",
      layer: 7,
      module_path: "model.layers.7.self_attn",
      shape: "[1152]",
      dtype: "float32",
      representation: "dense_tensor_summary",
    },
    sae_active_count: {
      value: saeSummary.active_count,
      metric: "summary.active_count",
      probe_id: "sae",
      source_slot: 2,
      feature_index: -1,
      site: "sae",
      layer: 22,
      module_path: "gemma_scope.resid_post.layer_22.width_65k",
      shape: "[65536]",
      dtype: "sparse_float32",
      representation: "sparse_sae_summary",
    },
    sae_top_activation: {
      value: saeSummary.top_activation,
      metric: "summary.top_activation",
      probe_id: "sae",
      source_slot: 2,
      feature_index: saeSummary.top_index,
      site: "sae",
      layer: 22,
      module_path: "gemma_scope.resid_post.layer_22.width_65k",
      shape: "[65536]",
      dtype: "sparse_float32",
      representation: "sparse_sae_summary",
    },
  };

  for (const [key, scalar] of Object.entries(expected)) {
    const prefix = `/patchable/${key}`;
    assert.equal(values[`${prefix}/valid`], true);
    assert.equal(values[`${prefix}/value`], scalar.value);
    assert.equal(values[`${prefix}/metric`], scalar.metric);
    assert.equal(values[`${prefix}/probe_id`], scalar.probe_id);
    assert.equal(values[`${prefix}/source_slot`], scalar.source_slot);
    assert.equal(values[`${prefix}/model`], "google/gemma-3-1b-pt");
    assert.equal(values[`${prefix}/token_index`], 2);
    assert.equal(values[`${prefix}/token_id`], 421);
    assert.equal(values[`${prefix}/token_text`], " glass");
    assert.equal(values[`${prefix}/site`], scalar.site);
    assert.equal(values[`${prefix}/layer`], scalar.layer);
    assert.equal(values[`${prefix}/module_path`], scalar.module_path);
    assert.equal(values[`${prefix}/shape`], scalar.shape);
    assert.equal(values[`${prefix}/dtype`], scalar.dtype);
    assert.equal(values[`${prefix}/representation`], scalar.representation);
    assert.equal(values[`${prefix}/feature_index`], scalar.feature_index);
  }

  assert.equal(values["/patchable/tensor_rms/value"], tensorSummary.rms);
  assert.equal(values["/patchable/tensor_max_abs/value"], tensorSummary.max_abs);
  assert.equal(values["/patchable/sae_active_count/value"], saeSummary.active_count);
  assert.equal(values["/patchable/sae_top_activation/value"], saeSummary.top_activation);
  assert.equal(result.updates.at(-1).address, "/token/revision");
  assert.equal(
    result.updates.some((update) => /patchable.*(?:vector|features)/.test(update.address)),
    false,
  );
});

test("patchable scalars follow subsequent probes and invalidate absent sources", () => {
  const adapter = loadAdapter();
  const second = valuesByAddress(
    adapter.decodeEvent(
      {
        type: "token",
        token: " next",
        token_id: 502,
        probes: [
          {
            id: "mlp-l3",
            model: "google/gemma-3-1b-pt",
            token_index: 6,
            site: "mlp_output",
            layer: 3,
            module_path: "model.layers.3.mlp",
            capture: "summary",
            shape: [1152],
            dtype: "float32",
            summary: { rms: 4.25, max_abs: 9.5, mean: -0.25 },
          },
        ],
      },
      5,
    ),
  );

  assert.equal(second["/patchable/tensor_rms/value"], 4.25);
  assert.equal(second["/patchable/tensor_rms/layer"], 3);
  assert.equal(second["/patchable/tensor_rms/site"], "mlp_output");
  assert.equal(second["/patchable/tensor_rms/module_path"], "model.layers.3.mlp");
  assert.equal(second["/patchable/tensor_rms/token_index"], 6);
  assert.equal(second["/patchable/sae_active_count/valid"], false);
  assert.equal(second["/patchable/sae_active_count/value"], 0);
  assert.equal(second["/patchable/sae_active_count/model"], "");
  assert.equal(second["/patchable/sae_top_activation/valid"], false);
  assert.equal(second["/patchable/sae_top_activation/feature_index"], -1);
});

test("token index falls back to a local counter when no probe index exists", () => {
  const adapter = loadAdapter();
  const result = adapter.decodeEvent(
    { type: "token", token: "x", token_id: 1, probes: [] },
    6,
  );

  assert.equal(result.tokenIndex, 7);
  assert.equal(valuesByAddress(result)["/token/index"], 7);
});

test("terminal and malformed events become explicit run states", () => {
  const adapter = loadAdapter();

  assert.equal(
    valuesByAddress(adapter.decodeEvent({ type: "done" }, 4))["/run/state"],
    "done",
  );
  assert.equal(
    valuesByAddress(adapter.decodeEvent({ type: "stopped" }, 4))["/run/state"],
    "stopped",
  );

  const backendError = valuesByAddress(
    adapter.decodeEvent({ type: "error", message: "CUDA failed" }, 4),
  );
  assert.equal(backendError["/run/state"], "error");
  assert.equal(backendError["/run/error"], "CUDA failed");

  const malformed = valuesByAddress(adapter.decodeEvent("not json", 4));
  assert.equal(malformed["/run/state"], "error");
  assert.match(malformed["/run/error"], /Invalid server message/);
});

test("the score QML device exposes the fixed Phase 1 tree", () => {
  const adapter = fs.readFileSync(
    path.join(workbenchDir, "websocket-adapter.js"),
    "utf8",
  );
  const qml = fs.readFileSync(
    path.join(workbenchDir, "websocket-device.qml"),
    "utf8",
  );

  assert.match(qml, /Ossia\.WebSockets/);
  assert.match(qml, /ws:\/\/127\.0\.0\.1:8080\/ws\/stream/);
  assert.match(qml, /function onDisonnected\s*\(/);
  assert.match(qml, /function onMessage\s*\(/);
  assert.match(qml, /function createTree\s*\(/);
  const embeddedAdapter = qml.match(
    /\/\/ BEGIN GENERATED ADAPTER\n([\s\S]*?)\/\/ END GENERATED ADAPTER/,
  );
  assert.ok(embeddedAdapter, "QML must embed the adapter because score stores it as text");
  assert.equal(embeddedAdapter[1].trim(), adapter.trim());
  assert.doesNotMatch(
    embeddedAdapter[1],
    /^var\s/m,
    "adapter state must use declarations that are valid inside a QML object",
  );
  for (const node of [
    "connection",
    "run",
    "loading",
    "token",
    "model",
    "observation",
    "blocks",
    "probe_controls",
    "probes",
    "features",
    "patchable",
  ]) {
    assert.match(qml, new RegExp(`name: "${node}"`));
  }
  assert.match(qml, /function patchableScalarNodes\s*\(/);
  assert.match(qml, /name: "tensor_rms"/);
  assert.match(qml, /name: "tensor_max_abs"/);
  assert.match(qml, /name: "sae_active_count"/);
  assert.match(qml, /name: "sae_top_activation"/);
  assert.doesNotMatch(qml, /name: "example"/);
  assert.doesNotMatch(qml, /name: "(?:vector|features)",\s*type:/);
});

test("prompt edits stay local and start reads the local score value", () => {
  const qml = fs.readFileSync(
    path.join(workbenchDir, "websocket-device.qml"),
    "utf8",
  );
  const promptBlock = qml.match(
    /name: "prompt"([\s\S]*?)name: "start"/,
  );

  assert.ok(promptBlock);
  assert.doesNotMatch(promptBlock[1], /request:/);
  assert.match(qml, /Device\.read\("\/run\/prompt"\)/);
  assert.match(qml, /Device\.read\("\/run\/max_tokens"\)/);
  assert.match(qml, /Device\.read\("\/run\/model"\)/);
  assert.match(qml, /Device\.read\("\/run\/sae_width"\)/);
  assert.match(qml, /Device\.read\("\/run\/sae_l0"\)/);
  assert.match(qml, /Device\.read\("\/observation\/requested_layer"\)/);
  assert.match(qml, /Device\.read\("\/observation\/requested_sae_layer"\)/);
  assert.match(qml, /function probeRackFromDevice\s*\(/);
  assert.match(qml, /updateParamsMessage/);
  assert.match(qml, /name: "max_tokens",\s*type: Ossia\.Type\.Int/);
  assert.match(qml, /name: "model",\s*type: Ossia\.Type\.String/);
  assert.match(qml, /name: "sae_width",\s*type: Ossia\.Type\.String/);
  assert.match(qml, /name: "sae_l0",\s*type: Ossia\.Type\.String/);
  assert.match(qml, /name: "requested_sae_layer",\s*type: Ossia\.Type\.Int/);
  assert.match(
    qml,
    /name: "start",\s*type: Ossia\.Type\.Bool/,
  );
  assert.match(
    qml,
    /name: "stop",\s*type: Ossia\.Type\.Bool/,
  );
});
