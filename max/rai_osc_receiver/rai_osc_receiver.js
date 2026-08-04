autowatch = 1;
inlets = 2;
outlets = 3;

var MAX_VOICES = 16;
var MAX_PENDING_FRAMES = 8;
var frames = {};
var frameOrder = [];
var lastCompletedFrame = null;

var state = {
    port: 9000,
    master_gain: 0.35,
    mute: 0,
    state: "listening",
    run_state: "idle",
    run_id: "-",
    sequence: -1,
    token_text: "-",
    note_count: 0,
    tonality: "-",
    bpm: 120,
    mode: "timed",
    loop: 0,
    tonality_enabled: 0,
    prompt_influence: 0.0,
    pitch_bias: 0.0,
    last_frequency: 0.0,
    last_activation: 0.0,
    last_feature: -1,
    last_cluster: -1,
    last_instrument: "-",
    last_error: "none",
    unknown_count: 0,
    release_count: 0,
    last_release_reason: "none",
    last_frame_json: "{}"
};

function loadbang() {
    emitSnapshot();
    outlet(2, "port", state.port);
}

function anything() {
    var selector = String(messagename);
    var args = arrayfromargs(arguments);

    if (inlet === 1) {
        handleConfig(selector, args);
        return;
    }

    if (selector === "list" && args.length > 0 && isAddress(args[0])) {
        selector = String(args.shift());
    }

    try {
        handleOsc(selector, args);
    } catch (error) {
        setError("receiver exception for " + selector + ": " + error);
    }
}

function handleConfig(selector, args) {
    if (selector === "port") {
        if (!requireArgs(selector, args, 1)) {
            return;
        }
        var port = integerValue(args[0]);
        if (port === null || port < 1 || port > 65535) {
            setError("invalid UDP port: " + args[0]);
            return;
        }
        state.port = port;
        publish("port", port);
        state.state = "listening";
        publish("state", state.state);
        outlet(2, "port", port);
        return;
    }

    if (selector === "master_gain") {
        if (!requireArgs(selector, args, 1)) {
            return;
        }
        var gain = finiteValue(args[0]);
        if (gain === null) {
            setError("invalid master gain: " + args[0]);
            return;
        }
        state.master_gain = clamp(gain, 0.0, 0.8);
        publish("master_gain", state.master_gain);
        return;
    }

    if (selector === "mute") {
        if (!requireArgs(selector, args, 1)) {
            return;
        }
        state.mute = booleanInt(args[0]);
        publish("mute", state.mute);
        return;
    }

    if (selector === "reset") {
        frames = {};
        frameOrder = [];
        releaseAll("reset");
        state.state = "listening";
        state.run_state = "idle";
        state.run_id = "-";
        state.sequence = -1;
        state.token_text = "-";
        state.note_count = 0;
        state.tonality = "-";
        state.last_error = "none";
        emitSnapshot();
        return;
    }

    if (selector === "dump") {
        emitSnapshot();
        return;
    }

    setError("unknown receiver config message: " + selector);
}

function handleOsc(address, args) {
    if (!isAddress(address)) {
        setError("malformed OSC address: " + address);
        return;
    }

    markReceiving();

    switch (address) {
    case "/rai/v1/run/start":
        handleRunStart(args);
        break;
    case "/rai/v1/token":
        handleToken(args);
        break;
    case "/rai/v1/note":
        handleNote(args);
        break;
    case "/rai/v1/tonality":
        handleTonality(args);
        break;
    case "/rai/v1/token/end":
        handleTokenEnd(args);
        break;
    case "/rai/v1/run/done":
        handleRunDone(args);
        break;
    case "/rai/v1/run/stop":
        handleRunStop(args);
        break;
    case "/rai/v1/run/silent":
        handleRunSilent(args);
        break;
    case "/rai/v1/control/bpm":
        handleControl("bpm", args, "int");
        break;
    case "/rai/v1/control/mode":
        handleControl("mode", args, "string");
        break;
    case "/rai/v1/control/loop":
        handleControl("loop", args, "bool");
        break;
    case "/rai/v1/control/tonality_enabled":
        handleControl("tonality_enabled", args, "bool");
        break;
    case "/rai/v1/control/prompt_influence":
        handleControl("prompt_influence", args, "float");
        break;
    case "/rai/v1/control/tonality_pitch_bias":
        handleControl("pitch_bias", args, "float");
        break;
    default:
        state.unknown_count += 1;
        publish("unknown_count", state.unknown_count);
        return;
    }
}

