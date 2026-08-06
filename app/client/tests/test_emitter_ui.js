"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

class FakeClassList {
  add() {}
  remove() {}
  toggle() {}
  contains() { return false; }
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

const elements = new Map([...htmlIds].map(id => [id, new FakeElement()]));
global.document = {
  getElementById(id) { return elements.get(id) || new FakeElement(); },
  createElement(tag) { return new FakeElement(tag); },
  querySelectorAll() { return []; },
};
global.window = global;
global.location = { protocol: "http:", host: "127.0.0.1:8080" };
global.localStorage = { getItem() { return null; }, setItem() {} };
global.requestAnimationFrame = () => 0;
global.CSS = { escape: value => String(value) };
global.WebSocket = class {
  static OPEN = 1;
  constructor() { this.readyState = 1; }
  send() {}
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
    if (url.endsWith("tonalities")) {
      return { tonalities: [{ name: "glass", description: "clear", intervals: [0, 7] }] };
    }
    return {};
  },
});

const instrumented = `${source}\n;globalThis.__emitterTest = { completeMapping, templateMappings, morphMapping, lerp };`;
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
  console.log(JSON.stringify({ passed: true, referencedIds: referencedIds.length }));
}, 25);
