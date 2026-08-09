"use strict";

// ── WebAudioEngine ─────────────────────────────────────────────────────────
class WebAudioEngine {
  constructor() {
    this._audioCtx   = null;
    this._masterGain = null;
    this._voiceBus   = null;
    this._filter     = null;
    this._panner     = null;
    this._delay      = null;
    this._delayWet   = null;
    this._delayFeedback = null;
    this._analyser   = null;
    this._waveData   = null;
    this._activeNodes = [];
  }

  resume() {
    if (!this._audioCtx) {
      this._audioCtx   = new AudioContext();
      this._masterGain = this._audioCtx.createGain();
      this._voiceBus   = this._audioCtx.createGain();
      this._filter     = this._audioCtx.createBiquadFilter();
      this._panner     = this._audioCtx.createStereoPanner();
      this._delay      = this._audioCtx.createDelay(1.0);
      this._delayWet   = this._audioCtx.createGain();
      this._delayFeedback = this._audioCtx.createGain();
      this._analyser   = this._audioCtx.createAnalyser();
      this._analyser.fftSize = 1024;
      this._waveData = new Float32Array(this._analyser.fftSize);
      this._masterGain.gain.value = 1.0;
      this._filter.type = "lowpass";
      this._filter.frequency.value = 16000;
      this._filter.Q.value = 0.1;
      this._delay.delayTime.value = 0.2;
      this._delayWet.gain.value = 0;
      this._delayFeedback.gain.value = 0.25;
      this._voiceBus.connect(this._filter);
      this._filter.connect(this._panner);
      this._panner.connect(this._masterGain);
      this._panner.connect(this._delay);
      this._delay.connect(this._delayWet);
      this._delayWet.connect(this._masterGain);
      this._delay.connect(this._delayFeedback);
      this._delayFeedback.connect(this._delay);
      this._masterGain.connect(this._analyser);
      this._analyser.connect(this._audioCtx.destination);
    }
    this._audioCtx.resume();
  }

  _buildNoteGraph(freq, amplitude, instrument, startTime, stopTime) {
    const actx  = this._audioCtx;
    const nodes = [];

    const makeOsc = (frequency, gainValue) => {
      const osc = actx.createOscillator();
      const g   = actx.createGain();
      osc.type            = "sine";
      osc.frequency.value = frequency;
      g.gain.value        = Math.max(gainValue, 0.0001);
      osc.connect(g);
      g.connect(this._voiceBus);
      osc.start(startTime);
      if (stopTime !== null) osc.stop(stopTime);
      nodes.push({ osc, gain: g });
      return g;
    };

    switch (instrument) {
      case "piano":
        makeOsc(freq,     amplitude);
        makeOsc(freq * 2, amplitude * 0.5);
        break;

      case "guitar":
        makeOsc(freq,     amplitude);
        makeOsc(freq * 2, amplitude * 0.3);
        makeOsc(freq * 3, amplitude * 0.2);
        break;

      case "bass":
        makeOsc(freq,     amplitude);
        makeOsc(freq / 2, amplitude * 0.6);
        break;

      case "strings":
        makeOsc(freq,     amplitude);
        makeOsc(freq + 2, amplitude);
        break;

      case "pad": {
        const g = makeOsc(freq, 0.0001);
        if (stopTime !== null) {
          const mid = (startTime + stopTime) / 2;
          g.gain.setValueAtTime(0.0001, startTime);
          g.gain.linearRampToValueAtTime(Math.max(amplitude, 0.0001), mid);
          g.gain.linearRampToValueAtTime(0.0001, stopTime);
        } else {
          g.gain.value = Math.max(amplitude, 0.0001);
        }
        break;
      }

      case "bell": {
        const bellPartials = [
          makeOsc(freq,     amplitude),
          makeOsc(freq * 2, amplitude * 0.4),
          makeOsc(freq * 5, amplitude * 0.2),
        ];
        if (stopTime !== null) {
          for (const g of bellPartials) {
            g.gain.setValueAtTime(g.gain.value, startTime);
            g.gain.exponentialRampToValueAtTime(0.0001, stopTime);
          }
        } else {
          for (const g of bellPartials) {
            g.gain.setValueAtTime(g.gain.value, startTime);
            g.gain.exponentialRampToValueAtTime(Math.max(g.gain.value * 0.1, 0.0001), startTime + 2);
          }
        }
        break;
      }

      case "flute":
        makeOsc(freq, amplitude);
        break;

      case "brass":
        makeOsc(freq,     amplitude);
        makeOsc(freq * 2, amplitude * 0.7);
        makeOsc(freq * 3, amplitude * 0.5);
        makeOsc(freq * 4, amplitude * 0.3);
        break;

      default:
        makeOsc(freq, amplitude);
    }

    return nodes;
  }

  playNotes(notes, mode, bpm, controls = {}) {
    if (!this._audioCtx || !notes.length) return;

    this.setMappedControls(controls);
    const density = Math.max(1, Math.round(controls["audio.note_density"] ?? notes.length));
    const audibleNotes = [...notes]
      .sort((a, b) => (b.amplitude ?? 0) - (a.amplitude ?? 0))
      .slice(0, density);
    if (!audibleNotes.length) return;

    const maxAmp = Math.max(...audibleNotes.map(n => n.amplitude ?? 0), 1);
    const durationScale = Math.max(0.05, controls["audio.duration"] ?? 1);
    const durationSec = mode === "timed" ? (60 / bpm) * durationScale : null;
    const startTime  = this._audioCtx.currentTime;
    const stopTime   = durationSec !== null ? startTime + durationSec : null;
    const pitchRatio = 2 ** ((controls["audio.pitch_semitones"] ?? 0) / 12);
    const voiceGain = Math.max(0, controls["audio.gain"] ?? 1);
    const timbreIndex = controls["audio.timbre"];
    const timbres = ["piano", "guitar", "bass", "strings", "pad", "bell", "flute", "brass"];

    if (mode === "sustain") this.stopAll();
    if (voiceGain <= 0) return;

    for (const note of audibleNotes) {
      const mappedInstrument = Number.isFinite(timbreIndex)
        ? timbres[Math.max(0, Math.min(timbres.length - 1, Math.round(timbreIndex)))]
        : (note.instrument ?? "default");
      const newNodes = this._buildNoteGraph(
        (note.freq ?? 440) * pitchRatio,
        ((note.amplitude ?? 0) / maxAmp) * voiceGain,
        mappedInstrument,
        startTime,
        stopTime
      );
      this._activeNodes.push(...newNodes);
    }
  }

  stopAll() {
    const t = this._audioCtx ? this._audioCtx.currentTime : 0;
    for (const { osc } of this._activeNodes) {
      try { osc.stop(t); } catch {}
    }
    this._activeNodes = [];
  }

  setVolume(v) {
    if (this._masterGain) this._masterGain.gain.value = v;
  }

  setMappedControls(controls = {}) {
    if (!this._audioCtx) return;
    const now = this._audioCtx.currentTime;
    const settle = now + 0.04;
    if (this._filter) {
      const cutoff = Math.max(80, Math.min(16000, controls["audio.filter_hz"] ?? 16000));
      const resonance = Math.max(0.1, Math.min(24, controls["audio.resonance"] ?? 0.1));
      this._filter.frequency.cancelScheduledValues(now);
      this._filter.frequency.linearRampToValueAtTime(cutoff, settle);
      this._filter.Q.linearRampToValueAtTime(resonance, settle);
    }
    if (this._panner) {
      const pan = Math.max(-1, Math.min(1, controls["audio.pan"] ?? 0));
      this._panner.pan.linearRampToValueAtTime(pan, settle);
    }
    if (this._delay) {
      const delayTime = Math.max(0.01, Math.min(1, controls["audio.delay_time"] ?? 0.2));
      this._delay.delayTime.linearRampToValueAtTime(delayTime, settle);
    }
    if (this._delayWet) {
      const mix = Math.max(0, Math.min(0.75, controls["audio.delay_mix"] ?? 0));
      this._delayWet.gain.linearRampToValueAtTime(mix, settle);
    }
  }

  getWaveform() {
    if (!this._analyser || !this._waveData) return null;
    this._analyser.getFloatTimeDomainData(this._waveData);
    return this._waveData;
  }
}

// ── State ──────────────────────────────────────────────────────────────────
const engine = new WebAudioEngine();
let ws = null;
let isRunning = false;
let tokenCount = 0;
let catalogue = {};        // modelId -> { layers: [...], widths: [...] }
let strategyDescs = {};    // value -> description
let modeDescs = {};        // value -> description
let tonalityCatalogue = []; // default artist tonalities from server
let defaultTonalityCatalogue = [];
let lastRenderedNotes = [];
let lensUpdateTimer = null;
let oscUpdateTimer = null;
let mappingUpdateTimer = null;
let mappingCatalogue = { signals: [], targets: [], curves: [], default_mappings: [] };
let emitterMappings = [];
let defaultEmitterMappings = [];
let emitterSignalCatalogue = [];
let defaultEmitterSignalKeys = [];
let selectedEmitterSignalKeys = new Set();
let signalCatalogueKindFilter = "all";
let currentEmitterSignals = {};
let currentEmitterStreams = {};
let currentEmitterControls = {};
let currentMappingDiagnostics = [];
let currentVisualControls = {};
let featureCatalogue = new Map();
let pinnedFeatures = new Set();
let mutedFeatures = new Set();
let soloFeatures = new Set();
let instrumentScenes = [];
let activeWorkspace = "model";
let expandedLensIndex = 0;
let currentLayerProfile = [];
let lastCapturedObservationLayer = null;
const WORKBENCH_SIGNAL_KEYS = ["model.layer_profile", "model.residual.vector", "sae.active_features"];

// Transport / history state
let isPaused = false;
let tokenHistory = [];   // all token events received since last start
let historyIndex = -1;   // index into tokenHistory currently shown; -1 = none
let pendingBuffer = [];  // tokens received while paused, not yet played
let isDone = false;      // generation finished (but session not stopped)
let sessionActive = false; // server task remains active while done/looping/idle

// Cluster viz state
let cvPalette = [];       // [{cluster_id, name, color}] ordered by PCA

// ── Local storage ──────────────────────────────────────────────────────────
const STORAGE_KEY = "sae_ui_params";
const INSTRUMENT_STORAGE_KEY = "sae_emitter_instrument_v1";
const SCENE_STORAGE_KEY = "sae_emitter_scenes_v1";

function saveParams() {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(collectParams())); } catch {}
}

function loadSavedParams() {
  try { const raw = localStorage.getItem(STORAGE_KEY); return raw ? JSON.parse(raw) : null; } catch { return null; }
}

function saveInstrumentState() {
  const payload = {
    pinned: [...pinnedFeatures],
    muted: [...mutedFeatures],
    solo: [...soloFeatures],
  };
  try { localStorage.setItem(INSTRUMENT_STORAGE_KEY, JSON.stringify(payload)); } catch {}
}

function loadInstrumentState() {
  try {
    const raw = JSON.parse(localStorage.getItem(INSTRUMENT_STORAGE_KEY) || "{}");
    pinnedFeatures = new Set((raw.pinned || []).map(Number));
    mutedFeatures = new Set((raw.muted || []).map(Number));
    soloFeatures = new Set((raw.solo || []).map(Number));
  } catch {}
}

function saveScenes() {
  try { localStorage.setItem(SCENE_STORAGE_KEY, JSON.stringify(instrumentScenes)); } catch {}
}

function loadScenes() {
  try {
    const value = JSON.parse(localStorage.getItem(SCENE_STORAGE_KEY) || "[]");
    instrumentScenes = Array.isArray(value) ? value : [];
  } catch {
    instrumentScenes = [];
  }
}

