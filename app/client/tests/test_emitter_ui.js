"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

class FakeClassList {
  constructor() { this.values = new Set(); }
  add(...names) { names.forEach(name => this.values.add(name)); }
  remove(...names) { names.forEach(name => this.values.delete(name)); }
  toggle(name, force) {
    if (force === true) { this.values.add(name); return true; }
    if (force === false) { this.values.delete(name); return false; }
    if (this.values.has(name)) { this.values.delete(name); return false; }
    this.values.add(name); return true;
  }
  contains(name) { return this.values.has(name); }
}

class FakeElement {
  constructor(tag = "div") {
    this.tagName = tag.toUpperCase();
    this.children = [];
    this.classList = new FakeClassList();
    this.dataset = {};
    this.style = { setProperty() {} };
    this.value = "";
    this.checked = false;
    this.disabled = false;
    this.textContent = "";
    this.offsetWidth = 640;
    this.offsetHeight = 240;
    this.width = 640;
    this.height = 240;
    this.listeners = {};
  }
  append(...children) {
    children.forEach(child => this.appendChild(child));
  }
  appendChild(child) {
    this.children.push(child);
    if (!this.value && child && child.value) this.value = child.value;
    return child;
  }
  addEventListener(type, handler) { this.listeners[type] = handler; }
  setAttribute(name, value) { this.attributes = this.attributes || {}; this.attributes[name] = String(value); }
  getAttribute(name) { return this.attributes?.[name] ?? null; }
  querySelector() { return null; }
  querySelectorAll() { return []; }
  scrollTo(options) { this.lastScrollOptions = options; }
  scrollIntoView() {}
  getContext() {
    return {
      beginPath() {}, clearRect() {}, fillRect() {}, lineTo() {}, moveTo() {},
      stroke() {}, strokeRect() {},
    };
  }
  set innerHTML(value) {
    this.children = [];
    if (value === "") this.value = "";
  }
  get innerHTML() { return ""; }
}

