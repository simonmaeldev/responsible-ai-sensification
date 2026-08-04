"use strict";

const assert = require("assert");
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const receiverPath = path.join(__dirname, "..", "rai_osc_receiver.js");
const source = fs.readFileSync(receiverPath, "utf8");
const outputs = [[], [], []];

const namespacePath = path.join(__dirname, "..", "rai_ossia_namespace.maxpat");
const namespace = JSON.parse(fs.readFileSync(namespacePath, "utf8"));
const namespaceBoxes = namespace.patcher.boxes.map(({ box }) => box);
const namespaceById = new Map(namespaceBoxes.map((box) => [box.id, box]));

assert.strictEqual(namespaceById.get("obj-in").maxclass, "inlet",
    "the namespace abstraction must use a standard Max inlet");
const configIds = ["obj-port", "obj-gain", "obj-mute"];
for (const id of configIds) {
    assert.match(namespaceById.get(id).text, /@mode bi(?:\s|$)/,
        `${id} must remain remotely readable and writable`);
}
const statusParameters = namespaceBoxes.filter((box) =>
    typeof box.text === "string" && box.text.startsWith("ossia.parameter status/"));
assert.strictEqual(statusParameters.length, 23);
for (const box of statusParameters) {
    assert.match(box.text, /@mode get(?:\s|$)/,
        `${box.id} must remain read-only in OSCQuery`);
    assert.doesNotMatch(box.text, /@access\b/,
        `${box.id} must use the current ossia @mode attribute`);
}
const configOutlets = ["obj-out-port", "obj-out-gain", "obj-out-mute"]
    .map((id) => namespaceById.get(id));
assert(configOutlets.every((box) => box.maxclass === "outlet"),
    "the namespace abstraction must expose three standard Max outlets");
assert.deepStrictEqual(configOutlets.map((box) => box.patching_rect[0]), [650, 700, 750],
    "outlet placement must preserve port, gain, mute ordering");

const sandbox = {
    Math,
    Number,
    String,
    JSON,
    isFinite,
    autowatch: 0,
    inlets: 0,
    outlets: 0,
    inlet: 0,
    messagename: "",
    arrayfromargs(args) {
        return Array.prototype.slice.call(args);
    },
    outlet(index, ...args) {
        outputs[index].push(args);
    }
};

vm.createContext(sandbox);
vm.runInContext(source, sandbox, { filename: receiverPath });

function send(address, ...args) {
    sandbox.inlet = 0;
    sandbox.messagename = address;
    sandbox.anything.apply(sandbox, args);
}

function configure(selector, value) {
    sandbox.inlet = 1;
    sandbox.messagename = selector;
    sandbox.anything.call(sandbox, value);
}

function voiceMessages(selector) {
    return outputs[0].filter((message) => message[0] === selector);
}

sandbox.loadbang();
assert.deepStrictEqual(outputs[2].pop(), ["port", 9000]);
configure("port", 9100);
assert.strictEqual(sandbox.state.port, 9100);
assert.deepStrictEqual(outputs[2].pop(), ["port", 9100]);
configure("port", 9000);
configure("master_gain", 0.35);
configure("mute", 0);

const run = "node-contract-test";
send("/rai/v1/run/start", run, 120, "timed");
assert.strictEqual(sandbox.state.run_id, run);
assert.strictEqual(sandbox.state.release_count, 1);

send("/rai/v1/control/bpm", 120);
send("/rai/v1/control/mode", "timed");
send("/rai/v1/control/loop", 0);
send("/rai/v1/control/tonality_enabled", 1);
send("/rai/v1/control/prompt_influence", 0.25);
send("/rai/v1/control/tonality_pitch_bias", 0.5);

send("/rai/v1/token", run, 1, 4242, "loopback token", 17);
send("/rai/v1/note", run, 1, 0, 12345, 330.25, 0.75, 2, "pad");
send("/rai/v1/note", run, 1, 1, 54321, 445.125, 0.5, 7, "bell");
send("/rai/v1/tonality", run, 1, "liminal amber", 0.875, 0.5);
send("/rai/v1/token/end", run, 1, 2);

assert.strictEqual(sandbox.lastCompletedFrame.notes.length, 2);
assert.strictEqual(sandbox.lastCompletedFrame.notes[1].frequency_hz, 445.125);
assert.strictEqual(sandbox.lastCompletedFrame.notes[1].activation, 0.5);
assert.strictEqual(sandbox.lastCompletedFrame.notes[1].feature_index, 54321);
assert.strictEqual(sandbox.lastCompletedFrame.notes[1].cluster_id, 7);
assert.strictEqual(sandbox.lastCompletedFrame.notes[1].instrument, "bell");
assert.strictEqual(sandbox.lastCompletedFrame.tonality.name, "liminal amber");
assert.strictEqual(sandbox.state.last_frequency, 445.125);
assert(voiceMessages("note").some((message) => message[1] === 445.125),
    "the raw frequency must reach a voice note message unchanged");

const releasesBeforeDone = sandbox.state.release_count;
send("/rai/v1/run/done", run);
assert.strictEqual(sandbox.state.run_state, "done");
assert.strictEqual(sandbox.state.release_count, releasesBeforeDone,
    "done must not release voices");

send("/rai/v1/control/bpm", 96);
send("/rai/v1/control/mode", "sustain");
send("/rai/v1/control/loop", 1);
send("/rai/v1/control/tonality_enabled", 0);
send("/rai/v1/control/prompt_influence", 0.625);
send("/rai/v1/control/tonality_pitch_bias", 0.375);
assert.strictEqual(sandbox.state.bpm, 96);
assert.strictEqual(sandbox.state.mode, "sustain");
assert.strictEqual(sandbox.state.loop, 1);
assert.strictEqual(sandbox.state.tonality_enabled, 0);
assert.strictEqual(sandbox.state.prompt_influence, 0.625);
assert.strictEqual(sandbox.state.pitch_bias, 0.375);

send("/rai/v1/future/unknown", "ignore me");
assert.strictEqual(sandbox.state.unknown_count, 1);
send("/rai/v1/note", run, 999);
assert.match(sandbox.state.last_error, /expected 8 args/);

send("/rai/v1/run/silent", run);
assert.strictEqual(sandbox.state.release_count, releasesBeforeDone + 1);
assert.strictEqual(sandbox.state.last_release_reason, "run_silent");
send("/rai/v1/run/stop", run);
assert.strictEqual(sandbox.state.release_count, releasesBeforeDone + 2);
assert.strictEqual(sandbox.state.last_release_reason, "run_stop");
assert.strictEqual(sandbox.state.state, "listening");

const sustainRun = "node-sustain-test";
send("/rai/v1/run/start", sustainRun, 96, "sustain");
send("/rai/v1/token", sustainRun, 1, 1, "held", 1);
send("/rai/v1/note", sustainRun, 1, 0, 9, 612.75, 1.0, -1, "default");
send("/rai/v1/token/end", sustainRun, 1, 1);
assert(voiceMessages("sustain").some((message) => message[1] === 612.75),
    "sustain mode must preserve the raw frequency");
const releasesBeforeNextToken = sandbox.state.release_count;
send("/rai/v1/token", sustainRun, 2, 2, "next", 2);
assert.strictEqual(sandbox.state.release_count, releasesBeforeNextToken + 1,
    "a new sustain token must release the previous frame");

console.log(JSON.stringify({
    passed: true,
    handledAddresses: 14,
    timedFrequencyHz: 445.125,
    sustainFrequencyHz: 612.75,
    unknownIgnored: sandbox.state.unknown_count,
    lastReleaseReason: sandbox.state.last_release_reason
}, null, 2));