// ── DOM refs ───────────────────────────────────────────────────────────────
const prompt          = document.getElementById("prompt");
const btnSend         = document.getElementById("btn-send");
const btnPrev         = document.getElementById("btn-prev");
const btnPlay         = document.getElementById("btn-play");
const btnPause        = document.getElementById("btn-pause");
const btnStop         = document.getElementById("btn-stop");
const btnNext         = document.getElementById("btn-next");
const statusEl        = document.getElementById("status");
const statusText      = document.getElementById("status-text");
const loopCountEl     = document.getElementById("loop-count-display");
const loadingPanel    = document.getElementById("loading-panel");
const loadingTitle    = document.getElementById("loading-title");
const loadingPercent  = document.getElementById("loading-percent");
const loadingProgress = document.getElementById("loading-progress");
const loadingDetail   = document.getElementById("loading-detail");
const modelSel        = document.getElementById("model");
const layerSel        = document.getElementById("layer");
const widthSel        = document.getElementById("width");
const strategySel     = document.getElementById("strategy");
const strategyHelp    = document.getElementById("strategy-help");
const clustersGroup   = document.getElementById("clusters-group");
const clustersIn      = document.getElementById("clusters");
const maxTokensIn     = document.getElementById("max-tokens");
const modeSel         = document.getElementById("mode");
const modeHelp        = document.getElementById("mode-help");
const bpmGroup        = document.getElementById("bpm-group");
const bpmIn           = document.getElementById("bpm");
const loopCb          = document.getElementById("loop");
const oscEnabledCb    = document.getElementById("osc-enabled");
const oscControls     = document.getElementById("osc-controls");
const oscHostIn       = document.getElementById("osc-host");
const oscPortIn       = document.getElementById("osc-port");
const oscMaxNotesIn   = document.getElementById("osc-max-notes");
const oscStatus       = document.getElementById("osc-status");
const oscSummaryState = document.getElementById("osc-summary-state");
const controlDrawer = document.getElementById("control-drawer");
const tonalityDrawer = document.getElementById("tonality-drawer");
const drawerBackdrop = document.getElementById("drawer-backdrop");
const btnControlsToggle = document.getElementById("btn-controls-toggle");
const btnControlsClose = document.getElementById("btn-controls-close");
const btnTonalityToggle = document.getElementById("btn-tonality-toggle");
const btnTonalityClose = document.getElementById("btn-tonality-close");
const volumeIn        = document.getElementById("volume");
const volumeValue     = document.getElementById("volume-value");
const tonalityEnabledCb = document.getElementById("tonality-enabled");
const tonalityControls = document.getElementById("tonality-controls");
const promptInfluenceIn = document.getElementById("prompt-influence");
const promptInfluenceValue = document.getElementById("prompt-influence-value");
const tonalityPitchBiasIn = document.getElementById("tonality-pitch-bias");
const tonalityPitchBiasValue = document.getElementById("tonality-pitch-bias-value");
const btnRawSound = document.getElementById("btn-raw-sound");
const btnInterpretedSound = document.getElementById("btn-interpreted-sound");
const btnAddLens = document.getElementById("btn-add-lens");
const btnResetLenses = document.getElementById("btn-reset-lenses");
const tonalityLensList = document.getElementById("tonality-lens-list");
const tonalityState = document.getElementById("tonality-state");
const tonalityPrimary = document.getElementById("tonality-primary");
const tonalityDescription = document.getElementById("tonality-description");
const tonalityBars = document.getElementById("tonality-bars");
const tonalityIntervals = document.getElementById("tonality-intervals");
const tonalityMemory = document.getElementById("tonality-memory");
const tonalityEvidence = document.getElementById("tonality-evidence");
const waveCanvas = document.getElementById("wave-canvas");
const lensEmbeddingStatus = document.getElementById("lens-embedding-status");
const mappingList = document.getElementById("mapping-list");
const mappingCount = document.getElementById("mapping-count");
const mappingTemplate = document.getElementById("mapping-template");
const btnApplyTemplate = document.getElementById("btn-apply-template");
const btnAddMapping = document.getElementById("btn-add-mapping");
const btnResetMappings = document.getElementById("btn-reset-mappings");
const btnClearMappings = document.getElementById("btn-clear-mappings");
const sceneName = document.getElementById("scene-name");
const sceneSelect = document.getElementById("scene-select");
const sceneA = document.getElementById("scene-a");
const sceneB = document.getElementById("scene-b");
const sceneMorph = document.getElementById("scene-morph");
const sceneMorphValue = document.getElementById("scene-morph-value");
const btnSaveScene = document.getElementById("btn-save-scene");
const btnLoadScene = document.getElementById("btn-load-scene");
const btnDeleteScene = document.getElementById("btn-delete-scene");
const signalToken = document.getElementById("signal-token");
const signalMonitor = document.getElementById("signal-monitor");
const controlCount = document.getElementById("control-count");
const controlMonitor = document.getElementById("control-monitor");
const featureCount = document.getElementById("feature-count");
const featureSearch = document.getElementById("feature-search");
const featureBrowser = document.getElementById("feature-browser");
const signalCatalogueSearch = document.getElementById("signal-catalogue-search");
const signalCatalogueList = document.getElementById("signal-catalogue-list");
const signalActiveCount = document.getElementById("signal-active-count");
const signalLocalRouteCount = document.getElementById("signal-local-route-count");
const signalMappingRouteCount = document.getElementById("signal-mapping-route-count");
const btnDefaultSignals = document.getElementById("btn-default-signals");
const btnClearSignals = document.getElementById("btn-clear-signals");
const visualProofPanel = document.getElementById("visual-proof-panel");
const observationLayerIn = document.getElementById("observation-layer");
const observationLayerValue = document.getElementById("observation-layer-value");
const contextToken = document.getElementById("context-token");
const contextLocation = document.getElementById("context-location");
const workspaceKicker = document.getElementById("workspace-kicker");
const workspaceTitle = document.getElementById("workspace-title");
const workspaceDescription = document.getElementById("workspace-description");
const modelAnatomy = document.getElementById("model-anatomy");
const atlasModel = document.getElementById("atlas-model");
const atlasToken = document.getElementById("atlas-token");
const atlasProbe = document.getElementById("atlas-probe");
const anatomyLayerCount = document.getElementById("anatomy-layer-count");
const anatomyLocation = document.getElementById("anatomy-location");
const gemmaActivityPlot = document.getElementById("gemma-activity-plot");
const modelLayerReadout = document.getElementById("model-layer-readout");
const btnLayerPrev = document.getElementById("btn-layer-prev");
const btnLayerNext = document.getElementById("btn-layer-next");
const layerBrowserPosition = document.getElementById("layer-browser-position");
const gemmaBlockNumber = document.getElementById("gemma-block-number");
const layerAttentionType = document.getElementById("layer-attention-type");
const gemmaAttentionSummary = document.getElementById("gemma-attention-summary");
const gemmaAttentionOperation = document.getElementById("gemma-attention-operation");
const gemmaMlpSummary = document.getElementById("gemma-mlp-summary");
const layerProfileMetrics = document.getElementById("layer-profile-metrics");
const denseStateCanvas = document.getElementById("dense-state-canvas");
const denseStateShape = document.getElementById("dense-state-shape");
const denseStateSummary = document.getElementById("dense-state-summary");
const denseStateStats = document.getElementById("dense-state-stats");
const sparseStateCanvas = document.getElementById("sparse-state-canvas");
const sparseStateCount = document.getElementById("sparse-state-count");
const sparseStateSummary = document.getElementById("sparse-state-summary");
const sparseStateTop = document.getElementById("sparse-state-top");

const WORKSPACE_COPY = {
  model: {
    kicker: "Gemma location",
    title: "Model and run",
    description: "Choose where data is observed in the current Gemma model.",
  },
  signals: {
    kicker: "Gemma data",
    title: "Map",
    description: "Choose what is extracted, inspected, and mapped.",
  },
};

function setInterfaceDrawer(drawerName, isOpen) {
  const controlsOpen = drawerName === "controls" && isOpen;
  const tonalityOpen = drawerName === "tonality" && isOpen;
  controlDrawer.classList.toggle("is-open", controlsOpen);
  controlDrawer.setAttribute("aria-hidden", String(!controlsOpen));
  tonalityDrawer.classList.toggle("is-open", tonalityOpen);
  tonalityDrawer.setAttribute("aria-hidden", String(!tonalityOpen));
  btnControlsToggle.setAttribute("aria-expanded", String(controlsOpen));
  btnTonalityToggle.setAttribute("aria-expanded", String(tonalityOpen));
  drawerBackdrop.hidden = !(controlsOpen || tonalityOpen);
  if (tonalityOpen) renderLensEditor();
}

function setWorkspace(workspace) {
  if (!WORKSPACE_COPY[workspace]) return;
  setInterfaceDrawer(null, false);
  activeWorkspace = workspace;
  document.querySelector(".visuals")?.scrollTo({ top: 0, behavior: "instant" });
  for (const tab of document.querySelectorAll("[data-workspace-tab]")) {
    tab.classList.toggle("active", tab.dataset.workspaceTab === workspace);
  }
  for (const page of document.querySelectorAll("[data-workspace-control]")) {
    page.classList.toggle("hidden", page.dataset.workspaceControl !== workspace);
  }
  for (const panel of document.querySelectorAll("[data-workspace-panel]")) {
    panel.classList.toggle("hidden", panel.dataset.workspacePanel !== workspace);
  }
  const copy = WORKSPACE_COPY[workspace];
  workspaceKicker.textContent = copy.kicker;
  workspaceTitle.textContent = copy.title;
  workspaceDescription.textContent = copy.description;
  if (workspace === "model") renderModelAnatomy();
}

function safeObservationLayer(value, availableLayers, fallback = 0) {
  const layers = (availableLayers || []).map(Number).filter(Number.isFinite);
  if (!layers.length) return Number.isFinite(Number(fallback)) ? Number(fallback) : 0;
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return layers.includes(Number(fallback)) ? Number(fallback) : layers[0];
  }
  return layers.reduce((closest, layer) => (
    Math.abs(layer - numeric) < Math.abs(closest - numeric) ? layer : closest
  ), layers[0]);
}

function layerProfileEntry(profile, layer) {
  return (profile || []).find(entry => Number(entry?.layer) === Number(layer)) || null;
}

function normalizedLayerActivity(entry, profile) {
  const value = Number(entry?.delta_rms);
  if (!Number.isFinite(value) || value < 0) return 0;
  const maximum = Math.max(
    0,
    ...(profile || []).map(item => Number(item?.delta_rms)).filter(Number.isFinite),
  );
  return maximum > 0 ? Math.min(1, value / maximum) : 0;
}

function layerProfilePoints(profile, width = 1000, height = 150) {
  const entries = (profile || []).map(entry => ({
    layer: Number(entry?.layer),
    value: Math.max(0, Number(entry?.delta_rms) || 0),
  })).filter(entry => Number.isFinite(entry.layer));
  if (!entries.length) return [];
  const maximumLayer = Math.max(1, ...entries.map(entry => entry.layer));
  const maximumValue = Math.max(0, ...entries.map(entry => entry.value));
  return entries.map(entry => ({
    layer: entry.layer,
    x: (entry.layer / maximumLayer) * width,
    y: maximumValue > 0 ? height - ((entry.value / maximumValue) * height) : height,
    value: entry.value,
  }));
}

function stepObservationLayer(current, direction, availableLayers) {
  const layers = (availableLayers || []).map(Number).filter(Number.isFinite).sort((a, b) => a - b);
  if (!layers.length) return Number(current) || 0;
  const selected = safeObservationLayer(current, layers, layers[0]);
  const index = Math.max(0, layers.indexOf(selected));
  return layers[Math.min(layers.length - 1, Math.max(0, index + Math.sign(Number(direction) || 0)))];
}

function currentModelInfo() {
  return catalogue[modelSel.value] || {
    layers: [],
    widths: [],
    observation_layers: [],
    architecture: {},
  };
}

function populateObservationLayer(modelId, preferredValue = observationLayerIn.value) {
  const info = catalogue[modelId] || {};
  const architectureCount = Number(info.architecture?.layer_count || 0);
  const available = info.observation_layers?.length
    ? info.observation_layers.map(Number)
    : Array.from({ length: architectureCount }, (_item, index) => index);
  if (!available.length) return;
  observationLayerIn.min = String(Math.min(...available));
  observationLayerIn.max = String(Math.max(...available));
  observationLayerIn.value = String(safeObservationLayer(preferredValue, available, layerSel.value));
  updateObservationLayer(false);
}

function updateObservationLayer(sendLive = true) {
  const info = currentModelInfo();
  const available = info.observation_layers || [];
  const selected = safeObservationLayer(observationLayerIn.value, available, layerSel.value);
  observationLayerIn.value = String(selected);
  const lastLayer = available.length ? Math.max(...available.map(Number)) : selected;
  observationLayerValue.textContent = `${selected} / ${lastLayer}`;
  contextLocation.textContent = `Dense L${selected} · SAE L${layerSel.value || "—"}`;
  if (anatomyLocation) {
    anatomyLocation.textContent = `Block ${selected} residual → dense probes · Block ${layerSel.value || "—"} residual → ${widthSel.value || "—"} SAE`;
  }
  renderModelAnatomy();
  renderGemmaBlock(selected);
  if (sendLive) {
    sendParamUpdate({ observation_layer: selected });
    saveParams();
  }
}

function selectObservationLayer(layer, sendLive = true) {
  observationLayerIn.value = String(layer);
  updateObservationLayer(sendLive);
}

function humanAttentionType(value) {
  const type = String(value || "unknown");
  if (type.includes("sliding")) return "Local sliding attention";
  if (type.includes("full")) return "Global full attention";
  return type === "unknown" ? "Attention type unavailable" : type.replaceAll("_", " ");
}

function renderGemmaBlock(observedLayer = Number(observationLayerIn.value)) {
  const info = currentModelInfo();
  const architecture = info.architecture || {};
  const layers = info.observation_layers || [];
  const selected = safeObservationLayer(observedLayer, layers, layerSel.value);
  const lastLayer = layers.length ? Math.max(...layers.map(Number)) : selected;
  const attentionType = architecture.layer_types?.[selected] || "unknown";
  const profileEntry = layerProfileEntry(currentLayerProfile, selected);
  const hiddenSize = Number(architecture.hidden_size) || "—";
  const intermediateSize = Number(architecture.intermediate_size) || "—";
  const attentionHeads = Number(architecture.attention_heads) || "—";
  const keyValueHeads = Number(architecture.key_value_heads) || "—";
  const headDimension = Number(architecture.head_dim) || "—";

  layerBrowserPosition.textContent = `L${selected} / ${lastLayer}`;
  modelLayerReadout.textContent = `Residual after block ${selected} · SAE fixed at block ${layerSel.value || "—"}`;
  btnLayerPrev.disabled = selected <= Math.min(...layers.map(Number));
  btnLayerNext.disabled = selected >= lastLayer;
  gemmaBlockNumber.textContent = `Transformer block ${selected}`;
  layerAttentionType.textContent = humanAttentionType(attentionType);
  gemmaAttentionSummary.textContent = `${attentionHeads} query heads · ${keyValueHeads} KV head${keyValueHeads === 1 ? "" : "s"} · ${headDimension}d/head`;
  gemmaAttentionOperation.textContent = attentionType.includes("sliding")
    ? `Q · K · V · O → post RMSNorm · ${architecture.sliding_window || "—"}-token window`
    : "Q · K · V · O → post RMSNorm · full context";
  gemmaMlpSummary.textContent = `GELU(gate) × up → down → post RMSNorm · ${hiddenSize} → ${intermediateSize} → ${hiddenSize}`;
  layerProfileMetrics.innerHTML = "";

  if (!profileEntry) {
    const waiting = document.createElement("span");
    waiting.className = "profile-waiting";
    waiting.textContent = "Run a prompt to measure this token across every transformer block.";
    layerProfileMetrics.appendChild(waiting);
    return;
  }
  const metricEntries = [
    ["residual RMS", profileEntry.rms],
    ["peak |x|", profileEntry.max_abs],
    ["update RMS", profileEntry.delta_rms],
    ["similarity to L−1", profileEntry.cosine_to_previous],
  ];
  for (const [label, value] of metricEntries) {
    const item = document.createElement("span");
    const small = document.createElement("small");
    const strong = document.createElement("strong");
    small.textContent = label;
    strong.textContent = value === null || value === undefined ? "input boundary" : formatSignalValue(value);
    item.append(small, strong);
    layerProfileMetrics.appendChild(item);
  }
}

function renderModelActivityPlot(profile = currentLayerProfile) {
  if (!gemmaActivityPlot) return;
  const points = layerProfilePoints(profile, 1000, 112);
  if (!points.length) {
    gemmaActivityPlot.innerHTML = '<path class="model-baseline" d="M0 112 L1000 112"></path><text x="500" y="58" text-anchor="middle">run a prompt to trace residual updates</text>';
    return;
  }
  const pointText = points.map(point => `${point.x.toFixed(2)},${point.y.toFixed(2)}`).join(" ");
  const areaText = `0,112 ${pointText} 1000,112`;
  gemmaActivityPlot.innerHTML = `
    <polyline class="model-activity-area" points="${areaText}"></polyline>
    <polyline class="model-activity-line" points="${pointText}"></polyline>
  `;
}