const root = path.resolve(__dirname, "..");
const html = fs.readFileSync(path.join(root, "index.html"), "utf8");
const sourcePath = path.join(root, "main.js");
const source = fs.readFileSync(sourcePath, "utf8");
const htmlIds = new Set([...html.matchAll(/\bid="([^"]+)"/g)].map(match => match[1]));
const referencedIds = [...source.matchAll(/getElementById\("([^"]+)"\)/g)].map(match => match[1]);
assert.deepEqual(referencedIds.filter(id => !htmlIds.has(id)), []);
assert.equal((html.match(/data-workspace-tab=/g) || []).length, 0);
assert.doesNotMatch(html, /class="workspace-nav"/);
assert.doesNotMatch(html, /data-workspace-tab="(?:observe|interpret|transform|route)"/);
assert.match(html, /<textarea[^>]+id="prompt"/);
assert.match(html, /id="model-anatomy"/);
assert.match(html, /id="gemma-model-map"/);
assert.match(html, /id="model-depth-grid"/);
assert.doesNotMatch(html, /class="model-path-stage"/);
assert.match(html, /id="model-layer-readout"/);
assert.match(html, /id="live-token-current"/);
assert.match(html, /id="live-token-position"/);
assert.match(html, /id="cv-text-content"/);
assert.match(html, /id="live-feature-directions"/);
assert.match(html, /id="live-feature-count"/);
assert.match(html, /id="tonality-lens-workspace"/);
assert.match(html, /id="osc-popover"/);
assert.match(html, /id="btn-controls-toggle"[^>]+aria-expanded="false"/);
assert.match(html, /id="btn-tonality-toggle"[^>]+aria-expanded="false"/);
assert.match(html, /id="control-drawer"[^>]+aria-hidden="true"/);
assert.match(html, /id="tonality-drawer"[^>]+aria-hidden="true"/);
assert.match(html, /id="drawer-backdrop"[^>]+hidden/);
assert.match(html, /<details\s+id="representation-disclosure"(?![^>]*\sopen)[^>]*>/);
assert.match(html, /<details\s+id="mapping-editor-disclosure"(?![^>]*\sopen)[^>]*>/);
assert.match(html, /id="btn-layer-prev"/);
assert.match(html, /id="btn-layer-next"/);
assert.match(html, /id="gemma-block-diagram"/);
assert.match(html, /id="layer-profile-metrics"/);
assert.match(html, /id="dense-state-canvas"/);
assert.match(html, /id="sparse-state-canvas"/);
assert.doesNotMatch(html, /data-workspace-panel=/);
assert.doesNotMatch(html, /class="atlas-view-tabs"/);
assert.match(html, /id="signal-catalogue-search"/);
assert.match(html, /id="signal-catalogue-list"/);
assert.match(html, /id="loading-panel"/);
assert.match(html, /id="loading-progress"/);
for (const stage of ["model", "sae", "neuronpedia", "features", "tonality", "generation"]) {
  assert.match(html, new RegExp(`data-loading-stage="${stage}"`));
}
const visualDisclosure = html.match(/<details\s+id="visual-proof-panel"[^>]*>/);
assert.ok(visualDisclosure, "visual proof of concept must use a details disclosure");
assert.doesNotMatch(visualDisclosure[0], /\sopen(?:\s|=|>)/);

const elements = new Map([...htmlIds].map(id => [id, new FakeElement()]));
const loadingBadges = new Map(
  ["model", "sae", "neuronpedia", "features", "tonality", "generation"].map(stage => {
    const element = new FakeElement("span");
    element.dataset.loadingStage = stage;
    element.dataset.state = "pending";
    return [stage, element];
  }),
);
const visualsViewport = new FakeElement("section");
global.document = {
  getElementById(id) { return elements.get(id) || new FakeElement(); },
  createElement(tag) { return new FakeElement(tag); },
  querySelector(selector) {
    if (selector === ".visuals") return visualsViewport;
    return null;
  },
  querySelectorAll(selector) {
    if (selector === "[data-loading-stage]") return [...loadingBadges.values()];
    return [];
  },
};
global.window = global;
global.location = { protocol: "http:", host: "127.0.0.1:8080" };
global.localStorage = { getItem() { return null; }, setItem() {} };
global.requestAnimationFrame = () => 0;
global.CSS = { escape: value => String(value) };
global.WebSocket = class {
  static OPEN = 1;
  static instances = [];
  constructor() {
    this.readyState = 1;
    this.sent = [];
    global.WebSocket.instances.push(this);
  }
  send(message) { this.sent.push(JSON.parse(message)); }
};
global.fetch = async url => ({
  async json() {
    if (url.endsWith("model-options")) {
      return {
        models: ["test-model"],
        model_catalogue: {
          "test-model": {
            layers: [22], widths: ["65k"], observation_layers: [0, 1, 2],
            architecture: {
              layer_count: 3, hidden_size: 2, intermediate_size: 4,
              attention_heads: 2, key_value_heads: 1, head_dim: 1,
              sliding_window: 8, max_position_embeddings: 32,
              layer_types: ["sliding_attention", "sliding_attention", "full_attention"],
            },
          },
        },
        strategies: [{ value: "identity", label: "Identity", description: "test" }],
        modes: [{ value: "timed", label: "Timed", description: "test" }],
      };
    }
    if (url.endsWith("defaults")) return { emitter_mappings: [] };
    if (url.endsWith("emitter-mapping")) {
      return {
        max_mappings: 32,
        curves: ["linear", "ease_in", "ease_out", "s_curve"],
        signals: [
          { key: "activation.max", label: "Maximum activation", group: "SAE" },
          { key: "tonality.score", label: "Tonality", group: "Semantic" },
          { key: "feature.top_share", label: "Top share", group: "SAE" },
        ],
        targets: [
          { key: "audio.gain", label: "Gain", group: "Audio", minimum: 0, maximum: 1 },
          { key: "audio.pan", label: "Pan", group: "Audio", minimum: -1, maximum: 1 },
        ],
        default_mappings: [
          { id: "starter", source: "activation.max", target: "audio.gain", output_min: 0, output_max: 1 },
        ],
      };
    }
    if (url.endsWith("emitter-signals")) {
      return {
        default_active: ["activation.max", "model.residual.rms"],
        signals: [
          {
            key: "model.layer_profile", label: "Layer profile", group: "Model",
            location: "decoder.layers.residual", kind: "derived", value_type: "layer_profile",
            description: "layer summaries", default_active: false, mappable: false,
            cost: "medium",
          },
          {
            key: "activation.max", label: "Maximum activation", group: "SAE",
            location: "sae.output", kind: "derived", value_type: "scalar",
            description: "strongest feature", default_active: true, mappable: true,
            cost: "low",
          },
          {
            key: "model.residual.vector", label: "Residual vector", group: "Model",
            location: "decoder.layer.selected.residual", kind: "raw", value_type: "vector",
            description: "raw residual", default_active: false, mappable: false,
            cost: "high",
          },
        ],
      };
    }
    if (url.endsWith("tonalities")) {
      return { tonalities: [{ name: "glass", description: "clear", intervals: [0, 7] }] };
    }
    return {};
  },
});

const instrumented = `${source}\n;globalThis.__emitterTest = { completeMapping, templateMappings, morphMapping, lerp, filterSignalCatalogue, signalRouteSummary, describeStreamValue, residualVectorStats, safeObservationLayer, normalizedLayerActivity, layerProfileEntry, layerProfilePoints, stepObservationLayer, scalePresetForIntervals, normalizedLens, visibleTokenLabel, featureDirectionRows, appendTokenToTimeline, handleMessage, handleLoadingMessage, startLoadingProgress, finishLoadingProgress, setWorkspace, setInterfaceDrawer, setSignalSelection(keys) { sessionActive = true; selectedEmitterSignalKeys = new Set(keys); sendSignalSelectionUpdate(); } };`;
vm.runInThisContext(instrumented, { filename: sourcePath });

setTimeout(() => {
  const api = global.__emitterTest;
  const mapping = api.completeMapping({ source: "tonality.score", target: "audio.pan" });
  assert.equal(mapping.output_min, -1);
  assert.equal(mapping.output_max, 1);
  assert.equal(api.lerp(0, 10, 0.25), 2.5);
  const morphed = api.morphMapping(
    { ...mapping, output_min: -1, output_max: 0 },
    { ...mapping, output_min: 0, output_max: 1 },
    0.5,
    0,
  );
  assert.equal(morphed.output_min, -0.5);
  assert.equal(morphed.output_max, 0.5);
  assert.ok(api.templateMappings("activation").length > 0);
  const filtered = api.filterSignalCatalogue(
    [
      { key: "activation.max", label: "Maximum activation", group: "SAE", kind: "derived", location: "sae.output" },
      { key: "model.residual.vector", label: "Residual vector", group: "Model", kind: "raw", location: "decoder.layer.selected.residual" },
    ],
    "residual",
    "raw",
  );
  assert.deepEqual(filtered.map(item => item.key), ["model.residual.vector"]);
  assert.deepEqual(
    api.signalRouteSummary(
      { key: "activation.max", mappable: true },
      new Set(["activation.max"]),
      [{ enabled: true, source: "activation.max" }, { enabled: false, source: "activation.max" }],
    ),
    { active: true, mappingCount: 1, connector: "Not routed" },
  );
  assert.equal(
    api.describeStreamValue({ value_type: "vector", value: { values: [1, 2], shape: [2], dtype: "float32" } }),
    "2 float32 values",
  );
  assert.equal(
    api.describeStreamValue({ value_type: "sparse_vector", value: [{ index: 1, activation: 2 }] }),
    "1 active feature",
  );
  assert.equal(
    api.describeStreamValue({ value_type: "layer_profile", value: { layers: [{}, {}, {}], shape: [3] } }),
    "3 transformer blocks",
  );
  assert.deepEqual(api.residualVectorStats([-2, 0, 2]), {
    count: 3,
    minimum: -2,
    maximum: 2,
    maxAbs: 2,
    rms: Math.sqrt(8 / 3),
  });
  assert.equal(api.safeObservationLayer(99, [0, 1, 2], 1), 2);
  assert.equal(api.safeObservationLayer("bad", [0, 1, 2], 1), 1);
  const profile = [
    { layer: 0, delta_rms: null },
    { layer: 1, delta_rms: 2 },
    { layer: 2, delta_rms: 4 },
  ];
  assert.equal(api.normalizedLayerActivity(profile[1], profile), 0.5);
  assert.equal(api.normalizedLayerActivity(profile[2], profile), 1);
  assert.deepEqual(api.layerProfileEntry(profile, 1), profile[1]);
  assert.deepEqual(api.layerProfilePoints(profile, 100, 40), [
    { layer: 0, x: 0, y: 40, value: 0 },
    { layer: 1, x: 50, y: 20, value: 2 },
    { layer: 2, x: 100, y: 0, value: 4 },
  ]);
  assert.deepEqual(
    api.featureDirectionRows([
      { index: 4, activation: 2, description: "quiet direction" },
      { index: 8, activation: 8, description: "strong direction" },
      { index: 2, activation: 4, description: "middle direction" },
      { index: 9, activation: 0, description: "inactive" },
    ], 2),
    [
      { index: 8, activation: 8, description: "strong direction", relative: 1 },
      { index: 2, activation: 4, description: "middle direction", relative: 0.5 },
    ],
  );
  assert.equal(api.visibleTokenLabel("\n"), "↵");
  assert.equal(api.visibleTokenLabel(" moon"), "␠moon");
  assert.equal(api.visibleTokenLabel(""), "∅");
  api.appendTokenToTimeline({ token: " plain" }, 0);
  assert.equal(elements.get("cv-text-content").children.length, 1);
  assert.equal(elements.get("cv-text-content").children[0].textContent, "␠plain");
  elements.get("cv-text-content").innerHTML = "";
  api.setWorkspace("signals");
  assert.deepEqual(visualsViewport.lastScrollOptions, { top: 0, behavior: "instant" });
  api.setInterfaceDrawer("controls", true);
  assert.equal(elements.get("control-drawer").classList.contains("is-open"), true);
  assert.equal(elements.get("control-drawer").getAttribute("aria-hidden"), "false");
  assert.equal(elements.get("tonality-drawer").getAttribute("aria-hidden"), "true");
  assert.equal(elements.get("btn-controls-toggle").getAttribute("aria-expanded"), "true");
  assert.equal(elements.get("drawer-backdrop").hidden, false);
  api.setInterfaceDrawer("tonality", true);
  assert.equal(elements.get("control-drawer").getAttribute("aria-hidden"), "true");
  assert.equal(elements.get("tonality-drawer").classList.contains("is-open"), true);
  assert.equal(elements.get("btn-tonality-toggle").getAttribute("aria-expanded"), "true");
  assert.equal(api.stepObservationLayer(0, -1, [0, 1, 2]), 0);
  assert.equal(api.stepObservationLayer(1, 1, [0, 1, 2]), 2);
  api.handleMessage({
    type: "model_structure",
    model: "test-model",
    architecture: {
      layer_count: 3,
      hidden_size: 2,
      intermediate_size: 4,
      attention_heads: 2,
      key_value_heads: 1,
      head_dim: 1,
      sliding_window: 8,
      layer_types: ["sliding_attention", "sliding_attention", "full_attention"],
    },
  });
  assert.equal(elements.get("anatomy-layer-count").textContent, "3 blocks");
  api.handleMessage({
    type: "token",
    token: " test",
    notes: [],
    observation: { layer: 1, sae_layer: 22, sae_width: "65k" },
    emitter: {
      signals: {},
      controls: {},
      mappings: [],
      streams: {
        "sae.active_features": {
          value_type: "sparse_vector",
          value: [
            { index: 12, activation: 7, description: "first live direction" },
            { index: 20, activation: 3, description: "second live direction" },
          ],
        },
      },
    },
  });
  assert.equal(elements.get("cv-text-content").children.length, 1, "tokens must not depend on colour notes");
  assert.equal(elements.get("live-token-current").textContent, '" test"');
  assert.equal(elements.get("live-feature-count").textContent, "2 active");
  assert.equal(elements.get("live-feature-directions").children.length, 2);
  assert.equal(api.scalePresetForIntervals([0, 2, 4, 5, 7, 9, 11]), "major");
  assert.equal(api.scalePresetForIntervals([0, 1, 6]), "custom");
  assert.equal(api.normalizedLens({ name: "D idea", description: "bright", intervals: [0, 4, 7], root: 14 }).root, 2);
  assert.ok(elements.get("signal-catalogue-list").children.length > 0);
  api.setSignalSelection(["activation.max", "model.residual.vector"]);
  assert.deepEqual(global.WebSocket.instances[0].sent.at(-1), {
    action: "update_params",
    params: { emitter_signal_keys: ["activation.max", "model.residual.vector"] },
  });
  api.startLoadingProgress();
  assert.equal(elements.get("loading-panel").classList.contains("hidden"), false);
  api.handleLoadingMessage({
    type: "loading",
    stage_key: "sae",
    label: "Sparse autoencoder",
    state: "active",
    detail: "Layer 22 · width 65k",
    progress: 1 / 6,
  });
  assert.equal(elements.get("loading-title").textContent, "Sparse autoencoder");
  assert.equal(elements.get("loading-detail").textContent, "Layer 22 · width 65k");
  assert.equal(elements.get("loading-percent").textContent, "17%");
  assert.equal(elements.get("loading-progress").value, 17);
  assert.equal(loadingBadges.get("sae").dataset.state, "active");
  assert.equal(loadingBadges.get("model").dataset.state, "pending");
  api.finishLoadingProgress();
  assert.equal(elements.get("loading-panel").classList.contains("hidden"), true);
  api.startLoadingProgress();
  api.handleMessage({ type: "error", message: "model unavailable" });
  api.handleMessage({ type: "stopped" });
  assert.equal(elements.get("loading-panel").classList.contains("hidden"), false);
  assert.equal(elements.get("loading-panel").dataset.state, "error");
  assert.equal(elements.get("loading-detail").textContent, "model unavailable");
  console.log(JSON.stringify({ passed: true, referencedIds: referencedIds.length }));
}, 25);
