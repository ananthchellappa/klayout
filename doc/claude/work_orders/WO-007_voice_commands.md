# WO-007: Voice commands

| | |
|---|---|
| Status | **Plan**: not started, needs user review |
| Written | 2026-10-27 |
| Effort | Step 0 ~1 h; Phase A ~2–3 days; Phase B ~1 week; Phase C open-ended |
| Touches | Phase A: a separate helper program + a `.lym` macro, no KLayout source changes. Phase B: new `src/plugins/tools/voice/` |
| Depends on | Nothing to start. Better with WO-005 (journal) so voice commands get logged |

## Goal

1. Settings → "Enable voice commands". The first time, KLayout asks: **"KLayout wants to access your microphone. Allow?"** Allow / Don't allow, remembered, revocable in Setup.
2. Then simple spoken commands work: "zoom fit", "zoom in", "pan left", "undo", "show only metal one", "hide poly", "open cell inverter", "run DRC", "save". Later, "probe net out", via the Xschem cross-probe (WO-003).
3. You always see what was heard ("Heard: zoom fit → Zoom Fit") and nothing destructive happens without confirmation.

## How to pull it off: the recommended architecture

```
 microphone ─▶ [ voice helper process ]  ──JSON lines on stdout──▶  [ KLayout voice macro/plugin ]
               audio capture                                         consent dialog, start/stop helper
               push-to-talk / VAD                                    grammar from current layout
               Vosk recognizer (grammar-restricted)                  intent → call_menu / pya API
                     ▲                                               status-bar feedback, journal
                     └──────────── grammar updates on stdin ◀───────
```