function renderModelAnatomy(observedLayer = Number(observationLayerIn.value)) {
  if (!modelAnatomy) return;
  const info = currentModelInfo();
  const layers = info.observation_layers || [];
  const saeLayer = Number(layerSel.value);
  const selected = safeObservationLayer(observedLayer, layers, saeLayer);
  modelAnatomy.innerHTML = "";
  for (const layer of layers) {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.layer = String(layer);
    button.className = "anatomy-layer";
    button.classList.toggle("is-observed", Number(layer) === selected);
    button.classList.toggle("has-sae", Number(layer) === saeLayer);
    const profileEntry = layerProfileEntry(currentLayerProfile, layer);
    const activity = normalizedLayerActivity(profileEntry, currentLayerProfile);
    button.style.setProperty("--layer-activity", String(activity));
    button.title = Number(layer) === saeLayer
      ? `Transformer block ${layer} · dense residual available · SAE attached`
      : `Transformer block ${layer} · dense residual available`;
    const label = document.createElement("span");
    label.textContent = `L${String(layer).padStart(2, "0")}`;
    const attention = document.createElement("small");
    const attentionType = String(info.architecture?.layer_types?.[Number(layer)] || "unknown");
    button.classList.toggle("is-global", attentionType.includes("full"));
    attention.textContent = attentionType.includes("full")
      ? "global"
      : (attentionType.includes("sliding") ? "local" : "unknown");
    const activityBar = document.createElement("b");
    activityBar.className = "layer-activity";
    const sites = document.createElement("span");
    sites.className = "layer-sites";
    if (Number(layer) === selected) {
      const probe = document.createElement("i");
      probe.className = "probe-dot";
      sites.appendChild(probe);
    }
    if (Number(layer) === saeLayer) {
      const sae = document.createElement("i");
      sae.className = "sae-dot";
      sites.appendChild(sae);
    }
    button.append(activityBar, label, attention, sites);
    button.addEventListener("click", () => {
      selectObservationLayer(layer, true);
    });
    modelAnatomy.appendChild(button);
  }
  const architecture = info.architecture || {};
  anatomyLayerCount.textContent = `${architecture.layer_count || layers.length || "—"} blocks`;
  atlasModel.textContent = architecture.label || modelSel.value || "model —";
  renderModelActivityPlot();
  renderGemmaBlock(selected);
}

function residualVectorStats(values) {
  const finite = (values || []).map(Number).filter(Number.isFinite);
  if (!finite.length) return { count: 0, minimum: 0, maximum: 0, maxAbs: 0, rms: 0 };
  const minimum = Math.min(...finite);
  const maximum = Math.max(...finite);
  return {
    count: finite.length,
    minimum,
    maximum,
    maxAbs: Math.max(Math.abs(minimum), Math.abs(maximum)),
    rms: Math.sqrt(finite.reduce((sum, value) => sum + (value * value), 0) / finite.length),
  };
}

function prepareDataCanvas(canvas) {
  if (!canvas) return null;
  const width = Math.max(1, Math.floor(canvas.offsetWidth || 640));
  const height = Math.max(1, Math.floor(canvas.offsetHeight || 280));
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d");
  context.clearRect(0, 0, width, height);
  context.fillStyle = "#101415";
  context.fillRect(0, 0, width, height);
  return { context, width, height };
}

function renderDenseState(stream = currentEmitterStreams["model.residual.vector"]) {
  const values = stream?.value?.values || [];
  const canvas = prepareDataCanvas(denseStateCanvas);
  if (!canvas || !values.length) {
    denseStateShape.textContent = "waiting";
    denseStateSummary.textContent = "dense waiting";
    denseStateStats.classList.add("is-empty");
    denseStateStats.textContent = "Enable the residual vector probe and start a run to receive coordinates.";
    return;
  }
  const stats = residualVectorStats(values);
  const centerY = canvas.height / 2;
  canvas.context.strokeStyle = "rgba(255,255,255,0.12)";
  canvas.context.lineWidth = 1;
  canvas.context.beginPath();
  canvas.context.moveTo(0, centerY);
  canvas.context.lineTo(canvas.width, centerY);
  canvas.context.stroke();
  canvas.context.strokeStyle = "rgba(79, 214, 197, 0.92)";
  canvas.context.lineWidth = 1.25;
  canvas.context.beginPath();
  values.forEach((rawValue, index) => {
    const x = values.length > 1 ? (index / (values.length - 1)) * canvas.width : canvas.width / 2;
    const normalized = stats.maxAbs ? (Number(rawValue) || 0) / stats.maxAbs : 0;
    const y = centerY - (normalized * (canvas.height * 0.43));
    if (index === 0) canvas.context.moveTo(x, y);
    else canvas.context.lineTo(x, y);
  });
  canvas.context.stroke();
  const captured = Number.isFinite(Number(lastCapturedObservationLayer))
    ? `captured L${lastCapturedObservationLayer} · `
    : "";
  denseStateShape.textContent = `${captured}${stats.count.toLocaleString()} dimensions`;
  denseStateSummary.textContent = `dense ${stats.count.toLocaleString()}`;
  denseStateStats.classList.remove("is-empty");
  denseStateStats.innerHTML = "";
  for (const [label, value] of [
    ["minimum", stats.minimum],
    ["maximum", stats.maximum],
    ["RMS", stats.rms],
    ["peak |x|", stats.maxAbs],
  ]) {
    const item = document.createElement("span");
    item.innerHTML = `<small>${label}</small><strong>${formatSignalValue(value)}</strong>`;
    denseStateStats.appendChild(item);
  }
}

function renderSparseState(stream = currentEmitterStreams["sae.active_features"]) {
  const features = Array.isArray(stream?.value) ? stream.value : [];
  const canvas = prepareDataCanvas(sparseStateCanvas);
  sparseStateTop.innerHTML = "";
  if (!canvas || !features.length) {
    sparseStateCount.textContent = "waiting";
    sparseStateSummary.textContent = "sparse waiting";
    sparseStateTop.classList.add("empty-monitor");
    sparseStateTop.textContent = "Enable the sparse SAE probe and start a run to see active features.";
    return;
  }
  const widthMatch = String(widthSel.value || "65k").match(/[\d.]+/);
  const multiplier = String(widthSel.value || "").toLowerCase().includes("k") ? 1000 : 1;
  const coordinateCount = Math.max(1, Number(widthMatch?.[0] || 65) * multiplier);
  const maximum = Math.max(...features.map(item => Number(item.activation) || 0), 1e-9);
  canvas.context.fillStyle = "rgba(255,255,255,0.08)";
  canvas.context.fillRect(0, canvas.height - 1, canvas.width, 1);
  for (const feature of features) {
    const x = (Number(feature.index) / coordinateCount) * canvas.width;
    const height = Math.max(2, ((Number(feature.activation) || 0) / maximum) * (canvas.height - 12));
    canvas.context.fillStyle = "rgba(139, 111, 232, 0.82)";
    canvas.context.fillRect(Math.max(0, x - 1), canvas.height - height, 3, height);
  }
  sparseStateCount.textContent = `${features.length} / ${coordinateCount.toLocaleString()} active`;
  sparseStateSummary.textContent = `sparse ${features.length}`;
  sparseStateTop.classList.remove("empty-monitor");
  const strongest = [...features]
    .sort((left, right) => Number(right.activation) - Number(left.activation))
    .slice(0, 8);
  for (const feature of strongest) {
    const row = document.createElement("div");
    row.className = "sparse-top-row";
    const index = document.createElement("strong");
    index.textContent = `#${feature.index}`;
    const description = document.createElement("span");
    description.textContent = feature.description || "No Neuronpedia description in this scope";
    const activation = document.createElement("span");
    activation.textContent = formatSignalValue(feature.activation);
    row.append(index, description, activation);
    sparseStateTop.appendChild(row);
  }
}

function renderNeuralAtlas(msg) {
  const observation = msg?.observation || {};
  const observedLayer = Number.isFinite(Number(observation.layer))
    ? Number(observation.layer)
    : Number(observationLayerIn.value);
  const saeLayer = observation.sae_layer ?? layerSel.value;
  const profileStream = currentEmitterStreams["model.layer_profile"];
  currentLayerProfile = Array.isArray(profileStream?.value?.layers)
    ? profileStream.value.layers
    : currentLayerProfile;
  if (Number.isFinite(Number(observation.layer))) lastCapturedObservationLayer = Number(observation.layer);
  contextToken.textContent = msg?.token ? `Token ${tokenCount} · ${JSON.stringify(msg.token)}` : "No token yet";
  contextLocation.textContent = `Dense L${observedLayer} · SAE L${saeLayer}`;
  atlasToken.textContent = msg?.token ? `token · ${JSON.stringify(msg.token)}` : "token —";
  atlasProbe.textContent = `residual · layer ${observedLayer}`;
  anatomyLocation.textContent = `Block ${observedLayer} residual → dense probes · Block ${saeLayer} residual → ${observation.sae_width || widthSel.value} SAE`;
  renderModelAnatomy(observedLayer);
  renderDenseState();
  renderSparseState();
}

function ensureWorkbenchSignalSelection() {
  for (const key of WORKBENCH_SIGNAL_KEYS) {
    if (emitterSignalCatalogue.some(spec => spec.key === key)) selectedEmitterSignalKeys.add(key);
  }
}

// ── Load options + defaults ─────────────────────────────────────────────────
async function loadOptions() {
  loadInstrumentState();
  loadScenes();
  try {
    const res = await fetch("/api/config/model-options");
    const data = await res.json();

    catalogue = data.model_catalogue ?? {};

    // Populate model dropdown
    data.models.forEach(m => {
      const opt = document.createElement("option");
      opt.value = m;
      opt.textContent = m;
      modelSel.appendChild(opt);
    });

    // Populate layer/width based on first model
    if (modelSel.value) populateLayerWidth(modelSel.value);

    // Populate strategy dropdown
    data.strategies.forEach(s => {
      const opt = document.createElement("option");
      opt.value = s.value;
      opt.textContent = s.label;
      strategySel.appendChild(opt);
      strategyDescs[s.value] = s.description;
    });
    updateStrategyHelp();

    // Populate mode dropdown
    data.modes.forEach(m => {
      const opt = document.createElement("option");
      opt.value = m.value;
      opt.textContent = m.label;
      modeSel.appendChild(opt);
      modeDescs[m.value] = m.description;
    });
    updateModeHelp();

  } catch (e) {
    console.warn("Could not load model options", e);
  }

  try {
    const res = await fetch("/api/config/defaults");
    const d = await res.json();
    applyParams(d);
  } catch (e) {
    console.warn("Could not load defaults", e);
  }

  try {
    const res = await fetch("/api/config/emitter-mapping");
    mappingCatalogue = await res.json();
    defaultEmitterMappings = structuredClone(mappingCatalogue.default_mappings ?? []);
    if (!emitterMappings.length) emitterMappings = structuredClone(defaultEmitterMappings);
    renderMappingEditor();
    renderSceneSelectors();
  } catch (e) {
    console.warn("Could not load emitter mapping catalogue", e);
  }

  try {
    const res = await fetch("/api/config/emitter-signals");
    const data = await res.json();
    emitterSignalCatalogue = data.signals ?? [];
    defaultEmitterSignalKeys = data.default_active ?? [];
    if (!selectedEmitterSignalKeys.size) {
      selectedEmitterSignalKeys = new Set(defaultEmitterSignalKeys);
    }
    renderSignalExplorer();
  } catch (e) {
    console.warn("Could not load Emitter signal catalogue", e);
  }

  try {
    const res = await fetch("/api/config/tonalities");
    const data = await res.json();
    tonalityCatalogue = (data.tonalities ?? []).map(entry => ({ ...entry, enabled: true }));
    defaultTonalityCatalogue = structuredClone(tonalityCatalogue);
    renderLensEditor();
    renderTonalityIdle();
  } catch (e) {
    console.warn("Could not load tonalities", e);
  }

  const saved = loadSavedParams();
  if (saved) applyParams(saved);
  ensureWorkbenchSignalSelection();
  renderMappingEditor();
  renderSceneSelectors();
  renderFeatureBrowser();
  renderSignalExplorer();
  renderModelAnatomy();
  renderNeuralAtlas(null);
}

function populateLayerWidth(modelId) {
  const info = catalogue[modelId] ?? { layers: [], widths: [] };

  layerSel.innerHTML = "";
  info.layers.forEach(l => {
    const opt = document.createElement("option");
    opt.value = l;
    opt.textContent = l;
    layerSel.appendChild(opt);
  });

  widthSel.innerHTML = "";
  info.widths.forEach(w => {
    const opt = document.createElement("option");
    opt.value = w;
    opt.textContent = w;
    widthSel.appendChild(opt);
  });

  populateObservationLayer(modelId);
}

function intervalsToText(intervals) {
  if (Array.isArray(intervals)) return intervals.join(", ");
  return intervals ?? "";
}

function parseIntervals(text) {
  return String(text || "")
    .replace(/;/g, ",")
    .split(",")
    .map(part => parseFloat(part.trim()))
    .filter(value => Number.isFinite(value));
}

const TONAL_ROOTS = ["C", "C♯", "D", "E♭", "E", "F", "F♯", "G", "A♭", "A", "B♭", "B"];
const SCALE_PRESETS = {
  custom: null,
  major: [0, 2, 4, 5, 7, 9, 11],
  natural_minor: [0, 2, 3, 5, 7, 8, 10],
  dorian: [0, 2, 3, 5, 7, 9, 10],
  mixolydian: [0, 2, 4, 5, 7, 9, 10],
  major_pentatonic: [0, 2, 4, 7, 9],
  minor_pentatonic: [0, 3, 5, 7, 10],
  whole_tone: [0, 2, 4, 6, 8, 10],
  chromatic: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
};

function scalePresetForIntervals(intervals) {
  const signature = (intervals || []).map(Number).join(",");
  return Object.entries(SCALE_PRESETS).find(([_key, values]) => values?.join(",") === signature)?.[0] || "custom";
}

function normalizedLens(entry) {
  return {
    name: String(entry.name || "").trim(),
    description: String(entry.description || "").trim(),
    intervals: Array.isArray(entry.intervals)
      ? entry.intervals.map(value => Number(value)).filter(value => Number.isFinite(value))
      : parseIntervals(entry.intervals),
    enabled: entry.enabled !== false,
    root: ((Number(entry.root) || 0) % 12 + 12) % 12,
  };
}

function collectTonalityLenses() {
  return tonalityCatalogue
    .map(normalizedLens)
    .filter(entry => entry.name && entry.description);
}