function handleRunStart(args) {
    if (!requireArgs("/rai/v1/run/start", args, 3)) {
        return;
    }
    var runId = nonEmptyString(args[0]);
    var bpm = integerValue(args[1]);
    var mode = nonEmptyString(args[2]);
    if (runId === null || bpm === null || bpm <= 0 || mode === null) {
        setError("invalid /run/start payload");
        return;
    }

    frames = {};
    frameOrder = [];
    releaseAll("run_start");
    state.run_id = runId;
    state.run_state = "started";
    state.sequence = -1;
    state.token_text = "-";
    state.note_count = 0;
    state.tonality = "-";
    state.bpm = bpm;
    state.mode = mode;
    state.last_error = "none";
    publish("run_id", state.run_id);
    publish("run_state", state.run_state);
    publish("sequence", state.sequence);
    publish("token_text", state.token_text);
    publish("note_count", state.note_count);
    publish("tonality", state.tonality);
    publish("bpm", state.bpm);
    publish("mode", state.mode);
    publish("last_error", state.last_error);
}

function handleToken(args) {
    if (!requireArgs("/rai/v1/token", args, 5)) {
        return;
    }
    var runId = nonEmptyString(args[0]);
    var sequence = integerValue(args[1]);
    var tokenId = integerValue(args[2]);
    var tokenText = String(args[3]);
    var elapsedMs = integerValue(args[4]);
    if (!validRun(runId) || sequence === null || tokenId === null || elapsedMs === null) {
        setError("invalid /token payload");
        return;
    }

    if (state.mode === "sustain") {
        releaseAll("next_token");
    }

    var key = frameKey(runId, sequence);
    if (frames[key]) {
        setError("duplicate token frame replaced: " + runId + "/" + sequence);
    }
    frames[key] = {
        run_id: runId,
        sequence: sequence,
        token_id: tokenId,
        token_text: tokenText,
        elapsed_ms: elapsedMs,
        notes: [],
        tonality: null
    };
    rememberFrameKey(key);
    state.sequence = sequence;
    state.token_text = tokenText.length ? tokenText : "-";
    state.note_count = 0;
    publish("sequence", state.sequence);
    publish("token_text", state.token_text);
    publish("note_count", state.note_count);
}

function handleNote(args) {
    if (!requireArgs("/rai/v1/note", args, 8)) {
        return;
    }
    var runId = nonEmptyString(args[0]);
    var sequence = integerValue(args[1]);
    var noteIndex = integerValue(args[2]);
    var featureIndex = integerValue(args[3]);
    var frequency = finiteValue(args[4]);
    var activation = finiteValue(args[5]);
    var clusterId = integerValue(args[6]);
    var instrument = String(args[7]);
    if (!validRun(runId) || sequence === null || noteIndex === null ||
            featureIndex === null || frequency === null || frequency <= 0 ||
            activation === null || clusterId === null) {
        setError("invalid /note payload");
        return;
    }

    var frame = getOrCreateFrame(runId, sequence, "/note before /token");
    if (!frame) {
        return;
    }
    frame.notes.push({
        note_index: noteIndex,
        feature_index: featureIndex,
        frequency_hz: frequency,
        activation: activation,
        cluster_id: clusterId,
        instrument: instrument
    });

    state.sequence = sequence;
    state.note_count = frame.notes.length;
    state.last_frequency = frequency;
    state.last_activation = activation;
    state.last_feature = featureIndex;
    state.last_cluster = clusterId;
    state.last_instrument = instrument.length ? instrument : "default";
    publish("sequence", state.sequence);
    publish("note_count", state.note_count);
    publish("last_frequency", state.last_frequency);
    publish("last_activation", state.last_activation);
    publish("last_feature", state.last_feature);
    publish("last_cluster", state.last_cluster);
    publish("last_instrument", state.last_instrument);
}