**Recognize out of process, act in process.** KLayout starts the helper with `QProcess` (no network port, it dies with KLayout) and reads one JSON line per utterance: `{"text":"zoom fit","conf":0.93}`. Reasons:
- KLayout's embedded Python never releases the GIL (see FAQ Q9). A recognizer running inside it would stutter the UI. Out of process, it can't.
- The helper can use any Python and any wheels (Vosk, sounddevice) in its own venv, independent of KLayout's Python 3.14.
- **The same helper can drive Xschem** (send intents over Xschem's loopback Tcl socket). One voice front-end for the whole Layout-XL flow.
- A crash in audio or ASR code can't take down a layout session.

**Speech engine: Vosk, in grammar mode.** Recommended for commands:
- Offline: nothing leaves the machine, no account, no cost. Apache-2.0. The small English model is about 40 MB and runs in real time on one CPU core.
- It accepts a **phrase list at runtime** (`KaldiRecognizer(model, rate, '["zoom fit", "zoom in", …, "[unk]"]')`). Restricting it to the command vocabulary is what makes command recognition accurate and fast. The list is rebuilt whenever the layout changes, so it includes the current layer names ("metal one" ↔ `met1`, "local interconnect" ↔ `li1`) and cell names.
- Alternative for later free-form speech ("move this up two microns"): whisper.cpp (MIT), `base.en`/`small.en`. More accurate on open vocabulary, but heavier (~0.5–1 s per utterance on CPU) and can't be constrained by grammar. Keep the helper's interface engine-neutral so either can be plugged in.
- Cloud ASR (Google, Azure, OpenAI): possible, but it streams lab audio off the machine and needs keys. Not recommended as the default.

**Listening mode: push-to-talk first.** Hold a key (default: Space-bar long-press is risky in an editor, so use something like `` ` `` or F12; configurable) → speak → release. Always-listening in an editor that's open all day will misfire. Add a wake word ("KLayout, zoom fit") as an option later, with Vosk's `[unk]` rejection and a confidence threshold.

**The microphone permission pop-up.** Two layers:
- KLayout's own consent dialog (a `QMessageBox`, stored as config `voice-mic-consent = granted|denied`). This is what you described, and it's the only prompt you get on Linux: Linux has no OS-level microphone permission.
- On native Windows/macOS builds, also call Qt 6's `QCoreApplication::requestPermission (QMicrophonePermission)` (available in our Qt 6.10.2; not exposed in the Python Qt bindings, so this part is C++, Phase B) so the OS prompt appears too.
- **On your WSL2 setup**, audio comes through WSLg's PulseAudio bridge (`PULSE_SERVER=unix:/mnt/wslg/PulseServer`, present on this machine). Windows decides mic access for WSLg: Settings → Privacy & security → Microphone → "Let desktop apps access your microphone" must be on. Windows shows its mic-in-use indicator while the helper listens. Push-to-talk means the helper opens the mic only while the key is held, so the indicator matches reality.

**Intent mapping (in KLayout).** A small table, not an AI model:

| Spoken | Action |
|---|---|
| zoom fit / fit | `mw.call_menu("cm_zoom_fit")` |
| zoom in / zoom out | `cm_zoom_in` / `cm_zoom_out` |
| pan left/right/up/down | `cm_pan_left` … |
| undo / redo | `cm_undo` / `cm_redo` |
| show only ‹layer› / hide ‹layer› / show all | iterate `view.each_layer()`, set `visible` |
| open cell ‹name› | `view.active_cellview().cell_name = …` |
| select layer ‹layer› | set current layer in the layer panel |
| save | `cm_save` (confirm) |
| run DRC | run the sky130 DRC macro (confirm) |
| probe net ‹name› | WO-003 cross-probe |

Layer spoken forms come from the sky130 layer names plus a small alias file (`met1` = "metal one", "M one"; `li1` = "L I", "local interconnect"; `poly`; `diff`), kept in an init file, user-editable like a Virtuoso bindkey file. Destructive or slow commands ask "Run DRC? (say yes / press Enter)".

## Phases

**Step 0 — prove the audio path on this machine (do first, ~1 h).**
- `sudo apt install pulseaudio-utils` (not installed yet), then `pactl list short sources` and `parecord --channels=1 --rate=16000 /tmp/x.wav` → play it back. If no source shows up, fix the Windows privacy setting / WSLg before anything else.
- In a venv: `pip install vosk sounddevice`, download `vosk-model-small-en-us-0.15`, run a 20-line test that prints recognised text for a fixed phrase list. **Not verified yet:** Vosk wheel availability for the venv's Python version; use Python 3.12 for the helper venv if 3.14 has no wheel.

**Phase A — working prototype, no KLayout source changes.**
- `voice_helper.py` (helper process: capture, push-to-talk gating via a stdin "listen"/"stop" message, Vosk, JSON out, grammar updates in).
- `voice.lym` autorun macro: menu item Tools → Voice Commands (on/off), consent dialog, `QProcess` management, intent table, status-bar feedback, a global push-to-talk shortcut via `set_key_bindings`.
- Measure: latency from key release to action (target < 500 ms), accuracy on the command list.

**Phase B — native plugin.** Move the KLayout side to C++ in `src/plugins/tools/voice/` (a `lay::PluginDeclaration` with config page in Setup): proper settings page (device, key, threshold, aliases file), `QMicrophonePermission` request, journal integration (WO-005). Helper stays a separate process.

**Phase C — richer commands.** Numbers and units ("move up two microns", "set grid five nanometers"), selection-relative commands, Xschem side ("in schematic, select M3"), whisper.cpp for free-form.

## Acceptance (Phase A)

- [ ] First enable shows the consent dialog; "Don't allow" leaves the mic untouched (helper never started); the choice persists across restarts and can be reset.
- [ ] Hold push-to-talk, say "zoom fit" → view zooms fit within 0.5 s of release; status bar shows "Heard: zoom fit".
- [ ] "show only metal one" on a sky130 layout leaves only `met1` visible.
- [ ] Unrecognised speech → "Didn't catch that", no action.
- [ ] 20 trials of each of 10 commands: ≥ 95 % correct, 0 wrong destructive actions.
- [ ] Killing the helper doesn't affect KLayout; the macro reports it and offers restart.
- [ ] UI stays responsive (no stutter while panning during recognition).

## Security / privacy

- Audio never leaves the machine with Vosk/whisper.cpp; no recordings are stored unless a debug flag is set.
- The helper talks to KLayout over its own stdin/stdout, no sockets. If it later drives Xschem, that is Xschem's loopback-only socket (see WO-003; Xschem evaluates any Tcl it receives, so never bind it beyond localhost).
