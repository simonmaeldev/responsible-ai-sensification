// rai_pipeline_figure.typ
// Figure: RAI Sensification — cluster sonification pipeline
// For use in poster and scientific paper.

#set page(width: 18cm, height: auto, margin: (x: 0.8cm, y: 0.8cm))
#set text(size: 8.5pt, font: "New Computer Modern")
#set par(justify: false)

// ── Colour palette ──────────────────────────────────────────────
#let c-in  = rgb("#DBEAFE") // light blue   — input / prompt
#let c-llm = rgb("#FEF9C3") // light yellow — LLM internals
#let c-sae = rgb("#DCFCE7") // light green  — SAE / features
#let c-np  = rgb("#F3E8FF") // light purple — Neuronpedia / clustering
#let c-map = rgb("#FDE8F3") // light pink   — audio mappings
#let c-out = rgb("#CCFBF1") // light teal   — audio output
#let bd    = 0.6pt + rgb("#6B7280")

// ── Helpers ─────────────────────────────────────────────────────
#let nd(content, fill: white) = rect(
  fill: fill, stroke: bd, radius: 3pt,
  inset: (x: 6pt, y: 5pt),
  align(center, content),
)

#let rarr = box(inset: (x: 5pt), text(size: 11pt)[→])
#let darr = pad(y: 2pt, align(center, text(size: 11pt)[↓]))

// ── Figure ──────────────────────────────────────────────────────
#figure(
  caption: [
    *RAI Sensification pipeline — cluster sonification method.*
    A text prompt drives an LLM autoregressively.
    At each new token the residual stream at layer $ell$ is encoded by a
    Sparse Autoencoder (SAE, JumpReLU) into ~65 k sparsely activated
    features $(i, a_i)$.
    Three independent mappings convert the active features into musical
    parameters: semantic clustering (via Neuronpedia descriptions +
    sentence embeddings + KMeans) determines the instrument timbre; the
    feature index within its cluster sets the log-scaled frequency; and
    the activation strength sets the amplitude.
    All notes are mixed by additive synthesis into an audio segment of
    0.5 s per token.
  ],
)[
  #set text(size: 8pt)

  // ── Row 1 — LLM generation ────────────────────────────────────
  #align(center, stack(dir: ltr, spacing: 0pt,
    nd([*Prompt*], fill: c-in),
    rarr,
    nd([*LLM* \ Gemma-3 1B], fill: c-llm),
    rarr,
    nd([Residual stream \ *layer* $ell$], fill: c-llm),
    rarr,
    nd([*SAE* (JumpReLU) \ ~65 k features], fill: c-sae),
    rarr,
    nd([Active features \ $brace.l (i, a_i) brace.r$], fill: c-sae),
  ))

  #v(2pt)
  #align(center, text(size: 7pt, fill: rgb("#9CA3AF"))[
    ↺ autoregressive loop — one new token at a time
  ])
  #v(10pt)

  // ── Row 2 — Three parallel feature→sound mappings ─────────────
  #grid(columns: (1fr, 1fr, 1fr), gutter: 8pt,

    // ── A: semantic clustering → instrument timbre ──
    stack(spacing: 4pt,
      nd([*Neuronpedia* \ feature description text], fill: c-np),
      darr,
      nd([Sentence embedding \ (all-MiniLM-L6-v2)], fill: c-np),
      darr,
      nd([MiniBatch KMeans \ $k$ semantic clusters], fill: c-np),
      darr,
      nd([*Instrument* (timbre) \ piano · guitar · bell · …], fill: c-map),
    ),

    // ── B: feature index → frequency ──
    stack(spacing: 4pt,
      nd([Feature index $i$ \ within cluster], fill: c-sae),
      darr,
      nd([
        Log-scale mapping \
        $f_i = f_"min" dot (f_"max" / f_"min")^(i \/ N)$
      ], fill: c-map),
      darr,
      nd([*Frequency* \ 20 Hz – 20 000 Hz], fill: c-map),
    ),

    // ── C: activation strength → amplitude ──
    stack(spacing: 4pt,
      nd([Activation strength $a_i$], fill: c-sae),
      darr,
      nd([Direct proportional \ mapping], fill: c-map),
      darr,
      nd([*Amplitude* (volume)], fill: c-map),
    ),
  )

  #v(10pt)

  // ── Row 3 — Additive synthesis ────────────────────────────────
  #align(center, stack(dir: ltr, spacing: 0pt,
    nd([*Additive synthesis* \ $sum$ instrument waveforms per token], fill: c-out),
    rarr,
    nd([*Audio output* \ 0.5 s / token · WAV or live], fill: c-out),
  ))

  // ── Colour legend ─────────────────────────────────────────────
  #v(10pt)
  #line(length: 100%, stroke: 0.5pt + rgb("#D1D5DB"))
  #v(4pt)
  #set text(size: 7pt, fill: rgb("#6B7280"))
  #align(center, grid(columns: (auto, auto, auto, auto, auto), gutter: 10pt,
    rect(fill: c-in,  stroke: bd, inset: 3pt, radius: 2pt)[ Input ],
    rect(fill: c-llm, stroke: bd, inset: 3pt, radius: 2pt)[ LLM internals ],
    rect(fill: c-sae, stroke: bd, inset: 3pt, radius: 2pt)[ SAE / features ],
    rect(fill: c-np,  stroke: bd, inset: 3pt, radius: 2pt)[ Neuronpedia / clustering ],
    rect(fill: c-map, stroke: bd, inset: 3pt, radius: 2pt)[ Audio mapping ],
  ))
]