function renderLensEditor() {
  if (!tonalityLensList) return;
  tonalityLensList.innerHTML = "";
  expandedLensIndex = Math.max(0, Math.min(expandedLensIndex, tonalityCatalogue.length - 1));

  tonalityCatalogue.forEach((entry, index) => {
    const lens = normalizedLens(entry);
    const item = document.createElement("details");
    item.className = "lens-editor-item";
    item.open = index === expandedLensIndex;

    const summary = document.createElement("summary");
    summary.className = "lens-editor-summary";
    const summaryName = document.createElement("strong");
    summaryName.textContent = lens.name || "Untitled lens";
    const summaryPitch = document.createElement("small");
    summaryPitch.textContent = `${TONAL_ROOTS[lens.root]} · ${intervalsToText(lens.intervals)}`;
    summary.append(summaryName, summaryPitch);
    item.addEventListener("toggle", () => {
      if (!item.open) return;
      expandedLensIndex = index;
      for (const sibling of tonalityLensList.children) {
        if (sibling !== item) sibling.open = false;
      }
    });

    const top = document.createElement("div");
    top.className = "lens-editor-top";

    const enabled = document.createElement("input");
    enabled.type = "checkbox";
    enabled.checked = lens.enabled;
    enabled.title = "Enable lens";
    enabled.addEventListener("change", () => {
      tonalityCatalogue[index].enabled = enabled.checked;
      item.classList.toggle("is-disabled", !enabled.checked);
      scheduleLensUpdate(0);
    });

    const name = document.createElement("input");
    name.type = "text";
    name.value = lens.name;
    name.placeholder = "lens name";
    name.title = "Lens name";
    name.addEventListener("input", () => {
      tonalityCatalogue[index].name = name.value;
      summaryName.textContent = name.value || "Untitled lens";
      scheduleLensUpdate();
    });

    const makeAction = (label, title, action) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "mini-icon-btn";
      button.textContent = label;
      button.title = title;
      button.addEventListener("click", action);
      return button;
    };
    const moveUp = makeAction("↑", "Move lens up", () => {
      if (index <= 0) return;
      [tonalityCatalogue[index - 1], tonalityCatalogue[index]] = [tonalityCatalogue[index], tonalityCatalogue[index - 1]];
      expandedLensIndex = index - 1;
      renderLensEditor();
      scheduleLensUpdate(0);
    });
    const moveDown = makeAction("↓", "Move lens down", () => {
      if (index >= tonalityCatalogue.length - 1) return;
      [tonalityCatalogue[index + 1], tonalityCatalogue[index]] = [tonalityCatalogue[index], tonalityCatalogue[index + 1]];
      expandedLensIndex = index + 1;
      renderLensEditor();
      scheduleLensUpdate(0);
    });
    const duplicate = makeAction("⧉", "Duplicate lens", () => {
      const copy = { ...normalizedLens(tonalityCatalogue[index]), name: `${lens.name} copy` };
      tonalityCatalogue.splice(index + 1, 0, copy);
      expandedLensIndex = index + 1;
      renderLensEditor();
      scheduleLensUpdate(0);
    });
    const remove = makeAction("×", "Remove lens", () => {
      tonalityCatalogue.splice(index, 1);
      expandedLensIndex = Math.min(index, tonalityCatalogue.length - 1);
      renderLensEditor();
      scheduleLensUpdate(0);
    });

    const description = document.createElement("textarea");
    description.value = lens.description;
    description.rows = 2;
    description.placeholder = "verbal description";
    description.title = "Verbal description";
    description.addEventListener("input", () => {
      tonalityCatalogue[index].description = description.value;
      scheduleLensUpdate();
    });

    const tonalControls = document.createElement("div");
    tonalControls.className = "lens-tonal-controls";

    const root = document.createElement("select");
    root.title = "Root key (C = pitch class 0)";
    for (const [pitchClass, label] of TONAL_ROOTS.entries()) {
      const option = document.createElement("option");
      option.value = String(pitchClass);
      option.textContent = `${label} root`;
      root.appendChild(option);
    }
    root.value = String(lens.root);
    root.addEventListener("change", () => {
      tonalityCatalogue[index].root = Number(root.value);
      summaryPitch.textContent = `${TONAL_ROOTS[Number(root.value)]} · ${intervalsToText(parseIntervals(intervals.value))}`;
      scheduleLensUpdate(0);
    });

    const preset = document.createElement("select");
    preset.title = "Conventional scale or custom interval set";
    for (const key of Object.keys(SCALE_PRESETS)) {
      const option = document.createElement("option");
      option.value = key;
      option.textContent = key === "custom" ? "Custom intervals" : key.replaceAll("_", " ");
      preset.appendChild(option);
    }
    preset.value = scalePresetForIntervals(lens.intervals);

    const intervals = document.createElement("input");
    intervals.type = "text";
    intervals.value = intervalsToText(lens.intervals);
    intervals.placeholder = "0, 2, 4, 7";
    intervals.title = "Intervals";
    intervals.addEventListener("input", () => {
      tonalityCatalogue[index].intervals = intervals.value;
      preset.value = scalePresetForIntervals(parseIntervals(intervals.value));
      summaryPitch.textContent = `${TONAL_ROOTS[Number(root.value)]} · ${intervalsToText(parseIntervals(intervals.value))}`;
      scheduleLensUpdate();
    });

    preset.addEventListener("change", () => {
      const presetIntervals = SCALE_PRESETS[preset.value];
      if (!presetIntervals) return;
      tonalityCatalogue[index].intervals = [...presetIntervals];
      intervals.value = intervalsToText(presetIntervals);
      summaryPitch.textContent = `${TONAL_ROOTS[Number(root.value)]} · ${intervalsToText(presetIntervals)}`;
      scheduleLensUpdate(0);
    });

    tonalControls.append(root, preset);

    item.classList.toggle("is-disabled", !lens.enabled);
    top.append(enabled, name, moveUp, moveDown, duplicate, remove);
    item.append(summary, top, description, tonalControls, intervals);
    tonalityLensList.appendChild(item);
  });
}

function scheduleLensUpdate(delayMs = 300) {
  saveParams();
  setLensEmbeddingStatus("queued", "embedding");
  if (lensUpdateTimer) clearTimeout(lensUpdateTimer);
  lensUpdateTimer = setTimeout(() => {
    const lenses = collectTonalityLenses();
    sendParamUpdate({ tonality_lenses: lenses });
    if (!sessionActive) setLensEmbeddingStatus("ready on play", "ready");
    if (!isRunning) renderTonalityIdle();
  }, delayMs);
}

function setLensEmbeddingStatus(message, state) {
  if (!lensEmbeddingStatus) return;
  lensEmbeddingStatus.textContent = message;
  lensEmbeddingStatus.dataset.state = state;
}

function updateStrategyHelp() {
  strategyHelp.dataset.tooltip = strategyDescs[strategySel.value] ?? "";
}

function updateModeHelp() {
  modeHelp.dataset.tooltip = modeDescs[modeSel.value] ?? "";
}

function applyParams(p) {
  if (p.prompt     !== undefined) prompt.value       = p.prompt;
  if (p.model      !== undefined) {
    modelSel.value = p.model;
    populateLayerWidth(p.model);
  }
  if (p.layer      !== undefined) layerSel.value     = p.layer;
  if (p.observation_layer !== undefined) observationLayerIn.value = p.observation_layer;
  if (p.width      !== undefined) widthSel.value     = p.width;
  if (p.strategy   !== undefined) { strategySel.value = p.strategy; updateStrategyHelp(); }
  if (p.clusters   !== undefined) clustersIn.value   = p.clusters;
  if (p.max_tokens !== undefined) maxTokensIn.value  = p.max_tokens;
  if (p.mode       !== undefined) { modeSel.value = p.mode; updateModeHelp(); }
  if (p.bpm        !== undefined) bpmIn.value        = p.bpm;
  if (p.loop       !== undefined) loopCb.checked     = p.loop;
  if (p.osc_enabled !== undefined) oscEnabledCb.checked = Boolean(p.osc_enabled);
  if (p.osc_host !== undefined) oscHostIn.value = p.osc_host;
  if (p.osc_port !== undefined) oscPortIn.value = p.osc_port;
  if (p.osc_max_notes_per_token !== undefined) oscMaxNotesIn.value = p.osc_max_notes_per_token;
  if (p.volume !== undefined) volumeIn.value = p.volume;
  if (p.tonality_enabled !== undefined) tonalityEnabledCb.checked = Boolean(p.tonality_enabled);
  if (p.prompt_influence !== undefined) promptInfluenceIn.value = p.prompt_influence;
  if (p.tonality_pitch_bias !== undefined) tonalityPitchBiasIn.value = p.tonality_pitch_bias;
  if (Array.isArray(p.tonality_lenses) && p.tonality_lenses.length) {
    tonalityCatalogue = p.tonality_lenses.map(normalizedLens);
    renderLensEditor();
    renderTonalityIdle();
  }
  if (Array.isArray(p.emitter_mappings)) {
    emitterMappings = structuredClone(p.emitter_mappings);
    renderMappingEditor();
  }
  if (Array.isArray(p.emitter_signal_keys)) {
    selectedEmitterSignalKeys = new Set(p.emitter_signal_keys.map(String));
    renderSignalExplorer();
  }

  // Sync conditional visibility
  if (p.strategy !== undefined) syncClustersVisibility();
  if (p.mode     !== undefined) syncBpmVisibility();
  syncOscControls();
  syncTonalityControls();
  updateTonalityControlValues();
  updateVolumeValue();
  updateObservationLayer(false);
}

// ── Collect current params ─────────────────────────────────────────────────
function collectParams() {
  return {
    prompt:     prompt.value,
    model:      modelSel.value,
    layer:      parseInt(layerSel.value),
    observation_layer: parseInt(observationLayerIn.value),
    width:      widthSel.value,
    strategy:   strategySel.value,
    clusters:   parseInt(clustersIn.value),
    max_tokens: parseInt(maxTokensIn.value),
    mode:       modeSel.value,
    bpm:        parseInt(bpmIn.value),
    loop:       loopCb.checked,
    osc_enabled: oscEnabledCb.checked,
    osc_host: oscHostIn.value.trim(),
    osc_port: boundedIntValue(oscPortIn, 9000, 1, 65535),
    osc_max_notes_per_token: boundedIntValue(oscMaxNotesIn, 32, 1, 128),
    volume: parseFloat(volumeIn.value),
    tonality_enabled: tonalityEnabledCb.checked,
    prompt_influence: parseFloat(promptInfluenceIn.value),
    tonality_pitch_bias: parseFloat(tonalityPitchBiasIn.value),
    tonality_lenses: collectTonalityLenses(),
    emitter_signal_keys: [...selectedEmitterSignalKeys],
    emitter_mappings: structuredClone(emitterMappings),
  };
}

// ── Conditional visibility ─────────────────────────────────────────────────
function syncClustersVisibility() {
  clustersGroup.classList.toggle("hidden", strategySel.value !== "cluster");
}

function syncBpmVisibility() {
  bpmGroup.classList.toggle("hidden", modeSel.value !== "timed");
}

function syncTonalityControls() {
  tonalityControls.classList.toggle("hidden", !tonalityEnabledCb.checked);
}

function boundedIntValue(input, fallback, minimum, maximum) {
  const value = parseInt(input.value);
  if (!Number.isFinite(value)) return fallback;
  return Math.max(minimum, Math.min(maximum, value));
}

function setOscStatus(message, state) {
  if (!oscStatus) return;
  oscStatus.textContent = message;
  oscStatus.dataset.state = state;
  if (oscSummaryState) {
    oscSummaryState.textContent = state === "ready" ? "on" : (state === "error" ? "error" : "off");
    oscSummaryState.dataset.state = state;
  }
}

function syncOscControls() {
  const enabled = oscEnabledCb.checked;
  oscControls.classList.toggle("hidden", !enabled);
  if (!enabled) {
    setOscStatus("OSC disabled", "disabled");
    return;
  }
  const host = oscHostIn.value.trim();
  if (!host) {
    setOscStatus("Enabled — enter a destination host/IP", "unconfigured");
    return;
  }
  const port = boundedIntValue(oscPortIn, 9000, 1, 65535);
  setOscStatus(`UDP target ${host}:${port} — delivery unconfirmed`, "ready");
}

function scheduleOscUpdate(delayMs = 250) {
  saveParams();
  if (oscUpdateTimer) clearTimeout(oscUpdateTimer);
  oscUpdateTimer = setTimeout(() => {
    sendParamUpdate({
      osc_enabled: oscEnabledCb.checked,
      osc_host: oscHostIn.value.trim(),
      osc_port: boundedIntValue(oscPortIn, 9000, 1, 65535),
      osc_max_notes_per_token: boundedIntValue(oscMaxNotesIn, 32, 1, 128),
    });
  }, delayMs);
}

function updateTonalityControlValues() {
  promptInfluenceValue.textContent = `${Math.round(parseFloat(promptInfluenceIn.value) * 100)}%`;
  tonalityPitchBiasValue.textContent = `${Math.round(parseFloat(tonalityPitchBiasIn.value) * 100)}%`;
}

function updateVolumeValue() {
  if (volumeValue) volumeValue.textContent = `${Math.round(parseFloat(volumeIn.value) * 100)}%`;
}

function setInterpretationBlend(value) {
  tonalityPitchBiasIn.value = String(value);
  updateTonalityControlValues();
  sendParamUpdate({ tonality_pitch_bias: parseFloat(tonalityPitchBiasIn.value) });
  saveParams();
}

// ── General Emitter Signal Explorer ───────────────────────────────────────
function filterSignalCatalogue(entries, query = "", kind = "all") {
  const needle = String(query || "").trim().toLowerCase();
  return entries.filter(entry => {
    if (kind !== "all" && entry.kind !== kind) return false;
    if (!needle) return true;
    return [
      entry.key,
      entry.label,
      entry.group,
      entry.location,
      entry.value_type,
      entry.description,
    ].some(value => String(value || "").toLowerCase().includes(needle));
  });
}

function signalRouteSummary(spec, selectedKeys, mappings) {
  return {
    active: selectedKeys.has(spec.key),
    mappingCount: mappings.filter(mapping => mapping.enabled !== false && mapping.source === spec.key).length,
    connector: "Not routed",
  };
}

function describeStreamValue(stream) {
  const value = stream?.value;
  if (stream?.value_type === "layer_profile") {
    const count = Number(value?.shape?.[0] ?? value?.layers?.length ?? 0);
    return `${count} transformer block${count === 1 ? "" : "s"}`;
  }
  if (stream?.value_type === "vector") {
    const length = Number(value?.shape?.[0] ?? value?.values?.length ?? 0);
    return `${length} ${value?.dtype || "numeric"} values`;
  }
  if (stream?.value_type === "sparse_vector") {
    const count = Array.isArray(value) ? value.length : 0;
    return `${count} active feature${count === 1 ? "" : "s"}`;
  }
  if (stream?.value_type === "structured") {
    const count = Array.isArray(value?.items) ? value.items.length : 0;
    return `${count} top-k entr${count === 1 ? "y" : "ies"}`;
  }
  if (Array.isArray(value)) return `${value.length} values`;
  if (value && typeof value === "object") return `${Object.keys(value).length} fields`;
  return value === undefined ? "waiting for token" : String(value);
}

function signalPreview(spec) {
  const scalar = currentEmitterSignals[spec.key];
  if (scalar) {
    return `${formatSignalValue(scalar.raw)}${scalar.unit ? ` ${scalar.unit}` : ""}`;
  }
  const stream = currentEmitterStreams[spec.key];
  if (stream) return describeStreamValue(stream);
  return selectedEmitterSignalKeys.has(spec.key) ? "waiting for token" : "available";
}

function sendSignalSelectionUpdate() {
  saveParams();
  sendParamUpdate({ emitter_signal_keys: [...selectedEmitterSignalKeys] });
  renderSignalExplorer();
  renderSignalMonitor();
}

