# Feature Backlog

Each item below is a self-contained feature for this branch. The current user
priority takes precedence over the older numeric ordering.

## Completed

- Live waveform: the browser audio graph now connects through a Web Audio API
  `AnalyserNode`, and the new GUI waveform canvas renders
  `getFloatTimeDomainData()` in real time.
- Live performance tonal lenses: editable verbal tonality descriptions and
  intervals can be changed from the GUI before or during generation; raw versus
  interpreted pitch blend is exposed; token payloads include run-level tonality
  memory and active-feature evidence.

## Current priority: Ableton OSC bridge

- **Ubuntu GPU PC (complete):** optional, live-configurable `/rai/v1` OSC
  emission is implemented and verified against a local UDP receiver.
- **Windows laptop (next):** implement the Max for Live/ossia receiver in a
  separate task and clone/branch.
- **Integration:** test both computers over the LAN after each side works alone.
- Do not treat Git worktrees as a cross-computer synchronization mechanism.

## 1. Image generation placeholder → actual image
The bottom-right panel is currently a static placeholder.
- Generate an image that encodes the SAE feature activations visually (e.g. scatter plot of active features by cluster, heatmap of activations over tokens, or a t-SNE/UMAP projection).
- Could also call an external image generation API conditioned on the generated text.
- Decide approach when implementing.

## 2. Neuronpedia download progress
The initial model + SAE + Neuronpedia load can take 30–60 s. Add a proper progress bar in the UI fed by server-sent `loading` events, showing each stage (model load, SAE load, Neuronpedia cache hit/download).

## 3. Session history & replay
- Save each completed run (prompt + all token events) to `runs/` as NDJSON.
- Add a "History" panel in the UI to list past runs and replay them without re-running the model.
- Reuse the existing `export.py` / `runs/` convention.

## 4. Instrument attribution per cluster 
- in a scroll box, display for each cluster:
  - the number of the cluster
  - which sound pack it plays (not clear how to do that at all, must be defined but the idea is to select which instrument is playing what is represented by this cluster)
  - the names of the features that were activated that are part of this cluster (to get a sense of what it represents)
