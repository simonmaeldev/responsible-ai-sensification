# RAI OSC Receiver for Max for Live

This is the Windows Phase 5B receiver for the `/rai/v1` contract documented in
`../../specs/ableton-osc-bridge.md`.

## Requirements

- Ableton Live 12 Suite with bundled Max 9.
- The official ossia Max package installed in Max 9's user `Packages` folder.

The receiver does not run Gemma or SAE inference. The Ubuntu GPU PC remains the
remote OSC source.

## Source Files

- `RAI OSC Receiver.maxpat`: editable receiver and Max for Live source.
- `rai_osc_receiver.js`: OSC validation, token-frame grouping, diagnostics, and
  voice allocation.
- `rai_receiver_panel.js`: presentation-mode diagnostic display.
- `rai_ossia_namespace.maxpat`: typed, queryable receiver namespace.
- `rai_osc_voice.maxpat`: one bounded preview voice used by `poly~`.

## Local Max Test

1. Open `RAI OSC Receiver.maxpat` in the bundled Max editor.
2. Confirm the display says `LISTENING UDP 9000`.
3. Turn on the local preview speaker only when you want standalone audio.
4. Run:

   ```powershell
   powershell -ExecutionPolicy Bypass -File tools\send_osc_loopback.ps1
   ```

5. Inspect the receiver panel and the OSCQuery tree at
   `http://127.0.0.1:5679/`.

The test frequency `445.125` should appear unchanged in
`/status/last_frequency` and on the receiver panel.

Ableton's command-line Max Runtime can validate the native UDP listener, but it
does not discover separately installed user packages. Open the receiver through
Live's **Edit in Max** host for the ossia/OSCQuery check.

## Ableton Device Packaging

`.amxd` is a Max-generated container, not a JSON file that should be created or
renamed by hand. After the source patch passes standalone verification:

1. Open the patch in Max from Live's **Edit in Max** workflow or open it in the
   bundled editor.
2. Save it as a Max Audio Effect named `RAI OSC Receiver.amxd`.
3. Keep the JavaScript and voice files beside the device, or freeze the device
   in Max before distributing it.
4. Load a single receiver instance in Live for the initial test. Multiple
   instances would compete for UDP port 9000 and OSCQuery ports 9011/5679.

The receiver mixes a bounded preview synth with an audio-effect pass-through.
Master gain affects only the preview synth.

## Network Test

For the later two-machine test, enter the Windows laptop's current LAN IPv4 in
the Ubuntu browser's OSC destination and use UDP port 9000. UDP is connectionless:
`listening` and `receiving` are accurate states; there is no handshake.