function renderSignalExplorer() {
  if (!signalCatalogueList) return;
  const filtered = filterSignalCatalogue(
    emitterSignalCatalogue,
    signalCatalogueSearch?.value,
    signalCatalogueKindFilter,
  );
  const selectedCount = emitterSignalCatalogue.filter(spec => selectedEmitterSignalKeys.has(spec.key)).length;
  const activeMappings = emitterMappings.filter(mapping => mapping.enabled !== false);
  if (signalActiveCount) signalActiveCount.textContent = `${selectedCount} active`;
  if (signalLocalRouteCount) signalLocalRouteCount.textContent = `${selectedCount} selected`;
  if (signalMappingRouteCount) signalMappingRouteCount.textContent = `${activeMappings.length} routes`;

  signalCatalogueList.innerHTML = "";
  signalCatalogueList.classList.remove("empty-monitor");
  const groups = new Map();
  for (const spec of filtered) {
    if (!groups.has(spec.group)) groups.set(spec.group, []);
    groups.get(spec.group).push(spec);
  }

  for (const [groupName, specs] of groups) {
    const group = document.createElement("section");
    group.className = "signal-catalogue-group";
    const heading = document.createElement("div");
    heading.className = "signal-group-heading";
    const headingLabel = document.createElement("span");
    headingLabel.textContent = groupName;
    const headingCount = document.createElement("span");
    headingCount.textContent = `${specs.filter(spec => selectedEmitterSignalKeys.has(spec.key)).length}/${specs.length}`;
    heading.append(headingLabel, headingCount);
    group.appendChild(heading);

    for (const spec of specs) {
      const routes = signalRouteSummary(spec, selectedEmitterSignalKeys, emitterMappings);
      const card = document.createElement("label");
      card.className = "signal-card";
      card.classList.toggle("is-active", routes.active);
      card.title = spec.key;

      const enabled = document.createElement("input");
      enabled.type = "checkbox";
      enabled.checked = routes.active;
      enabled.addEventListener("change", () => {
        if (enabled.checked) selectedEmitterSignalKeys.add(spec.key);
        else selectedEmitterSignalKeys.delete(spec.key);
        sendSignalSelectionUpdate();
      });

      const main = document.createElement("div");
      main.className = "signal-card-main";
      const title = document.createElement("div");
      title.className = "signal-card-title";
      const label = document.createElement("strong");
      label.textContent = spec.label;
      const kind = document.createElement("span");
      kind.className = `signal-badge ${spec.kind}`;
      kind.textContent = spec.kind;
      const type = document.createElement("span");
      type.className = "signal-badge";
      type.textContent = spec.value_type;
      title.append(label, kind, type);

      const description = document.createElement("div");
      description.className = "signal-card-description";
      description.textContent = spec.description;
      const meta = document.createElement("div");
      meta.className = "signal-card-meta";
      const location = document.createElement("span");
      location.textContent = spec.location;
      const cost = document.createElement("span");
      cost.textContent = `${spec.cost || "low"} cost`;
      meta.append(location, cost);

      const preview = document.createElement("div");
      preview.className = "signal-card-preview";
      preview.textContent = signalPreview(spec);
      const routeList = document.createElement("div");
      routeList.className = "signal-card-routes";
      const monitorRoute = document.createElement("span");
      monitorRoute.className = routes.active ? "is-routed" : "";
      monitorRoute.textContent = routes.active ? "Local monitor" : "Inactive";
      const mappingRoute = document.createElement("span");
      mappingRoute.className = routes.mappingCount ? "is-routed" : "";
      mappingRoute.textContent = spec.mappable
        ? `${routes.mappingCount} mapping${routes.mappingCount === 1 ? "" : "s"}`
        : "Not scalar-mappable";
      const connectorRoute = document.createElement("span");
      connectorRoute.textContent = routes.connector;
      routeList.append(monitorRoute, mappingRoute, connectorRoute);
      main.append(title, description, meta, preview, routeList);
      card.append(enabled, main);
      group.appendChild(card);
    }
    signalCatalogueList.appendChild(group);
  }

  if (!filtered.length) {
    signalCatalogueList.classList.add("empty-monitor");
    signalCatalogueList.textContent = "No signals match this search and filter.";
  }
}

// ── Emitter mapping instrument ─────────────────────────────────────────────
function mappingId(prefix = "mapping") {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`;
}

function targetSpec(key) {
  return mappingCatalogue.targets.find(item => item.key === key) ?? {
    minimum: 0,
    maximum: 1,
    unit: "",
  };
}

function completeMapping(partial = {}) {
  const source = partial.source || mappingCatalogue.signals[0]?.key || "activation.max";
  const target = partial.target || mappingCatalogue.targets[0]?.key || "audio.gain";
  const spec = targetSpec(target);
  return {
    id: partial.id || mappingId(),
    enabled: partial.enabled !== false,
    source,
    target,
    curve: partial.curve || "linear",
    threshold: Number(partial.threshold ?? 0),
    invert: Boolean(partial.invert),
    quantize_steps: Number(partial.quantize_steps ?? 0),
    smoothing: Number(partial.smoothing ?? 0),
    output_min: Number(partial.output_min ?? spec.minimum),
    output_max: Number(partial.output_max ?? spec.maximum),
  };
}

function populateGroupedOptions(select, items, selected) {
  select.innerHTML = "";
  const groups = new Map();
  for (const item of items) {
    if (!groups.has(item.group)) groups.set(item.group, []);
    groups.get(item.group).push(item);
  }
  for (const [group, entries] of groups) {
    const optgroup = document.createElement("optgroup");
    optgroup.label = group;
    for (const entry of entries) {
      const option = document.createElement("option");
      option.value = entry.key;
      option.textContent = entry.label;
      option.selected = entry.key === selected;
      optgroup.appendChild(option);
    }
    select.appendChild(optgroup);
  }
}

function mappingField(label, control) {
  const field = document.createElement("label");
  field.className = "mapping-field";
  const caption = document.createElement("span");
  caption.textContent = label;
  field.append(caption, control);
  return field;
}

function numberControl(value, step, onChange) {
  const input = document.createElement("input");
  input.type = "number";
  input.step = step;
  input.value = Number(value).toFixed(step < 1 ? 2 : 0);
  input.addEventListener("change", () => onChange(Number(input.value)));
  return input;
}

function renderMappingEditor() {
  if (!mappingList) return;
  mappingList.innerHTML = "";
  if (mappingCount) mappingCount.textContent = `${emitterMappings.length}/${mappingCatalogue.max_mappings || 32}`;
  if (!mappingCatalogue.signals.length || !mappingCatalogue.targets.length) return;

  emitterMappings.forEach((rawMapping, index) => {
    const mapping = completeMapping(rawMapping);
    emitterMappings[index] = mapping;
    const row = document.createElement("div");
    row.className = "mapping-row";
    row.dataset.mappingId = mapping.id;
    row.classList.toggle("is-disabled", !mapping.enabled);

    const top = document.createElement("div");
    top.className = "mapping-row-top";
    const enabled = document.createElement("input");
    enabled.type = "checkbox";
    enabled.checked = mapping.enabled;
    enabled.title = "Enable mapping";
    enabled.addEventListener("change", () => {
      mapping.enabled = enabled.checked;
      row.classList.toggle("is-disabled", !mapping.enabled);
      scheduleMappingUpdate();
    });
    const source = document.createElement("select");
    populateGroupedOptions(source, mappingCatalogue.signals, mapping.source);
    source.addEventListener("change", () => {
      mapping.source = source.value;
      scheduleMappingUpdate();
    });
    const arrow = document.createElement("span");
    arrow.className = "mapping-arrow";
    arrow.textContent = "→";
    const target = document.createElement("select");
    populateGroupedOptions(target, mappingCatalogue.targets, mapping.target);
    target.addEventListener("change", () => {
      mapping.target = target.value;
      const spec = targetSpec(mapping.target);
      mapping.output_min = spec.minimum;
      mapping.output_max = spec.maximum;
      renderMappingEditor();
      scheduleMappingUpdate(0);
    });
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "mapping-remove";
    remove.textContent = "×";
    remove.title = "Remove mapping";
    remove.addEventListener("click", () => {
      emitterMappings.splice(index, 1);
      renderMappingEditor();
      scheduleMappingUpdate(0);
    });
    top.append(enabled, source, arrow, target, remove);

    const grid = document.createElement("div");
    grid.className = "mapping-grid";
    const curve = document.createElement("select");
    for (const value of mappingCatalogue.curves || ["linear"]) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value.replace("_", " ");
      option.selected = value === mapping.curve;
      curve.appendChild(option);
    }
    curve.addEventListener("change", () => { mapping.curve = curve.value; scheduleMappingUpdate(); });
    grid.append(
      mappingField("Curve", curve),
      mappingField("Out min", numberControl(mapping.output_min, 0.01, value => {
        mapping.output_min = value;
        scheduleMappingUpdate();
      })),
      mappingField("Out max", numberControl(mapping.output_max, 0.01, value => {
        mapping.output_max = value;
        scheduleMappingUpdate();
      })),
      mappingField("Threshold", numberControl(mapping.threshold, 0.01, value => {
        mapping.threshold = value;
        scheduleMappingUpdate();
      })),
      mappingField("Smooth", numberControl(mapping.smoothing, 0.01, value => {
        mapping.smoothing = value;
        scheduleMappingUpdate();
      })),
      mappingField("Steps", numberControl(mapping.quantize_steps, 1, value => {
        mapping.quantize_steps = value;
        scheduleMappingUpdate();
      })),
    );
    const invert = document.createElement("label");
    invert.className = "mapping-invert";
    const invertInput = document.createElement("input");
    invertInput.type = "checkbox";
    invertInput.checked = mapping.invert;
    invertInput.addEventListener("change", () => { mapping.invert = invertInput.checked; scheduleMappingUpdate(); });
    invert.append(invertInput, "Invert");
    grid.appendChild(invert);

    const latest = currentMappingDiagnostics.find(item => item.id === mapping.id);
    const readout = document.createElement("div");
    readout.className = "mapping-live-readout";
    readout.textContent = latest
      ? `${formatSignalValue(latest.input)} → ${formatSignalValue(latest.output)}`
      : "waiting for token";
    row.append(top, grid, readout);
    mappingList.appendChild(row);
  });
  renderSignalExplorer();
}

function scheduleMappingUpdate(delayMs = 120) {
  saveParams();
  if (mappingUpdateTimer) clearTimeout(mappingUpdateTimer);
  mappingUpdateTimer = setTimeout(() => {
    sendParamUpdate({ emitter_mappings: structuredClone(emitterMappings) });
  }, delayMs);
}

function templateMappings(name) {
  if (name === "semantic") {
    return [
      completeMapping({ source: "tonality.score", target: "audio.delay_mix", curve: "ease_in", smoothing: 0.4, output_min: 0, output_max: 0.55 }),
      completeMapping({ source: "tonality.change", target: "audio.pitch_semitones", quantize_steps: 8, output_min: 0, output_max: 7 }),
      completeMapping({ source: "prompt.influence", target: "audio.pan", smoothing: 0.6, output_min: -1, output_max: 1 }),
      completeMapping({ source: "pitch.interpretation", target: "audio.delay_time", output_min: 0.05, output_max: 0.7 }),
      completeMapping({ source: "feature.top_index", target: "visual.hue", quantize_steps: 12, output_min: 0, output_max: 360 }),
      completeMapping({ source: "tonality.score", target: "visual.energy", curve: "ease_out", output_min: 0.25, output_max: 1 }),
    ];
  }
  if (name === "sparse") {
    return [
      completeMapping({ source: "feature.top_share", target: "audio.gain", curve: "ease_out", smoothing: 0.25, output_min: 0.15, output_max: 1 }),
      completeMapping({ source: "feature.described_ratio", target: "audio.filter_hz", curve: "ease_in", smoothing: 0.5, output_min: 300, output_max: 12000 }),
      completeMapping({ source: "pitch.spread", target: "audio.duration", curve: "ease_out", output_min: 0.2, output_max: 2 }),
      completeMapping({ source: "cluster.dominance", target: "visual.bar_scale", output_min: 0.5, output_max: 2.3 }),
      completeMapping({ source: "feature.count", target: "visual.motion", curve: "ease_out", output_min: 0, output_max: 1 }),
    ];
  }
  return structuredClone(defaultEmitterMappings).map(completeMapping);
}

function captureScene(name, mappings = emitterMappings) {
  return {
    id: mappingId("scene"),
    name,
    mappings: structuredClone(mappings),
    tonalities: structuredClone(tonalityCatalogue),
    promptInfluence: Number(promptInfluenceIn.value),
    pitchBias: Number(tonalityPitchBiasIn.value),
    volume: Number(volumeIn.value),
    audition: {
      pinned: [...pinnedFeatures],
      muted: [...mutedFeatures],
      solo: [...soloFeatures],
    },
  };
}

function ensureFactoryScenes() {
  const factories = [
    ["factory-activation", "Activation performance", "activation"],
    ["factory-semantic", "Semantic drift", "semantic"],
    ["factory-sparse", "Sparse detail", "sparse"],
  ];
  for (const [id, name, template] of factories) {
    const existing = instrumentScenes.find(scene => scene.id === id);
    if (existing) {
      if (!(existing.tonalities || []).length && tonalityCatalogue.length) {
        existing.tonalities = structuredClone(tonalityCatalogue);
      }
      continue;
    }
    instrumentScenes.unshift({ ...captureScene(name, templateMappings(template)), id, builtin: true });
  }
  saveScenes();
}

function renderSceneSelectors() {
  if (!sceneSelect || !sceneA || !sceneB) return;
  ensureFactoryScenes();
  for (const select of [sceneSelect, sceneA, sceneB]) {
    const previous = select.value;
    select.innerHTML = "";
    instrumentScenes.forEach(scene => {
      const option = document.createElement("option");
      option.value = scene.id;
      option.textContent = scene.name;
      select.appendChild(option);
    });
    if (instrumentScenes.some(scene => scene.id === previous)) select.value = previous;
  }
  if (!sceneB.value && instrumentScenes[1]) sceneB.value = instrumentScenes[1].id;
  if (sceneA.value === sceneB.value && instrumentScenes[1]) sceneB.value = instrumentScenes[1].id;
}

function sceneById(id) {
  return instrumentScenes.find(scene => scene.id === id);
}

function applyScene(scene) {
  if (!scene) return;
  emitterMappings = structuredClone(scene.mappings || []);
  tonalityCatalogue = structuredClone(scene.tonalities || tonalityCatalogue).map(normalizedLens);
  promptInfluenceIn.value = String(scene.promptInfluence ?? promptInfluenceIn.value);
  tonalityPitchBiasIn.value = String(scene.pitchBias ?? tonalityPitchBiasIn.value);
  volumeIn.value = String(scene.volume ?? volumeIn.value);
  const audition = scene.audition || {};
  pinnedFeatures = new Set((audition.pinned || []).map(Number));
  mutedFeatures = new Set((audition.muted || []).map(Number));
  soloFeatures = new Set((audition.solo || []).map(Number));
  renderMappingEditor();
  renderLensEditor();
  renderFeatureBrowser();
  updateTonalityControlValues();
  updateVolumeValue();
  engine.setVolume(Number(volumeIn.value));
  saveInstrumentState();
  saveParams();
  sendParamUpdate({
    emitter_mappings: structuredClone(emitterMappings),
    tonality_lenses: collectTonalityLenses(),
    prompt_influence: Number(promptInfluenceIn.value),
    tonality_pitch_bias: Number(tonalityPitchBiasIn.value),
  });
}

function lerp(a, b, amount) {
  return Number(a) + ((Number(b) - Number(a)) * amount);
}

function morphMapping(a, b, amount, index) {
  const categorical = amount < 0.5 ? a : b;
  const left = a || b;
  const right = b || a;
  return completeMapping({
    ...categorical,
    id: `morph-${index}-${categorical.target}`,
    enabled: Boolean(categorical.enabled),
    threshold: lerp(left.threshold ?? 0, right.threshold ?? 0, amount),
    smoothing: lerp(left.smoothing ?? 0, right.smoothing ?? 0, amount),
    quantize_steps: Math.round(lerp(left.quantize_steps ?? 0, right.quantize_steps ?? 0, amount)),
    output_min: lerp(left.output_min, right.output_min, amount),
    output_max: lerp(left.output_max, right.output_max, amount),
  });
}

function applySceneMorph() {
  const left = sceneById(sceneA.value);
  const right = sceneById(sceneB.value);
  if (!left || !right) return;
  const amount = Number(sceneMorph.value);
  sceneMorphValue.textContent = `${Math.round(amount * 100)}%`;
  const count = Math.max(left.mappings?.length || 0, right.mappings?.length || 0);
  emitterMappings = Array.from({ length: count }, (_, index) =>
    morphMapping(left.mappings[index], right.mappings[index], amount, index)
  );
  tonalityCatalogue = structuredClone((amount < 0.5 ? left : right).tonalities || tonalityCatalogue).map(normalizedLens);
  promptInfluenceIn.value = String(lerp(left.promptInfluence ?? 0.2, right.promptInfluence ?? 0.2, amount));
  tonalityPitchBiasIn.value = String(lerp(left.pitchBias ?? 0.55, right.pitchBias ?? 0.55, amount));
  volumeIn.value = String(lerp(left.volume ?? 0.7, right.volume ?? 0.7, amount));
  renderMappingEditor();
  renderLensEditor();
  updateTonalityControlValues();
  updateVolumeValue();
  engine.setVolume(Number(volumeIn.value));
  scheduleMappingUpdate(0);
  scheduleLensUpdate(0);
  sendParamUpdate({
    prompt_influence: Number(promptInfluenceIn.value),
    tonality_pitch_bias: Number(tonalityPitchBiasIn.value),
  });
}

// ── WebSocket ──────────────────────────────────────────────────────────────
function connectWS() {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  ws = new WebSocket(`${proto}//${location.host}/ws/stream`);

  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    handleMessage(msg);
  };

  ws.onerror = () => setStatus("WebSocket error");
  ws.onclose = () => { ws = null; sessionActive = false; finishLoadingProgress(); setIdle(); };
}

