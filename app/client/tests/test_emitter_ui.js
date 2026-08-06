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
  querySelector() { return null; }
  querySelectorAll() { return []; }
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
assert.match(html, /data-control-tab="signals"/);
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
global.document = {
  getElementById(id) { return elements.get(id) || new FakeElement(); },
  createElement(tag) { return new FakeElement(tag); },
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
        model_catalogue: { "test-model": { layers: [22], widths: ["65k"] } },
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

const instrumented = `${source}\n;globalThis.__emitterTest = { completeMapping, templateMappings, morphMapping, lerp, filterSignalCatalogue, signalRouteSummary, describeStreamValue, handleMessage, handleLoadingMessage, startLoadingProgress, finishLoadingProgress, setSignalSelection(keys) { sessionActive = true; selectedEmitterSignalKeys = new Set(keys); sendSignalSelectionUpdate(); } };`;
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