function handleTonality(args) {
    if (!requireArgs("/rai/v1/tonality", args, 5)) {
        return;
    }
    var runId = nonEmptyString(args[0]);
    var sequence = integerValue(args[1]);
    var name = String(args[2]);
    var score = finiteValue(args[3]);
    var effectivePitchBias = finiteValue(args[4]);
    if (!validRun(runId) || sequence === null || score === null || effectivePitchBias === null) {
        setError("invalid /tonality payload");
        return;
    }
    var frame = getOrCreateFrame(runId, sequence, "/tonality before /token");
    if (!frame) {
        return;
    }
    frame.tonality = {
        name: name,
        score: score,
        effective_pitch_bias: effectivePitchBias
    };
    state.tonality = name.length ? name : "-";
    publish("tonality", state.tonality);
}

function handleTokenEnd(args) {
    if (!requireArgs("/rai/v1/token/end", args, 3)) {
        return;
    }
    var runId = nonEmptyString(args[0]);
    var sequence = integerValue(args[1]);
    var emittedCount = integerValue(args[2]);
    if (!validRun(runId) || sequence === null || emittedCount === null || emittedCount < 0) {
        setError("invalid /token/end payload");
        return;
    }
    var key = frameKey(runId, sequence);
    var frame = frames[key];
    if (!frame) {
        setError("/token/end without a buffered frame: " + runId + "/" + sequence);
        return;
    }
    if (frame.notes.length !== emittedCount) {
        setError("token note count mismatch: expected " + emittedCount + ", received " + frame.notes.length);
    }
    flushFrame(key, frame);
}

function handleRunDone(args) {
    if (!requireArgs("/rai/v1/run/done", args, 1)) {
        return;
    }
    var runId = nonEmptyString(args[0]);
    if (!validRun(runId)) {
        setError("invalid /run/done run ID");
        return;
    }
    state.run_state = "done";
    publish("run_state", state.run_state);
}

function handleRunSilent(args) {
    if (!requireArgs("/rai/v1/run/silent", args, 1)) {
        return;
    }
    var runId = nonEmptyString(args[0]);
    if (!validRun(runId)) {
        setError("invalid /run/silent run ID");
        return;
    }
    releaseAll("run_silent");
    state.run_state = "silent";
    publish("run_state", state.run_state);
}

function handleRunStop(args) {
    if (!requireArgs("/rai/v1/run/stop", args, 1)) {
        return;
    }
    var runId = nonEmptyString(args[0]);
    if (!validRun(runId)) {
        setError("invalid /run/stop run ID");
        return;
    }
    releaseAll("run_stop");
    frames = {};
    frameOrder = [];
    state.run_state = "stopped";
    state.state = "listening";
    publish("run_state", state.run_state);
    publish("state", state.state);
}

function handleControl(name, args, type) {
    if (!requireArgs("/rai/v1/control/" + name, args, 1)) {
        return;
    }
    var value;
    if (type === "int") {
        value = integerValue(args[0]);
        if (value === null || value <= 0) {
            setError("invalid control " + name + ": " + args[0]);
            return;
        }
    } else if (type === "float") {
        value = finiteValue(args[0]);
        if (value === null) {
            setError("invalid control " + name + ": " + args[0]);
            return;
        }
    } else if (type === "bool") {
        value = booleanInt(args[0]);
    } else {
        value = String(args[0]);
        if (!value.length) {
            setError("invalid control " + name + ": empty string");
            return;
        }
    }
    state[name] = value;
    publish(name, value);
}

function flushFrame(key, frame) {
    delete frames[key];
    forgetFrameKey(key);
    lastCompletedFrame = frame;

    state.sequence = frame.sequence;
    state.token_text = frame.token_text.length ? frame.token_text : "-";
    state.note_count = frame.notes.length;
    if (frame.tonality) {
        state.tonality = frame.tonality.name.length ? frame.tonality.name : "-";
    }
    state.last_frame_json = JSON.stringify(frame);
    publish("sequence", state.sequence);
    publish("token_text", state.token_text);
    publish("note_count", state.note_count);
    publish("tonality", state.tonality);
    publish("last_frame_json", state.last_frame_json);

    if (!frame.notes.length || state.mute) {
        return;
    }

    var audible = frame.notes.slice(0);
    audible.sort(function (a, b) {
        return b.activation - a.activation;
    });
    audible = audible.slice(0, MAX_VOICES);

    var maxActivation = 0.0;
    var i;
    for (i = 0; i < audible.length; i += 1) {
        maxActivation = Math.max(maxActivation, Math.max(0.0, audible[i].activation));
    }
    if (maxActivation <= 0.0) {
        return;
    }

    var duration = timedDurationMs();
    for (i = 0; i < audible.length; i += 1) {
        var note = audible[i];
        var normalized = Math.max(0.0, note.activation) / maxActivation;
        var previewGain = 0.20 * Math.sqrt(normalized) / Math.sqrt(audible.length);
        previewGain = clamp(previewGain, 0.0, 0.12);
        outlet(0, "target", i + 1);
        if (state.mode === "sustain") {
            outlet(0, "sustain", note.frequency_hz, previewGain);
        } else {
            outlet(0, "note", note.frequency_hz, previewGain, duration);
        }
    }
}