function loadingStageElements() {
  return [...document.querySelectorAll("[data-loading-stage]")];
}

function startLoadingProgress() {
  loadingPanel.classList.remove("hidden");
  loadingPanel.dataset.state = "active";
  loadingTitle.textContent = "Preparing Emitter";
  loadingDetail.textContent = "Waiting for the runtime…";
  loadingPercent.textContent = "0%";
  loadingProgress.value = 0;
  for (const stage of loadingStageElements()) stage.dataset.state = "pending";
}

function handleLoadingMessage(msg) {
  if (loadingPanel.classList.contains("hidden")) startLoadingProgress();
  const priorProgress = Number(loadingProgress.value) / 100;
  const rawProgress = Number(msg.progress);
  const normalizedProgress = Number.isFinite(rawProgress)
    ? Math.max(0, Math.min(1, rawProgress))
    : Math.max(0, Math.min(1, priorProgress || 0));
  const percent = Math.round(normalizedProgress * 100);
  const label = msg.label || msg.stage || "Preparing Emitter";
  const detail = msg.detail || (msg.stage_key ? "Preparing selected runtime…" : "Loading runtime resources…");

  loadingPanel.dataset.state = msg.state === "error" ? "error" : "active";
  loadingTitle.textContent = label;
  loadingDetail.textContent = detail;
  loadingPercent.textContent = `${percent}%`;
  loadingProgress.value = percent;
  for (const stage of loadingStageElements()) {
    if (stage.dataset.loadingStage === msg.stage_key) {
      stage.dataset.state = msg.state || "active";
    }
  }
  setStatus(`Preparing · ${label}`);
}

function finishLoadingProgress(force = false) {
  if (!force && loadingPanel.dataset.state === "error") return;
  loadingPanel.classList.add("hidden");
  loadingPanel.dataset.state = "active";
}

function failLoadingProgress(message) {
  loadingPanel.classList.remove("hidden");
  loadingPanel.dataset.state = "error";
  loadingTitle.textContent = "Preparation failed";
  loadingDetail.textContent = message || "The Emitter could not prepare this run.";
}

function handleMessage(msg) {
  switch (msg.type) {
    case "ready":
      applyParams(msg.params);
      finishLoadingProgress(true);
      setIdle();
      setStatus("Connected — ready");
      break;

    case "loading":
      handleLoadingMessage(msg);
      break;

    case "cluster_palette":
      cvPalette = msg.palette || [];
      renderColorStrip();
      break;

    case "model_structure": {
      const modelId = msg.model || modelSel.value;
      if (!catalogue[modelId]) catalogue[modelId] = { layers: [], widths: [] };
      catalogue[modelId].architecture = {
        ...(catalogue[modelId].architecture || {}),
        ...(msg.architecture || {}),
      };
      const layerCount = Number(catalogue[modelId].architecture.layer_count || 0);
      if (layerCount > 0) {
        catalogue[modelId].observation_layers = Array.from({ length: layerCount }, (_item, index) => index);
      }
      if (modelId === modelSel.value) {
        populateObservationLayer(modelId, observationLayerIn.value);
        renderModelAnatomy();
      }
      break;
    }

    case "token":
      finishLoadingProgress();
      tokenHistory.push(msg);
      if (isPaused) {
        pendingBuffer.push(msg);
        btnNext.disabled = false;
        break;
      }
      tokenCount++;
      historyIndex = tokenHistory.length - 1;
      setStatus(`Tokens: ${tokenCount}`);
      if (msg.loop_count !== undefined) {
        loopCountEl.textContent = `Loop: ${msg.loop_count}`;
        loopCountEl.classList.remove("hidden");
      }
      consumeEmitterPayload(msg);
      engine.playNotes(
        auditionNotes(msg.notes ?? []),
        modeSel.value,
        parseInt(bpmIn.value),
        currentEmitterControls,
      );
      renderClusterViz(msg);
      renderTonalityPanel(msg);
      renderEmitterInspector(msg);
      highlightToken(historyIndex);
      break;

    case "done":
      finishLoadingProgress();
      setStatus(`Done (${tokenCount} tokens) — loop or send a new prompt`);
      if (historyIndex === -1) resetClusterViz();
      setDone();
      break;

    case "silent":
      engine.stopAll();
      setStatus("Silent");
      break;

    case "osc_status":
      setOscStatus(msg.message || "OSC status unavailable", msg.status || "unconfigured");
      break;

    case "tonality_lenses_status":
      if (msg.status === "embedding") setLensEmbeddingStatus("embedding…", "embedding");
      else if (msg.status === "ready") setLensEmbeddingStatus(`${msg.lens_count ?? 0} embedded`, "ready");
      else setLensEmbeddingStatus("embedding error", "error");
      break;

    case "stopped":
      engine.stopAll();
      finishLoadingProgress();
      if (!isRunning) {
        sessionActive = false;
        setIdle();
        resetClusterViz();
      }
      break;

    case "error":
      failLoadingProgress(msg.message);
      setStatus(`Error: ${msg.message}`);
      sessionActive = false;
      setIdle();
      break;
  }
}

function formatSignalValue(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "—";
  if (Math.abs(numeric) >= 1000) return numeric.toFixed(0);
  if (Math.abs(numeric) >= 10) return numeric.toFixed(1);
  return numeric.toFixed(3);
}

function consumeEmitterPayload(msg) {
  const emitter = msg.emitter || {};
  currentEmitterSignals = emitter.signals || {};
  currentEmitterStreams = emitter.streams || {};
  currentEmitterControls = emitter.controls || {};
  currentMappingDiagnostics = emitter.mappings || [];
  currentVisualControls = Object.fromEntries(
    Object.entries(currentEmitterControls).filter(([key]) => key.startsWith("visual."))
  );
  updateFeatureCatalogue(msg.notes || []);
  applyVisualControls();
  renderSignalExplorer();
  renderNeuralAtlas(msg);
}

function auditionNotes(notes) {
  const hasSolo = soloFeatures.size > 0;
  return notes.filter(note => {
    const feature = Number(note.feature_index);
    if (mutedFeatures.has(feature)) return false;
    return !hasSolo || soloFeatures.has(feature);
  });
}

function applyVisualControls() {
  const panel = document.getElementById("cluster-viz-panel");
  const canvas = document.getElementById("cluster-canvas");
  const energy = Math.max(0, Math.min(1, currentVisualControls["visual.energy"] ?? 1));
  const hue = currentVisualControls["visual.hue"] ?? 0;
  const motion = Math.max(0, Math.min(1, currentVisualControls["visual.motion"] ?? 0));
  if (panel) {
    panel.style.opacity = String(0.55 + (energy * 0.45));
    panel.style.transform = `translateY(${Math.sin(tokenCount * 0.9) * motion * 4}px)`;
  }
  if (canvas) canvas.style.filter = `hue-rotate(${hue}deg) brightness(${0.7 + (energy * 0.6)})`;
}

function renderEmitterInspector(msg) {
  if (signalToken) signalToken.textContent = `token ${tokenCount}`;
  renderSignalMonitor();
  renderControlMonitor();
  renderFeatureBrowser();
  for (const diagnostic of currentMappingDiagnostics) {
    const row = mappingList?.querySelector(`[data-mapping-id="${CSS.escape(diagnostic.id)}"]`);
    const readout = row?.querySelector(".mapping-live-readout");
    if (readout) readout.textContent = `${formatSignalValue(diagnostic.input)} → ${formatSignalValue(diagnostic.output)}`;
  }
  if (featureCount) featureCount.textContent = `${(msg.notes || []).length} active`;
}

function renderSignalMonitor() {
  if (!signalMonitor) return;
  signalMonitor.innerHTML = "";
  signalMonitor.classList.remove("empty-monitor");
  for (const [key, signal] of Object.entries(currentEmitterSignals)) {
    const row = document.createElement("div");
    row.className = "signal-row";
    row.title = `${key} · normalized ${formatSignalValue(signal.normalized)}`;
    const fill = document.createElement("div");
    fill.className = "signal-fill";
    fill.style.width = `${Math.round(Math.max(0, Math.min(1, signal.normalized || 0)) * 100)}%`;
    const label = document.createElement("span");
    label.textContent = signal.label || key;
    const value = document.createElement("span");
    value.textContent = `${formatSignalValue(signal.raw)}${signal.unit ? ` ${signal.unit}` : ""}`;
    row.append(fill, label, value);
    signalMonitor.appendChild(row);
  }
  for (const [key, stream] of Object.entries(currentEmitterStreams)) {
    const row = document.createElement("div");
    row.className = "signal-row stream-signal-row";
    row.title = `${key} · ${stream.location || "stream"}`;
    const label = document.createElement("span");
    label.textContent = stream.label || key;
    const value = document.createElement("span");
    value.textContent = describeStreamValue(stream);
    row.append(label, value);
    signalMonitor.appendChild(row);
  }
  if (!signalMonitor.children.length) {
    signalMonitor.classList.add("empty-monitor");
    signalMonitor.textContent = "No emitter signals in this token.";
  }
}

function renderControlMonitor() {
  if (!controlMonitor) return;
  const entries = Object.entries(currentEmitterControls);
  if (controlCount) controlCount.textContent = `${entries.length} active`;
  controlMonitor.innerHTML = "";
  controlMonitor.classList.remove("empty-monitor");
  for (const [key, output] of entries) {
    const spec = targetSpec(key);
    const span = Math.max(spec.maximum - spec.minimum, 1e-9);
    const normalized = Math.max(0, Math.min(1, (output - spec.minimum) / span));
    const row = document.createElement("div");
    row.className = "control-row";
    row.title = key;
    const fill = document.createElement("div");
    fill.className = "control-fill";
    fill.style.width = `${Math.round(normalized * 100)}%`;
    const label = document.createElement("span");
    label.textContent = spec.label || key;
    const value = document.createElement("span");
    value.textContent = `${formatSignalValue(output)}${spec.unit ? ` ${spec.unit}` : ""}`;
    row.append(fill, label, value);
    controlMonitor.appendChild(row);
  }
  if (!entries.length) {
    controlMonitor.classList.add("empty-monitor");
    controlMonitor.textContent = "No enabled mappings.";
  }
}

function updateFeatureCatalogue(notes) {
  for (const item of featureCatalogue.values()) item.active = false;
  for (const note of notes) {
    const index = Number(note.feature_index);
    if (!Number.isFinite(index)) continue;
    featureCatalogue.set(index, {
      ...featureCatalogue.get(index),
      index,
      active: true,
      activation: Number(note.amplitude || 0),
      description: note.feature_description || "",
      cluster: note.cluster,
      clusterName: note.cluster_name || "",
      color: note.cluster_color || "#888888",
      rawFreq: Number(note.raw_freq ?? note.freq ?? 0),
      finalFreq: Number(note.freq ?? 0),
      instrument: note.instrument || "default",
    });
  }
}

function toggleFeatureSet(target, index) {
  if (target.has(index)) target.delete(index);
  else target.add(index);
  saveInstrumentState();
  renderFeatureBrowser();
}

function renderFeatureBrowser() {
  if (!featureBrowser) return;
  const query = String(featureSearch?.value || "").trim().toLowerCase();
  const items = [...featureCatalogue.values()]
    .filter(item => item.active || pinnedFeatures.has(item.index))
    .filter(item => {
      if (!query) return true;
      return [item.index, item.description, item.clusterName, item.cluster, item.instrument]
        .some(value => String(value ?? "").toLowerCase().includes(query));
    })
    .sort((a, b) => {
      const pinDifference = Number(pinnedFeatures.has(b.index)) - Number(pinnedFeatures.has(a.index));
      return pinDifference || Number(b.active) - Number(a.active) || b.activation - a.activation;
    })
    .slice(0, 80);

  featureBrowser.innerHTML = "";
  featureBrowser.classList.remove("empty-monitor");
  for (const item of items) {
    const row = document.createElement("div");
    row.className = "feature-row";
    row.classList.toggle("is-muted-feature", mutedFeatures.has(item.index));
    row.classList.toggle("is-solo-feature", soloFeatures.has(item.index));
    row.style.borderLeftColor = item.color;
    const actions = document.createElement("div");
    actions.className = "feature-actions";
    for (const [label, title, set] of [
      ["P", "Pin feature", pinnedFeatures],
      ["M", "Mute in browser audition", mutedFeatures],
      ["S", "Solo in browser audition", soloFeatures],
    ]) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = label;
      button.title = title;
      button.classList.toggle("active", set.has(item.index));
      button.addEventListener("click", () => toggleFeatureSet(set, item.index));
      actions.appendChild(button);
    }
    const main = document.createElement("div");
    main.className = "feature-main";
    const description = document.createElement("div");
    description.className = "feature-description";
    description.textContent = item.description || `feature ${item.index}`;
    description.title = item.description || `feature ${item.index}`;
    const meta = document.createElement("div");
    meta.className = "feature-meta";
    meta.textContent = `#${item.index} · ${item.clusterName || `cluster ${item.cluster ?? "—"}`} · ${formatSignalValue(item.rawFreq)}→${formatSignalValue(item.finalFreq)} Hz`;
    main.append(description, meta);
    const activation = document.createElement("span");
    activation.className = "feature-activation";
    activation.textContent = item.active ? formatSignalValue(item.activation) : "idle";
    row.append(actions, main, activation);
    featureBrowser.appendChild(row);
  }
  if (!items.length) {
    featureBrowser.classList.add("empty-monitor");
    featureBrowser.textContent = query ? "No matching active or pinned features." : "Feature evidence will appear here.";
  }
}

