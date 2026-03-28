"use strict";

// ── WebAudioEngine ─────────────────────────────────────────────────────────
class WebAudioEngine {
  constructor() {
    this._audioCtx   = null;
    this._masterGain = null;
    this._activeNodes = [];
  }

  resume() {
    if (!this._audioCtx) {
      this._audioCtx   = new AudioContext();
      this._masterGain = this._audioCtx.createGain();
      this._masterGain.gain.value = 1.0;
      this._masterGain.connect(this._audioCtx.destination);
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
      g.connect(this._masterGain);
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

  playNotes(notes, mode, bpm) {
    if (!this._audioCtx || !notes.length) return;

    const maxAmp     = Math.max(...notes.map(n => n.amplitude ?? 0), 1);
    const durationSec = mode === "timed" ? 60 / bpm : null;
    const startTime  = this._audioCtx.currentTime;
    const stopTime   = durationSec !== null ? startTime + durationSec : null;

    if (mode === "sustain") this.stopAll();

    for (const note of notes) {
      const newNodes = this._buildNoteGraph(
        note.freq      ?? 440,
        (note.amplitude ?? 0) / maxAmp,
        note.instrument ?? "default",
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
}

// ── State ──────────────────────────────────────────────────────────────────
const engine = new WebAudioEngine();
let ws = null;
let isRunning = false;
let tokenCount = 0;
let catalogue = {};        // modelId -> { layers: [...], widths: [...] }
let strategyDescs = {};    // value -> description
let modeDescs = {};        // value -> description

// Transport / history state
let isPaused = false;
let tokenHistory = [];   // all token events received since last start
let historyIndex = -1;   // index into tokenHistory currently shown; -1 = none
let pendingBuffer = [];  // tokens received while paused, not yet played
let isDone = false;      // generation finished (but session not stopped)

// Cluster viz state
let cvPalette = [];       // [{cluster_id, name, color}] ordered by PCA

// ── Local storage ──────────────────────────────────────────────────────────
const STORAGE_KEY = "sae_ui_params";

function saveParams() {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(collectParams())); } catch {}
}

function loadSavedParams() {
  try { const raw = localStorage.getItem(STORAGE_KEY); return raw ? JSON.parse(raw) : null; } catch { return null; }
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
const volumeIn        = document.getElementById("volume");

// ── Load options + defaults ─────────────────────────────────────────────────
async function loadOptions() {
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

  const saved = loadSavedParams();
  if (saved) applyParams(saved);
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
}

function updateStrategyHelp() {
  strategyHelp.dataset.tooltip = strategyDescs[strategySel.value] ?? "";
}

function updateModeHelp() {
  modeHelp.dataset.tooltip = modeDescs[modeSel.value] ?? "";
}

function applyParams(p) {
  if (p.prompt     !== undefined) prompt.value       = p.prompt;
  if (p.model      !== undefined) modelSel.value     = p.model;
  if (p.layer      !== undefined) layerSel.value     = p.layer;
  if (p.width      !== undefined) widthSel.value     = p.width;
  if (p.strategy   !== undefined) { strategySel.value = p.strategy; updateStrategyHelp(); }
  if (p.clusters   !== undefined) clustersIn.value   = p.clusters;
  if (p.max_tokens !== undefined) maxTokensIn.value  = p.max_tokens;
  if (p.mode       !== undefined) { modeSel.value = p.mode; updateModeHelp(); }
  if (p.bpm        !== undefined) bpmIn.value        = p.bpm;
  if (p.loop       !== undefined) loopCb.checked     = p.loop;

  // Sync conditional visibility
  if (p.strategy !== undefined) syncClustersVisibility();
  if (p.mode     !== undefined) syncBpmVisibility();
}

// ── Collect current params ─────────────────────────────────────────────────
function collectParams() {
  return {
    prompt:     prompt.value,
    model:      modelSel.value,
    layer:      parseInt(layerSel.value),
    width:      widthSel.value,
    strategy:   strategySel.value,
    clusters:   parseInt(clustersIn.value),
    max_tokens: parseInt(maxTokensIn.value),
    mode:       modeSel.value,
    bpm:        parseInt(bpmIn.value),
    loop:       loopCb.checked,
  };
}

// ── Conditional visibility ─────────────────────────────────────────────────
function syncClustersVisibility() {
  clustersGroup.classList.toggle("hidden", strategySel.value !== "cluster");
}

function syncBpmVisibility() {
  bpmGroup.classList.toggle("hidden", modeSel.value !== "timed");
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
  ws.onclose = () => { ws = null; setIdle(); };
}

function handleMessage(msg) {
  switch (msg.type) {
    case "ready":
      applyParams(msg.params);
      setStatus("Connected — ready");
      break;

    case "loading":
      setStatus(msg.stage);
      break;

    case "cluster_palette":
      cvPalette = msg.palette || [];
      renderColorStrip();
      break;

    case "token":
      tokenHistory.push(msg);
      if (isPaused) {
        pendingBuffer.push(msg);
        break;
      }
      tokenCount++;
      historyIndex = tokenHistory.length - 1;
      setStatus(`Tokens: ${tokenCount}`);
      if (msg.loop_count !== undefined) {
        loopCountEl.textContent = `Loop: ${msg.loop_count}`;
        loopCountEl.classList.remove("hidden");
      }
      engine.playNotes(msg.notes ?? [], modeSel.value, parseInt(bpmIn.value));
      renderClusterViz(msg);
      highlightToken(historyIndex);
      break;

    case "done":
      setStatus(`Done (${tokenCount} tokens) — loop or send a new prompt`);
      if (historyIndex === -1) resetClusterViz();
      setDone();
      break;

    case "silent":
      engine.stopAll();
      setStatus("Silent");
      break;

    case "stopped":
      engine.stopAll();
      setIdle();
      resetClusterViz();
      break;

    case "error":
      setStatus(`Error: ${msg.message}`);
      setIdle();
      break;
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
    const barH = (note.amplitude / maxAmp) * H;
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
  btnSend.disabled  = true;
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
  btnStop.disabled  = true;
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
    engine.playNotes(event.notes ?? [], modeSel.value, parseInt(bpmIn.value));
    renderClusterVizStatic(event);
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
  engine.playNotes(event.notes ?? [], modeSel.value, parseInt(bpmIn.value));
  renderClusterVizStatic(event);
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
  engine.playNotes(event.notes ?? [], modeSel.value, parseInt(bpmIn.value));
  renderClusterVizStatic(event);
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
  engine.resume();
  engine.setVolume(parseFloat(volumeIn.value));
  setRunning();
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
  isPaused = false;
  pendingBuffer = [];
  ws.send(JSON.stringify({ action: "stop" }));
});
btnPrev.addEventListener("click", navigatePrev);
btnNext.addEventListener("click", navigateNext);
btnSend.addEventListener("click", startPipeline);

function sendParamUpdate(partial) {
  if (!isRunning || !ws || ws.readyState !== WebSocket.OPEN) return;
  ws.send(JSON.stringify({ action: "update_params", params: partial }));
}

prompt.addEventListener("input", () => saveParams());

modelSel.addEventListener("change", () => {
  populateLayerWidth(modelSel.value);
  sendParamUpdate({ model: modelSel.value });
  saveParams();
});

layerSel.addEventListener("change", () => { sendParamUpdate({ layer: parseInt(layerSel.value) }); saveParams(); });
widthSel.addEventListener("change", () => { sendParamUpdate({ width: widthSel.value }); saveParams(); });

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

volumeIn.addEventListener("input", () => engine.setVolume(parseFloat(volumeIn.value)));

// ── Init ───────────────────────────────────────────────────────────────────
loadOptions();
connectWS();
