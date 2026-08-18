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
    adapter.startMessage("A glass bell in winter", 7, 7, probeRack),
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
  assert.deepEqual(JSON.parse(JSON.stringify(start.params.probe_rack)), probeRack);
  assert.deepEqual(
    JSON.parse(adapter.updateParamsMessage({ observation_layer: 12 })),
    { action: "update_params", params: { observation_layer: 12 } },
  );
  assert.deepEqual(JSON.parse(adapter.stopMessage()), { action: "stop" });
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
        layer: 22,
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
  assert.equal(values["/model/name"], "google/gemma-3-1b-it");
  assert.equal(values["/observation/layer"], 17);
  assert.equal(values["/observation/sae_layer"], 22);
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
  ]) {
    assert.match(qml, new RegExp(`name: "${node}"`));
  }
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
  assert.match(qml, /Device\.read\("\/observation\/requested_layer"\)/);
  assert.match(qml, /function probeRackFromDevice\s*\(/);
  assert.match(qml, /updateParamsMessage/);
  assert.match(qml, /name: "max_tokens",\s*type: Ossia\.Type\.Int/);
  assert.match(
    qml,
    /name: "start",\s*type: Ossia\.Type\.Bool/,
  );
  assert.match(
    qml,
    /name: "stop",\s*type: Ossia\.Type\.Bool/,
  );
});