// ── Cluster Viz ─────────────────────────────────────────────────────────────
function renderColorStrip() {
  const strip = document.getElementById("cv-color-strip");
  if (!strip) return;
  strip.innerHTML = "";
  for (const item of cvPalette) {
    const div = document.createElement("div");
    div.style.backgroundColor = item.color;
    div.title = item.name;
    const span = document.createElement("span");
    span.textContent = item.name;
    div.appendChild(span);
    strip.appendChild(div);
  }
}

function renderClusterViz(msg) {
  const tokenLabel = document.getElementById("cv-token-label");
  if (tokenLabel) tokenLabel.textContent = msg.token || "—";

  const notes = msg.notes || [];
  const enrichedNotes = notes.filter(n => n.cluster_color);
  if (enrichedNotes.length === 0) return;

  // Sum activations per cluster to find dominant cluster
  const clusterTotals = {};
  for (const note of enrichedNotes) {
    const cid = note.cluster;
    if (cid !== null && cid !== undefined) {
      clusterTotals[cid] = (clusterTotals[cid] || 0) + note.amplitude;
    }
  }

  let dominantClusterId = null, maxTotal = -Infinity;
  for (const [cid, total] of Object.entries(clusterTotals)) {
    if (total > maxTotal) { maxTotal = total; dominantClusterId = cid; }
  }
  const dominantEntry = cvPalette.find(p => String(p.cluster_id) === String(dominantClusterId));

  // Background color = dominant cluster's color
  const clusterCanvas = document.getElementById("cluster-canvas");
  if (clusterCanvas) {
    clusterCanvas.style.backgroundColor = dominantEntry ? dominantEntry.color : "#333333";
  }

  // Labels: dominant cluster name + top-amplitude feature within dominant cluster
  const inDominant = enrichedNotes.filter(n => String(n.cluster) === String(dominantClusterId));
  const topFeature = inDominant.length
    ? inDominant.reduce((a, b) => a.amplitude > b.amplitude ? a : b)
    : null;

  const clusterLabel = document.getElementById("cv-cluster-label");
  const featureLabel = document.getElementById("cv-feature-label");
  if (clusterLabel) clusterLabel.textContent = `cluster: ${dominantEntry?.name || "—"}`;
  if (featureLabel) featureLabel.textContent = `feature: ${topFeature?.feature_description || "—"}`;

  // Draw sorted bar chart
  if (clusterCanvas) drawClusterBars(clusterCanvas, enrichedNotes);

  // Append token span to full text output
  const textContent = document.getElementById("cv-text-content");
  if (textContent) {
    const span = document.createElement("span");
    span.dataset.idx = tokenHistory.length - 1;
    span.textContent = msg.token || "";
    textContent.appendChild(span);
    const textBox = document.getElementById("cv-text-output");
    if (textBox) textBox.scrollTop = textBox.scrollHeight;
  }
}

// Same as renderClusterViz but does NOT append to the text output (for navigation)
function renderClusterVizStatic(msg) {
  const tokenLabel = document.getElementById("cv-token-label");
  if (tokenLabel) tokenLabel.textContent = msg.token || "—";

  const notes = msg.notes || [];
  const enrichedNotes = notes.filter(n => n.cluster_color);
  if (enrichedNotes.length === 0) return;

  const clusterTotals = {};
  for (const note of enrichedNotes) {
    const cid = note.cluster;
    if (cid !== null && cid !== undefined) {
      clusterTotals[cid] = (clusterTotals[cid] || 0) + note.amplitude;
    }
  }

  let dominantClusterId = null, maxTotal = -Infinity;
  for (const [cid, total] of Object.entries(clusterTotals)) {
    if (total > maxTotal) { maxTotal = total; dominantClusterId = cid; }
  }
  const dominantEntry = cvPalette.find(p => String(p.cluster_id) === String(dominantClusterId));

  const clusterCanvas = document.getElementById("cluster-canvas");
  if (clusterCanvas) {
    clusterCanvas.style.backgroundColor = dominantEntry ? dominantEntry.color : "#333333";
  }

  const inDominant = enrichedNotes.filter(n => String(n.cluster) === String(dominantClusterId));
  const topFeature = inDominant.length
    ? inDominant.reduce((a, b) => a.amplitude > b.amplitude ? a : b)
    : null;

  const clusterLabel = document.getElementById("cv-cluster-label");
  const featureLabel = document.getElementById("cv-feature-label");
  if (clusterLabel) clusterLabel.textContent = `cluster: ${dominantEntry?.name || "—"}`;
  if (featureLabel) featureLabel.textContent = `feature: ${topFeature?.feature_description || "—"}`;

  if (clusterCanvas) drawClusterBars(clusterCanvas, enrichedNotes);
}

function renderTonalityIdle() {
  if (tonalityState) tonalityState.textContent = tonalityCatalogue.length ? "ready" : "idle";
  if (tonalityPrimary) tonalityPrimary.textContent = "—";
  if (tonalityDescription) tonalityDescription.textContent = "—";
  if (tonalityBars) {
    tonalityBars.innerHTML = "";
    for (const entry of tonalityCatalogue.slice(0, 4)) {
      const row = document.createElement("div");
      row.className = "tonality-match is-muted";
      const name = document.createElement("span");
      name.textContent = entry.name;
      const score = document.createElement("span");
      score.textContent = "0.00";
      row.append(name, score);
      tonalityBars.appendChild(row);
    }
  }
  if (tonalityIntervals) tonalityIntervals.innerHTML = "";
  renderIdleReadout(tonalityMemory, "Run memory · 0");
  renderIdleReadout(tonalityEvidence, "Why this sound");
}

function renderIdleReadout(target, label) {
  if (!target) return;
  target.innerHTML = "";
  const header = document.createElement("div");
  header.className = "tonality-subhead";
  header.textContent = label;
  const row = document.createElement("div");
  row.className = "memory-row is-empty";
  const dash = document.createElement("span");
  dash.textContent = "—";
  row.appendChild(dash);
  target.append(header, row);
}

function renderTonalityPanel(msg) {
  lastRenderedNotes = msg.notes ?? [];
  const payload = msg.tonality;
  const matches = payload?.matches ?? [];

  if (!matches.length) {
    if (tonalityState) tonalityState.textContent = payload ? "silent" : "off";
    if (tonalityPrimary) tonalityPrimary.textContent = "—";
    if (tonalityDescription) tonalityDescription.textContent = "—";
    if (tonalityBars) tonalityBars.innerHTML = "";
    if (tonalityIntervals) tonalityIntervals.innerHTML = "";
    renderIdleReadout(tonalityMemory, "Run memory · 0");
    renderIdleReadout(tonalityEvidence, "Why this sound");
    return;
  }

  const primary = matches[0];
  if (tonalityState) {
    const promptPct = Math.round((payload.prompt_influence ?? 0) * 100);
    const pitchPct = Math.round((payload.pitch_bias ?? 0) * 100);
    tonalityState.textContent = `${TONAL_ROOTS[Number(primary.root || 0)]} · P${promptPct} / T${pitchPct}`;
  }
  if (tonalityPrimary) tonalityPrimary.textContent = primary.name;
  if (tonalityDescription) tonalityDescription.textContent = primary.description || "—";

  if (tonalityBars) {
    tonalityBars.innerHTML = "";
    for (const match of matches) {
      const row = document.createElement("div");
      row.className = "tonality-match";

      const normalized = Math.max(0.02, Math.min(1, (match.score + 1) / 2));
      const fill = document.createElement("div");
      fill.className = "tonality-match-fill";
      fill.style.width = `${Math.round(normalized * 100)}%`;

      const name = document.createElement("span");
      name.textContent = match.name;

      const score = document.createElement("span");
      score.textContent = match.score.toFixed(2);

      row.append(fill, name, score);
      tonalityBars.appendChild(row);
    }
  }

  if (tonalityIntervals) {
    tonalityIntervals.innerHTML = "";
    for (const interval of primary.intervals ?? []) {
      const chip = document.createElement("span");
      const numeric = Number(interval);
      const pitchClass = Number(primary.root || 0) + numeric;
      chip.textContent = Number.isInteger(pitchClass)
        ? `${TONAL_ROOTS[((pitchClass % 12) + 12) % 12]} · +${numeric}`
        : `+${numeric.toFixed(2)} st`;
      tonalityIntervals.appendChild(chip);
    }
  }

  renderTonalityMemory(payload.memory);
  renderTonalityEvidence(payload.evidence ?? []);
}

function renderTonalityMemory(memory) {
  if (!tonalityMemory) return;
  tonalityMemory.innerHTML = "";
  const matches = memory?.matches ?? [];
  if (!matches.length) return;

  const header = document.createElement("div");
  header.className = "tonality-subhead";
  header.textContent = `Run memory · ${memory.token_count ?? 0}`;
  tonalityMemory.appendChild(header);

  for (const match of matches.slice(0, 2)) {
    const row = document.createElement("div");
    row.className = "memory-row";
    const label = document.createElement("span");
    label.textContent = match.name;
    const score = document.createElement("span");
    score.textContent = match.score.toFixed(2);
    row.append(label, score);
    tonalityMemory.appendChild(row);
  }
}

function renderTonalityEvidence(evidence) {
  if (!tonalityEvidence) return;
  tonalityEvidence.innerHTML = "";
  if (!evidence.length) return;

  const header = document.createElement("div");
  header.className = "tonality-subhead";
  header.textContent = "Why this sound";
  tonalityEvidence.appendChild(header);

  for (const item of evidence.slice(0, 3)) {
    const row = document.createElement("div");
    row.className = "evidence-row";
    row.style.borderLeftColor = item.cluster_color || "#888888";

    const description = document.createElement("span");
    description.textContent = item.description || `feature ${item.feature_index}`;

    const meta = document.createElement("span");
    const shift = item.pitch_shift_semitones ?? 0;
    meta.textContent = `${Number(item.activation || 0).toFixed(2)} · ${shift >= 0 ? "+" : ""}${Number(shift).toFixed(1)} st`;

    row.append(description, meta);
    tonalityEvidence.appendChild(row);
  }
}

