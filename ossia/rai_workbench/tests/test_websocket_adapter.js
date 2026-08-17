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
  const start = JSON.parse(adapter.startMessage("A glass bell in winter", 7));

  assert.equal(start.action, "start");
  assert.equal(start.params.prompt, "A glass bell in winter");
  assert.equal(start.params.max_tokens, 7);
  assert.deepEqual(Array.from(start.params.emitter_signal_keys), [
    "model.layer_profile",
    "model.residual.vector",
    "sae.active_features",
  ]);
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
        layer: 17,
        sae_layer: 22,
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

  assert.equal(values["/probes/1/enabled"], true);
  assert.equal(values["/probes/1/id"], "residual-17");
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
  for (const node of [
    "connection",
    "run",
    "loading",
    "token",
    "model",
    "observation",
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
