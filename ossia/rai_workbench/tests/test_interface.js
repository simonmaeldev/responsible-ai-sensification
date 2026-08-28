const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const workbenchDir = path.resolve(__dirname, "..");

function readWorkbenchFile(name) {
  return fs.readFileSync(path.join(workbenchDir, name), "utf8");
}

function findDevice(value, name) {
  if (!value || typeof value !== "object") {
    return null;
  }
  if (value.Device && value.Device.Name === name) {
    return value.Device;
  }
  for (const child of Object.values(value)) {
    const found = findDevice(child, name);
    if (found) {
      return found;
    }
  }
  return null;
}

function findByScriptingName(value, name) {
  if (!value || typeof value !== "object") {
    return null;
  }
  if (value.Metadata && value.Metadata.ScriptingName === name) {
    return value;
  }
  for (const child of Object.values(value)) {
    const found = findByScriptingName(child, name);
    if (found) {
      return found;
    }
  }
  return null;
}

test("the Phase 3 UI preserves the Phase 2 run and evidence surface", () => {
  const qml = readWorkbenchFile("interface.qml");

  assert.match(qml, /import QtQuick\.Controls/);
  assert.match(qml, /import Score\.UI as UI/);
  for (const objectName of [
    "promptInput",
    "maxTokensInput",
    "runButton",
    "stopButton",
    "connectionState",
    "loadingProgress",
    "runError",
    "currentToken",
    "currentTokenId",
    "featureList",
  ]) {
    assert.match(qml, new RegExp(`objectName: "${objectName}"`));
  }

  for (const address of [
    "RAI Workbench:/run/prompt",
    "RAI Workbench:/run/max_tokens",
    "RAI Workbench:/run/start",
    "RAI Workbench:/run/stop",
    "RAI Workbench:/connection/state",
    "RAI Workbench:/run/state",
    "RAI Workbench:/run/error",
    "RAI Workbench:/loading/label",
    "RAI Workbench:/loading/detail",
    "RAI Workbench:/loading/progress",
    "RAI Workbench:/token/id",
    "RAI Workbench:/token/text",
  ]) {
    assert.match(qml, new RegExp(address.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  }

  assert.match(qml, /function startRun\s*\(/);
  assert.match(qml, /function startRun\s*\(\)\s*\{[\s\S]*?Score\.play\(\)/);
  assert.match(qml, /startValue\s*=\s*!startValue/);
  assert.match(qml, /function stopRun\s*\(/);
  assert.match(qml, /stopValue\s*=\s*!stopValue/);
  assert.match(qml, /JSON\.stringify\(root\.snapshotValue\("tokenText", root\.tokenText\)\)/);
  assert.doesNotMatch(qml, /font\.family:\s*"monospace"/);
  assert.doesNotMatch(qml, /\/vector\/\d+|values\s*:\s*\[/i);
});

test("the research view exposes synchronized token history and truthful provenance", () => {
  const qml = readWorkbenchFile("interface.qml");

  for (const objectName of [
    "tokenTimeline",
    "historyPosition",
    "modelProvenance",
    "denseProvenance",
    "saeProvenance",
    "selectedBlockDetails",
    "probeSummaryList",
  ]) {
    assert.match(qml, new RegExp(`objectName: "${objectName}"`));
  }
  assert.match(qml, /property var tokenHistory/);
  assert.match(qml, /function captureCurrentSnapshot\s*\(/);
  assert.match(qml, /function selectHistory\s*\(/);
  assert.match(qml, /function followLatest\s*\(/);
  assert.match(qml, /tokenRevision/);
  assert.match(qml, /JSON\.stringify/);
  assert.match(qml, /module path/i);
  assert.match(qml, /representation/i);
  assert.match(qml, /shape/i);
});

test("the research view maps real blocks and can move a matching all-layer SAE", () => {
  const qml = readWorkbenchFile("interface.qml");

  assert.match(qml, /id: blockRepeater/);
  assert.match(qml, /model: root\.modelLayerCount/);
  assert.match(qml, /RAI Workbench:\/blocks\//);
  assert.match(qml, /attention_type/);
  assert.match(qml, /delta_rms/);
  assert.match(qml, /cosine_to_previous/);
  assert.match(qml, /RAI Workbench:\/observation\/requested_layer/);
  assert.match(qml, /RAI Workbench:\/observation\/requested_sae_layer/);
  assert.match(qml, /function setObservationLayer\s*\(/);
  assert.match(qml, /function setSaeLayer\s*\(/);
  assert.match(qml, /followSaeLayer/);
  assert.match(qml, /matching SAE/i);
  assert.match(qml, /not semantic|no semantic proximity/i);
});

test("the score run controls expose the complete official 270M all-layer example", () => {
  const qml = readWorkbenchFile("interface.qml");

  for (const address of [
    "RAI Workbench:/run/model",
    "RAI Workbench:/run/sae_width",
    "RAI Workbench:/run/sae_l0",
    "RAI Workbench:/observation/sae_category",
    "RAI Workbench:/observation/sae_repo_id",
    "RAI Workbench:/observation/sae_revision",
  ]) {
    assert.match(qml, new RegExp(address.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  }
  assert.match(qml, /google\/gemma-3-270m/);
  assert.match(qml, /resid_post_all/);
  assert.match(qml, /Feature indices.*specific.*layer|specific.*layer.*feature indices/is);
});

test("the interface renders eight bounded provenance-bearing probe summaries and controls", () => {
  const qml = readWorkbenchFile("interface.qml");

  assert.match(qml, /id: probeSummaryRepeater/);
  assert.match(qml, /id: probeControlRepeater/);
  assert.match(qml, /model: 8/);
  assert.match(qml, /RAI Workbench:\/probes\//);
  assert.match(qml, /RAI Workbench:\/probe_controls\//);
  assert.match(qml, /function setProbeLayer\s*\(/);
  assert.match(qml, /module_path/);
  assert.match(qml, /token_index/);
  assert.match(qml, /dtype/);
  assert.match(qml, /representation/);
  assert.doesNotMatch(qml, /RAI Workbench:\/probes\/[^"\n]*vector/);
});

test("the interface renders twelve exact SAE and Neuronpedia evidence rows", () => {
  const qml = readWorkbenchFile("interface.qml");

  assert.match(qml, /id: featureRepeater/);
  assert.match(qml, /model: 12/);
  assert.match(qml, /"RAI Workbench:\/features\/"\s*\+\s*\(index \+ 1\)/);
  assert.match(qml, /featureIndex/);
  assert.match(qml, /featureActivation/);
  assert.match(qml, /featureDescription/);
  assert.match(qml, /toFixed\(6\)/);
  assert.match(qml, /No Neuronpedia description/);
  assert.match(qml, /function featureAt\s*\(/);
});

test("the interface keeps four patchable raw scalars synchronized with history", () => {
  const qml = readWorkbenchFile("interface.qml");

  assert.match(qml, /objectName: "patchableScalarList"/);
  assert.match(qml, /property var patchableScalarKeys/);
  assert.match(qml, /function patchableScalarAt\s*\(/);
  assert.match(qml, /patchableScalars:\s*root\.capturePatchableScalars\(\)/);
  for (const key of [
    "tensor_rms",
    "tensor_max_abs",
    "sae_active_count",
    "sae_top_activation",
  ]) {
    assert.match(qml, new RegExp(`RAI Workbench:/patchable/${key}`));
  }
  for (const field of [
    "valid",
    "value",
    "metric",
    "probe_id",
    "source_slot",
    "model",
    "token_index",
    "token_id",
    "token_text",
    "site",
    "layer",
    "module_path",
    "shape",
    "dtype",
    "representation",
    "feature_index",
  ]) {
    assert.match(qml, new RegExp(`/${field.replace(/[.*+?^${}()|[\\]\\]/g, "\\$&")}"`));
  }
  assert.match(qml, /raw values are unchanged/i);
  assert.match(qml, /index is an identifier, not semantic geometry/i);
});

test("the score-generated document embeds the exact Phase 1 device", () => {
  const scoreDocument = JSON.parse(readWorkbenchFile("rai-workbench.score"));
  const device = findDevice(scoreDocument, "RAI Workbench");

  assert.ok(device, "rai-workbench.score must contain the RAI Workbench device");
  assert.equal(device.Protocol, "59e81303-af24-4559-b33d-1c6f59f0f017");
  assert.equal(device.Address, "ws://127.0.0.1:8080/ws/stream");
  assert.equal(device.Text.trim(), readWorkbenchFile("websocket-device.qml").trim());
});

test("the score document contains one clearly removable built-in example mapping", () => {
  const scoreDocument = JSON.parse(readWorkbenchFile("rai-workbench.score"));
  const example = findByScriptingName(
    scoreDocument,
    "EXAMPLE_patchable_tensor_rms_delete_safe",
  );
  const documentText = JSON.stringify(scoreDocument);

  assert.ok(example, "the removable Slice 4 example process must be present");
  assert.equal(example.uuid, "ee3a50c0-a202-4f51-a26d-be57a939997d");
  assert.equal(example.ObjectName, "avnd_float");
  assert.equal(example.Inlets[0].Address, "RAI Workbench:/patchable/tensor_rms/value");
  assert.equal(example.Outlets.length, 1);
  assert.equal(example.Outlets[0].Address, undefined);
  assert.match(
    documentText,
    /RAI Workbench:\/patchable\/tensor_rms\/value/,
  );
  assert.equal(
    documentText.match(/EXAMPLE_patchable_tensor_rms_delete_safe/g).length,
    1,
  );
});

test("the runbook documents debug and normal custom UI launches", () => {
  const readme = readWorkbenchFile("README.md");

  assert.match(readme, /--ui-debug\s+ossia\/rai_workbench\/interface\.qml\s+ossia\/rai_workbench\/rai-workbench\.score/);
  assert.match(readme, /--ui\s+ossia\/rai_workbench\/interface\.qml\s+ossia\/rai_workbench\/rai-workbench\.score/);
  assert.match(readme, /four patchable scalar\s+observations/i);
  assert.match(readme, /EXAMPLE_patchable_tensor_rms_delete_safe/);
  assert.match(readme, /delete.*example.*observation.*remain/is);
});