function timedDurationMs() {
    var bpm = Math.max(1, state.bpm);
    return Math.round(clamp((60000.0 / bpm) * 0.9, 60.0, 2000.0));
}

function releaseAll(reason) {
    outlet(0, "target", 0);
    outlet(0, "off");
    state.release_count += 1;
    state.last_release_reason = reason;
    publish("release_count", state.release_count);
    publish("last_release_reason", state.last_release_reason);
}

function getOrCreateFrame(runId, sequence, warning) {
    var key = frameKey(runId, sequence);
    if (!frames[key]) {
        frames[key] = {
            run_id: runId,
            sequence: sequence,
            token_id: -1,
            token_text: "",
            elapsed_ms: 0,
            notes: [],
            tonality: null
        };
        rememberFrameKey(key);
        setError(warning + ": " + runId + "/" + sequence);
    }
    return frames[key];
}

function rememberFrameKey(key) {
    if (frameOrder.indexOf(key) < 0) {
        frameOrder.push(key);
    }
    while (frameOrder.length > MAX_PENDING_FRAMES) {
        var stale = frameOrder.shift();
        delete frames[stale];
        setError("discarded oldest incomplete token frame");
    }
}

function forgetFrameKey(key) {
    var index = frameOrder.indexOf(key);
    if (index >= 0) {
        frameOrder.splice(index, 1);
    }
}

function frameKey(runId, sequence) {
    return JSON.stringify([String(runId), Number(sequence)]);
}

function validRun(runId) {
    if (runId === null) {
        return false;
    }
    if (state.run_id !== "-" && String(runId) !== String(state.run_id)) {
        setError("run ID mismatch: active " + state.run_id + ", received " + runId);
        return false;
    }
    return true;
}

function markReceiving() {
    if (state.state !== "receiving") {
        state.state = "receiving";
        publish("state", state.state);
    }
}

function emitSnapshot() {
    var names = [
        "port", "master_gain", "mute", "state", "run_state", "run_id",
        "sequence", "token_text", "note_count", "tonality", "bpm", "mode",
        "loop", "tonality_enabled", "prompt_influence", "pitch_bias",
        "last_frequency", "last_activation", "last_feature", "last_cluster",
        "last_instrument", "last_error", "unknown_count", "release_count",
        "last_release_reason", "last_frame_json"
    ];
    var i;
    for (i = 0; i < names.length; i += 1) {
        publish(names[i], state[names[i]]);
    }
}

function publish(name, value) {
    if (typeof value === "string" && value.length === 0) {
        value = "-";
    }
    outlet(1, name, value);
}

function setError(message) {
    state.last_error = String(message);
    publish("last_error", state.last_error);
}

function requireArgs(address, args, count) {
    if (args.length < count) {
        setError(address + " expected " + count + " args, received " + args.length);
        return false;
    }
    return true;
}

function isAddress(value) {
    return typeof value === "string" && value.charAt(0) === "/";
}

function nonEmptyString(value) {
    if (value === null || value === undefined) {
        return null;
    }
    var result = String(value);
    return result.length ? result : null;
}

function finiteValue(value) {
    var result = Number(value);
    return isFinite(result) ? result : null;
}

function integerValue(value) {
    var result = finiteValue(value);
    if (result === null) {
        return null;
    }
    return Math.round(result);
}

function booleanInt(value) {
    if (typeof value === "string") {
        var normalized = value.toLowerCase();
        if (normalized === "false" || normalized === "off" || normalized === "0") {
            return 0;
        }
    }
    return Number(value) ? 1 : 0;
}

function clamp(value, minimum, maximum) {
    return Math.max(minimum, Math.min(maximum, value));
}