function drawWaveformFrame() {
  if (waveCanvas) {
    const W = waveCanvas.offsetWidth || waveCanvas.width || 320;
    const H = waveCanvas.offsetHeight || waveCanvas.height || 120;
    if (waveCanvas.width !== W || waveCanvas.height !== H) {
      waveCanvas.width = W;
      waveCanvas.height = H;
    }

    const ctx = waveCanvas.getContext("2d");
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = "#101314";
    ctx.fillRect(0, 0, W, H);
    ctx.strokeStyle = "rgba(255,255,255,0.08)";
    ctx.lineWidth = 1;
    for (let y = H / 4; y < H; y += H / 4) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(W, y);
      ctx.stroke();
    }

    const data = engine.getWaveform();
    ctx.beginPath();
    ctx.lineWidth = 2;
    ctx.strokeStyle = data ? "#2cc5a7" : "rgba(213,139,91,0.65)";
    if (data) {
      for (let x = 0; x < W; x++) {
        const sample = data[Math.floor((x / W) * data.length)] || 0;
        const y = (H / 2) + (sample * H * 0.42);
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
    } else {
      const noteEnergy = Math.min(1, lastRenderedNotes.length / 32);
      for (let x = 0; x < W; x++) {
        const phase = (x / W) * Math.PI * 4;
        const y = (H / 2) + Math.sin(phase) * noteEnergy * H * 0.18;
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
    }
    ctx.stroke();
  }
  requestAnimationFrame(drawWaveformFrame);
}

function highlightToken(idx) {
  const textContent = document.getElementById("cv-text-content");
  if (!textContent) return;
  for (const span of textContent.querySelectorAll("span.token-active")) {
    span.classList.remove("token-active");
  }
  const target = textContent.querySelector(`span[data-idx="${idx}"]`);
  if (target) {
    target.classList.add("token-active");
    target.scrollIntoView({ block: "nearest" });
  }
}

function drawClusterBars(canvas, notes) {
  // Sync canvas pixel size to its CSS size for sharp rendering
  const W = canvas.offsetWidth || canvas.width;
  const H = canvas.offsetHeight || canvas.height;
  if (canvas.width !== W || canvas.height !== H) {
    canvas.width = W;
    canvas.height = H;
  }

  const canvasCtx = canvas.getContext("2d");
  canvasCtx.clearRect(0, 0, W, H);

  if (!notes.length) return;

  const sorted = [...notes].sort((a, b) => a.amplitude - b.amplitude);
  const maxAmp = Math.max(...sorted.map(n => n.amplitude), 1);
  const barW = Math.max(2, Math.floor(W / sorted.length));

  for (let i = 0; i < sorted.length; i++) {
    const note = sorted[i];
    const barScale = Math.max(0.25, Math.min(2.5, currentVisualControls["visual.bar_scale"] ?? 1));
    const barH = Math.min(H, (note.amplitude / maxAmp) * H * barScale);
    const x = i * barW;
    const y = H - barH;
    canvasCtx.fillStyle = note.cluster_color || "#888888";
    canvasCtx.fillRect(x, y, barW, barH);
    canvasCtx.strokeStyle = "#000000";
    canvasCtx.lineWidth = 1;
    canvasCtx.strokeRect(x, y, barW, barH);
  }
}

function resetClusterViz() {
  const textContent = document.getElementById("cv-text-content");
  if (textContent) textContent.innerHTML = "";
  const tokenLabel = document.getElementById("cv-token-label");
  if (tokenLabel) tokenLabel.textContent = "—";
  const clusterLabel = document.getElementById("cv-cluster-label");
  if (clusterLabel) clusterLabel.textContent = "cluster: —";
  const featureLabel = document.getElementById("cv-feature-label");
  if (featureLabel) featureLabel.textContent = "feature: —";
  const clusterCanvas = document.getElementById("cluster-canvas");
  if (clusterCanvas) {
    clusterCanvas.style.backgroundColor = "";
    const canvasCtx = clusterCanvas.getContext("2d");
    canvasCtx.clearRect(0, 0, clusterCanvas.width, clusterCanvas.height);
  }
  lastRenderedNotes = [];
  currentEmitterSignals = {};
  currentEmitterControls = {};
  currentMappingDiagnostics = [];
  currentVisualControls = {};
  featureCatalogue = new Map([...featureCatalogue].filter(([index]) => pinnedFeatures.has(index)));
  if (signalToken) signalToken.textContent = "waiting";
  if (signalMonitor) {
    signalMonitor.className = "monitor-list empty-monitor";
    signalMonitor.textContent = "Start a run to inspect normalized signals.";
  }
  if (controlMonitor) {
    controlMonitor.className = "monitor-list empty-monitor";
    controlMonitor.textContent = "Mappings will appear here.";
  }
  if (controlCount) controlCount.textContent = "0 active";
  renderFeatureBrowser();
  applyVisualControls();
  renderTonalityIdle();
}

// ── UI helpers ─────────────────────────────────────────────────────────────
function setStatus(msg) {
  statusText.textContent = msg;
}

function setIdle() {
  isRunning = false; isPaused = false; isDone = false;
  btnPlay.disabled  = false;
  btnPause.disabled = true;
  btnStop.disabled  = true;
  btnPrev.disabled  = true;
  btnNext.disabled  = true;
  btnSend.disabled  = false;
}

function setRunning() {
  isRunning = true; isPaused = false; isDone = false;
  tokenCount = 0;
  loopCountEl.classList.add("hidden");
  loopCountEl.textContent = "Loop: 0";
  btnPlay.disabled  = true;
  btnPause.disabled = false;
  btnStop.disabled  = false;
  btnPrev.disabled  = true;
  btnNext.disabled  = true;
  btnSend.disabled  = false;
}

function setPaused() {
  isPaused = true;
  btnPlay.disabled  = false;
  btnPause.disabled = true;
  btnStop.disabled  = false;
  btnPrev.disabled  = historyIndex <= 0;
  btnNext.disabled  = historyIndex >= tokenHistory.length - 1;
  btnSend.disabled  = false;
}

function setDone() {
  isRunning = false; isDone = true;
  btnPlay.disabled  = false;
  btnPause.disabled = true;
  btnStop.disabled  = false;
  btnPrev.disabled  = historyIndex <= 0;
  btnNext.disabled  = historyIndex >= tokenHistory.length - 1;
  btnSend.disabled  = false;
}

// ── Transport actions ───────────────────────────────────────────────────────
function pausePipeline() {
  if (!isRunning || isPaused) return;
  engine.stopAll();
  setStatus("Paused");
  setPaused();
}

async function resumePipeline() {
  if (!isPaused) return;
  isPaused = false;
  setRunning();
  setStatus(`Tokens: ${tokenCount}`);
  const buf = pendingBuffer.splice(0);
  for (const event of buf) {
    if (isPaused) break;
    historyIndex = tokenHistory.indexOf(event);
    consumeEmitterPayload(event);
    engine.playNotes(auditionNotes(event.notes ?? []), modeSel.value, parseInt(bpmIn.value), currentEmitterControls);
    renderClusterVizStatic(event);
    renderTonalityPanel(event);
    renderEmitterInspector(event);
    highlightToken(historyIndex);
    tokenCount++;
    setStatus(`Tokens: ${tokenCount}`);
    if (modeSel.value === "timed") {
      await new Promise(r => setTimeout(r, 60000 / parseInt(bpmIn.value)));
    }
  }
  if (!isPaused && isDone && pendingBuffer.length === 0) setDone();
}

function navigatePrev() {
  if (historyIndex <= 0) return;
  historyIndex--;
  const event = tokenHistory[historyIndex];
  engine.stopAll();
  consumeEmitterPayload(event);
  engine.playNotes(auditionNotes(event.notes ?? []), modeSel.value, parseInt(bpmIn.value), currentEmitterControls);
  renderClusterVizStatic(event);
  renderTonalityPanel(event);
  renderEmitterInspector(event);
  highlightToken(historyIndex);
  btnPrev.disabled = historyIndex <= 0;
  btnNext.disabled = false;
  setStatus(`Token ${historyIndex + 1} / ${tokenHistory.length}`);
}

function navigateNext() {
  if (historyIndex >= tokenHistory.length - 1) return;
  historyIndex++;
  const event = tokenHistory[historyIndex];
  engine.stopAll();
  consumeEmitterPayload(event);
  engine.playNotes(auditionNotes(event.notes ?? []), modeSel.value, parseInt(bpmIn.value), currentEmitterControls);
  renderClusterVizStatic(event);
  renderTonalityPanel(event);
  renderEmitterInspector(event);

  // Append text span if this token was never live-rendered (arrived while paused)
  const textContent = document.getElementById("cv-text-content");
  if (textContent && !textContent.querySelector(`span[data-idx="${historyIndex}"]`)) {
    const span = document.createElement("span");
    span.dataset.idx = historyIndex;
    span.textContent = event.token || "";
    textContent.appendChild(span);
    const textBox = document.getElementById("cv-text-output");
    if (textBox) textBox.scrollTop = textBox.scrollHeight;
  }

  highlightToken(historyIndex);
  btnNext.disabled = historyIndex >= tokenHistory.length - 1;
  btnPrev.disabled = false;
  setStatus(`Token ${historyIndex + 1} / ${tokenHistory.length}`);
}

// ── Control wiring ─────────────────────────────────────────────────────────
function startPipeline() {
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  tokenHistory = [];
  historyIndex = -1;
  pendingBuffer = [];
  isPaused = false;
  isDone = false;
  resetClusterViz();
  engine.resume();
  engine.setVolume(parseFloat(volumeIn.value));
  startLoadingProgress();
  setRunning();
  sessionActive = true;
  ws.send(JSON.stringify({ action: "start", params: collectParams() }));
}

btnPlay.addEventListener("click", () => {
  if (isPaused) { resumePipeline(); }
  else { startPipeline(); }
});
btnPause.addEventListener("click", pausePipeline);
btnStop.addEventListener("click", () => {
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  engine.stopAll();
  isRunning = false;
  sessionActive = false;
  isPaused = false;
  pendingBuffer = [];
  ws.send(JSON.stringify({ action: "stop" }));
});
btnPrev.addEventListener("click", navigatePrev);
btnNext.addEventListener("click", navigateNext);
btnSend.addEventListener("click", startPipeline);

function sendParamUpdate(partial) {
  if (!sessionActive || !ws || ws.readyState !== WebSocket.OPEN) return;
  ws.send(JSON.stringify({ action: "update_params", params: partial }));
}

prompt.addEventListener("input", () => saveParams());
prompt.addEventListener("keydown", event => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") startPipeline();
});

modelSel.addEventListener("change", () => {
  populateLayerWidth(modelSel.value);
  saveParams();
});

layerSel.addEventListener("change", () => {
  updateObservationLayer(false);
  saveParams();
});
observationLayerIn.addEventListener("input", () => updateObservationLayer(true));
btnLayerPrev.addEventListener("click", () => {
  selectObservationLayer(
    stepObservationLayer(observationLayerIn.value, -1, currentModelInfo().observation_layers),
    true,
  );
});
btnLayerNext.addEventListener("click", () => {
  selectObservationLayer(
    stepObservationLayer(observationLayerIn.value, 1, currentModelInfo().observation_layers),
    true,
  );
});
widthSel.addEventListener("change", () => {
  updateObservationLayer(false);
  saveParams();
});

strategySel.addEventListener("change", () => {
  updateStrategyHelp();
  syncClustersVisibility();
  sendParamUpdate({ strategy: strategySel.value });
  saveParams();
});

clustersIn.addEventListener("input", () => { sendParamUpdate({ clusters: parseInt(clustersIn.value) }); saveParams(); });
maxTokensIn.addEventListener("input", () => { sendParamUpdate({ max_tokens: parseInt(maxTokensIn.value) }); saveParams(); });

modeSel.addEventListener("change", () => {
  updateModeHelp();
  syncBpmVisibility();
  sendParamUpdate({ mode: modeSel.value });
  saveParams();
});

bpmIn.addEventListener("input", () => { sendParamUpdate({ bpm: parseInt(bpmIn.value) }); saveParams(); });
loopCb.addEventListener("change", () => { sendParamUpdate({ loop: loopCb.checked }); saveParams(); });

oscEnabledCb.addEventListener("change", () => {
  syncOscControls();
  scheduleOscUpdate(0);
});

oscHostIn.addEventListener("input", () => { syncOscControls(); scheduleOscUpdate(); });
oscHostIn.addEventListener("change", () => scheduleOscUpdate(0));

oscPortIn.addEventListener("input", () => { syncOscControls(); scheduleOscUpdate(); });
oscPortIn.addEventListener("change", () => {
  oscPortIn.value = boundedIntValue(oscPortIn, 9000, 1, 65535);
  syncOscControls();
  scheduleOscUpdate(0);
});

oscMaxNotesIn.addEventListener("input", () => { syncOscControls(); scheduleOscUpdate(); });
oscMaxNotesIn.addEventListener("change", () => {
  oscMaxNotesIn.value = boundedIntValue(oscMaxNotesIn, 32, 1, 128);
  scheduleOscUpdate(0);
});

volumeIn.addEventListener("input", () => {
  engine.setVolume(parseFloat(volumeIn.value));
  updateVolumeValue();
  saveParams();
});

tonalityEnabledCb.addEventListener("change", () => {
  syncTonalityControls();
  sendParamUpdate({ tonality_enabled: tonalityEnabledCb.checked });
  saveParams();
});

promptInfluenceIn.addEventListener("input", () => {
  updateTonalityControlValues();
  sendParamUpdate({ prompt_influence: parseFloat(promptInfluenceIn.value) });
  saveParams();
});

tonalityPitchBiasIn.addEventListener("input", () => {
  updateTonalityControlValues();
  sendParamUpdate({ tonality_pitch_bias: parseFloat(tonalityPitchBiasIn.value) });
  saveParams();
});

btnRawSound.addEventListener("click", () => setInterpretationBlend(0));
btnInterpretedSound.addEventListener("click", () => setInterpretationBlend(1));

btnAddLens.addEventListener("click", () => {
  tonalityCatalogue.push({
    name: "new lens",
    description: "type a sonic-interpretive description",
    intervals: [0, 2, 7],
    root: 0,
    enabled: true,
  });
  expandedLensIndex = tonalityCatalogue.length - 1;
  renderLensEditor();
  scheduleLensUpdate(0);
});

btnResetLenses.addEventListener("click", () => {
  tonalityCatalogue = structuredClone(defaultTonalityCatalogue);
  expandedLensIndex = 0;
  renderLensEditor();
  scheduleLensUpdate(0);
});

for (const tab of document.querySelectorAll("[data-workspace-tab]")) {
  tab.addEventListener("click", () => setWorkspace(tab.dataset.workspaceTab));
}

btnControlsToggle.addEventListener("click", () => {
  setInterfaceDrawer("controls", btnControlsToggle.getAttribute("aria-expanded") !== "true");
});
btnControlsClose.addEventListener("click", () => setInterfaceDrawer(null, false));
btnTonalityToggle.addEventListener("click", () => {
  setInterfaceDrawer("tonality", btnTonalityToggle.getAttribute("aria-expanded") !== "true");
});
btnTonalityClose.addEventListener("click", () => setInterfaceDrawer(null, false));
drawerBackdrop.addEventListener("click", () => setInterfaceDrawer(null, false));
document.addEventListener?.("keydown", event => {
  if (event.key === "Escape") setInterfaceDrawer(null, false);
});

btnAddMapping.addEventListener("click", () => {
  const maximum = mappingCatalogue.max_mappings || 32;
  if (emitterMappings.length >= maximum) return;
  emitterMappings.push(completeMapping());
  renderMappingEditor();
  scheduleMappingUpdate(0);
});

btnResetMappings.addEventListener("click", () => {
  emitterMappings = structuredClone(defaultEmitterMappings);
  renderMappingEditor();
  scheduleMappingUpdate(0);
});

btnClearMappings.addEventListener("click", () => {
  emitterMappings = [];
  renderMappingEditor();
  scheduleMappingUpdate(0);
});

btnApplyTemplate.addEventListener("click", () => {
  emitterMappings = templateMappings(mappingTemplate.value);
  renderMappingEditor();
  scheduleMappingUpdate(0);
});

btnSaveScene.addEventListener("click", () => {
  const name = sceneName.value.trim();
  if (!name) return;
  const scene = captureScene(name);
  const existingIndex = instrumentScenes.findIndex(item => item.name.toLowerCase() === name.toLowerCase() && !item.builtin);
  if (existingIndex >= 0) {
    scene.id = instrumentScenes[existingIndex].id;
    instrumentScenes[existingIndex] = scene;
  } else {
    instrumentScenes.push(scene);
  }
  sceneName.value = "";
  saveScenes();
  renderSceneSelectors();
  sceneSelect.value = scene.id;
});

btnLoadScene.addEventListener("click", () => applyScene(sceneById(sceneSelect.value)));

btnDeleteScene.addEventListener("click", () => {
  const scene = sceneById(sceneSelect.value);
  if (!scene || scene.builtin) return;
  instrumentScenes = instrumentScenes.filter(item => item.id !== scene.id);
  saveScenes();
  renderSceneSelectors();
});

sceneMorph.addEventListener("input", applySceneMorph);
sceneA.addEventListener("change", applySceneMorph);
sceneB.addEventListener("change", applySceneMorph);
featureSearch.addEventListener("input", renderFeatureBrowser);
signalCatalogueSearch.addEventListener("input", renderSignalExplorer);

for (const filterButton of document.querySelectorAll("[data-signal-filter]")) {
  filterButton.addEventListener("click", () => {
    signalCatalogueKindFilter = filterButton.dataset.signalFilter || "all";
    for (const item of document.querySelectorAll("[data-signal-filter]")) {
      item.classList.toggle("active", item === filterButton);
    }
    renderSignalExplorer();
  });
}

btnDefaultSignals.addEventListener("click", () => {
  selectedEmitterSignalKeys = new Set(defaultEmitterSignalKeys);
  sendSignalSelectionUpdate();
});

btnClearSignals.addEventListener("click", () => {
  selectedEmitterSignalKeys = new Set();
  sendSignalSelectionUpdate();
});

visualProofPanel.addEventListener("toggle", () => {
  if (!visualProofPanel.open) return;
  requestAnimationFrame(() => {
    const clusterCanvas = document.getElementById("cluster-canvas");
    if (clusterCanvas) drawClusterBars(clusterCanvas, lastRenderedNotes);
    applyVisualControls();
  });
});

if (window.addEventListener) {
  window.addEventListener("resize", () => {
    renderDenseState();
    renderSparseState();
  });
}

// ── Init ───────────────────────────────────────────────────────────────────
loadOptions();
connectWS();
drawWaveformFrame();
