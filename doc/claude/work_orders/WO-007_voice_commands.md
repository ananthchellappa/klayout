# WO-007: Voice commands for forms and precise geometry

| | |
|---|---|
| Status | **Plan**: scope agreed 2026-10-29, not started |
| Written | 2026-10-27, rewritten 2026-10-29 |
| Scope | Group 1 (fill a form in one sentence) and Group 2 (precise geometry). Answers on screen only. |
| Effort | Step 0 ~half a day; Phase A ~1–2 weeks; Phase B ~2 weeks |
| Touches | Phase A: a helper program plus a `.lym` macro, no KLayout source changes. Phase B: `src/plugins/tools/voice/` (C++) |
| Related | WO-005 (journal: every voice action is logged); WO-003 (cross-probe, later groups) |

## 1. Principle

Voice is for what the hand does slowly: going two menus deep and filling in a form, or clicking somewhere exact. It is **not** for single-key actions (F2, Ctrl+Z); those stay on the keyboard and the plan deliberately leaves them out.

Mouse and voice work together. The mouse says **where** ("here", "this"); the voice says **what** and **how much**.

## 2. First command set

### Group 1: fill a form in one sentence

All of these use the `skywater130` PCell library (PCells verified to exist: `nfet`, `pfet`, `res_poly`, `mim_cap`, `vias_gen`, `guard_ring_gen`, plus others under `cells/`).

| Say | Does | Replaces |
|---|---|---|
| "Place nfet, W 2, L 0.15, 4 fingers, here" | PCell instance with those parameters at the cursor | Libraries drag → PCell form → 3 fields → OK |
| "Place pfet W 4 L 0.5 here, rotate 90" | same, with orientation | as above + rotate |
| "Array this 4 by 2, pitch 5 by 3" | turns the selected instance into a 4×2 array, pitch 5 µm × 3 µm | Object Properties → array fields |
| "Via stack met1 to met4 here, 2 by 2" | `vias_gen` instance | PCell form |
| "Guard ring around this, p-tap" | `guard_ring_gen` sized to the selection bbox plus margin | measure, PCell form, place |
| "Poly resistor, W 1, L 10, here" | `res_poly` | PCell form |
| "Pin VOUT on met2 here" | text `VOUT` on the met2 pin/label layer at the cursor | text tool + layer pick + typing |
| "Set W to 3" / "make it 6 fingers" | changes parameters of the selected PCell | Object Properties form |

### Group 2: precise geometry

| Say | Does |
|---|---|
| "Move up 0.34" / "move left 2 grid" | move selection by a delta (µm, nm, or grid steps) |
| "Move to 10, 20" | move selection so its reference point (origin or bbox lower-left, configurable) lands on (10, 20) |
| "Box on met2 from 0, 0 to 5, 1.4" | exact rectangle |
| "Box on met1 here, 2 by 0.5" | rectangle of that size centred on the cursor |
| "Stretch right edge to 12.5" | moves the selected shape's right edge to x = 12.5 |
| "Make this 0.28 wide" | path width, or box width, of the selection |
| "Align left edges" / "align centres vertically" | aligns the selected objects |
| "Space these 2 microns apart" | distributes the selection with 2 µm gaps |
| "Mirror about Y" / "rotate 90" | transforms the selection about its centre |
| "Copy right 5, 3 times" | three copies at 5 µm steps |

**Units.** µm is the default. Accept "nanometres"/"nano", "microns"/"um", "grid". Every number is shown back with its unit.

## 3. Robustness and fault tolerance (the core requirement)

The rule: **a misheard command can cost a correction, never a silent layout error.**

1. **Nothing runs without confirmation.** Every recognised command opens a **preview card** (a small panel near the cursor) and a **ghost** of the result drawn in the layout (`pya.Marker`: the outline of the PCell to be placed, the moved shape at its new place).
   - The card lists each field: `Place nfet · W = 2 µm · L = 0.15 µm · nf = 4 · at (12.305, 4.500) · R0`.
   - Enter or "yes" runs it. Esc or "no" discards it.
   - Fields can be corrected by **voice** ("no, W 3"), which edits the card without starting over, or by **keyboard** (Tab into the field).
2. **One command = one undo step.** Each confirmed action runs inside `view.transaction("Voice: …")` / `commit`, so a single Ctrl+Z reverts all of it, even an array or a guard ring.
3. **Validate before preview, against the PDK.**
   - Parameter ranges come from the PCell declaration and sky130 rules: nfet_01v8 L ≥ 0.15, W ≥ 0.42 (to be read from the deck/PCell, not hard-coded).
   - Coordinates snap to the manufacturing grid (5 nm), and the card says so ("12.3071 → 12.305").
   - A layer that doesn't exist, or a command that needs a selection when nothing is selected, is shown as an error on the card, not executed.
4. **Ambiguous numbers are flagged, not guessed.** "Two point eight" vs "twenty-eight", "fifteen" vs "fifty", "point one five" vs "one five". The card highlights a number when the recogniser's alternatives disagree on it and shows the alternative ("2.8 · or 28?"). Implausible values are flagged too (W = 28 for an nfet in a 2 µm-wide area).
5. **Freeze the context when you start talking.** Pressing push-to-talk snapshots the cursor position (in µm), the current cell and the selection. "Here" and "this" refer to that snapshot even if the mouse moves while you speak. If the selection changes before you confirm, the card is invalidated.
6. **Never execute a partial parse.** If any required slot is missing or below the confidence threshold, the card shows it empty and red, and waits.
7. **Engine failover.** If the cloud STT doesn't answer within a timeout (default 3 s) or errors, fall back to the local engine automatically and say so on the card. The local engine is always installed, so voice keeps working offline.
8. **Process isolation.** Audio and STT run in a separate helper process. If it crashes or hangs, KLayout is unaffected, the macro reports it and restarts it (with back-off).
9. **Everything is logged** for debugging: transcript, alternatives, parsed command, the action taken, and the journal line (WO-005). Audio is saved only with a debug switch.
10. **Regression tests.** A text corpus (`utterance → expected command`) runs through the parser in CI with no audio. A small recorded-audio set of your own voice measures end-to-end accuracy when engines or models change.

## 4. Architecture

```
 mic ─▶ helper process ──────────────────────────────▶ KLayout (macro, later C++ plugin)
        capture (push-to-talk)                          consent dialog, start/supervise helper
        STT engine: local | cloud  (+ failover)          context snapshot (cursor, cell, selection)
        returns transcript + N-best + word confidences   parser → command + slots (+ confidences)
              ▲                                          validation (PDK, grid, selection)
              └── vocabulary hints (layers, cells, nets) preview card + ghost marker
                                                         confirm → transaction → journal
```

### 4.1 Speech to text: local and cloud, both supported

The helper uses an engine-neutral interface: `transcribe(audio, hints) → {text, alternatives[], word_confidences[]}`. Engines are configured in Setup; one is primary, the local one is the fallback.

| | Local | Cloud |
|---|---|---|
| Candidates | **whisper.cpp** or **faster-whisper** (Whisper `base.en`/`small.en`) | Providers with a speech-to-text API, e.g. OpenAI, Google Cloud, Azure, Deepgram. Choose in Step 0 by testing |
| Pros | free, offline, audio never leaves the machine | usually more accurate, especially on accents and noisy rooms; no CPU load |
| Cons | CPU load; ~0.5–1.5 s per utterance on CPU | audio leaves the machine; needs an API key; per-minute cost; network latency |
| Vocabulary hints | Whisper initial prompt with layer/cell names | provider phrase-hint/keyword features where offered |

- API keys live in a file outside the repo (e.g. `~/.config/klayout-voice/keys`, mode 600), never in `klayoutrc`.
- A per-engine on/off switch in Setup, so cloud use is an explicit choice.

### 4.2 Understanding: a grammar, not a guess

Turning the transcript into a command is done by a **deterministic grammar parser** (Python, in the KLayout macro), not a language model:
- It handles the commands in §2 with free word order for the slots ("W 2 L 0.15" = "L 0.15, W 2"), spoken numbers ("zero point one five", "one fifty nano"), units, and layer aliases.
- Its behaviour is predictable and fully testable with the regression corpus, which is the robustness requirement.
- The parser takes the N-best transcripts and picks the best one that parses completely; slot confidences come from the word confidences.

**Open decision (not required for Phase A):** an optional language-model parser as a fallback for phrasings the grammar rejects. It would output the same command structure and go through the same validation and preview card, so it can't bypass any safety. Decide after Phase A shows how often the grammar misses.

### 4.3 Layer and name aliases

A user-editable init file, like a Virtuoso bindkey file: `met1` = "metal one" / "M one" / "metal 1"; `li1` = "local interconnect" / "L I"; `poly`; `diff`; `nwell`… Device aliases: "nmos"/"n-fet" → `nfet`. These also feed the STT vocabulary hints.

### 4.4 Microphone consent

- First enable shows KLayout's own dialog: **"KLayout wants to access your microphone. Allow?"** The answer is saved (`voice-mic-consent`) and can be reset in Setup. Denied means the helper is never started.
- Linux has no OS-level microphone permission, so this dialog is the only prompt. On native Windows/macOS builds Phase B also calls Qt's `QMicrophonePermission` (C++ only; not in the Python Qt bindings).
- On WSL2 the mic comes through WSLg's PulseAudio bridge (`/mnt/wslg/PulseServer`, present on this machine). Windows must allow "Let desktop apps access your microphone".
- Push-to-talk: the helper opens the mic only while the key is held. Default key to be chosen so it doesn't clash with editing keys; configurable.

## 5. Plan

**Step 0: prove the pieces (half a day).**
- Audio: `sudo apt install pulseaudio-utils`; `pactl list short sources`; record 16 kHz mono and play it back.
- Local STT: install whisper.cpp or faster-whisper in a helper venv; transcribe 20 recorded commands; measure latency and errors.
- Cloud STT: same 20 recordings through two providers; compare accuracy, latency, and cost per hour of speech.
- Cursor position: confirm how the macro gets the cursor's layout coordinate. A `pya.Plugin` `mouse_moved_event` gives it in µm, but check it's delivered when the plugin isn't the active tool; otherwise map `QCursor.pos()` through the view's canvas and `view.box()`.
- Output: a short results table appended to this work order, and the engine choices.

**Phase A: working prototype (no KLayout source changes).**
- `voice_helper.py`: push-to-talk capture, engine interface with local + cloud + failover, JSON lines on stdout, hints on stdin.
- `voice.lym`: consent, helper supervision, context snapshot, parser, validation, preview card + ghost marker, transactions, journal lines.
- Command set: all of Group 1 and Group 2 in §2.
- Parser regression corpus: at least 300 utterances, including deliberately ambiguous and malformed ones.

**Phase B: native plugin.** Move the KLayout side to `src/plugins/tools/voice/`: Setup page (engines, keys file, push-to-talk key, thresholds, alias file), `QMicrophonePermission`, journal integration. The helper stays a separate process.

**Later (separate work orders):** Groups 3–10 from the brainstorm: find by name, select by property, queries, Xschem cross-probe, flows.

## 6. Acceptance (Phase A)

- [ ] Denying consent leaves the mic untouched; the choice persists and can be reset.
- [ ] "Place nfet W 2 L 0.15 4 fingers here" → card with the four values and the snapped position, ghost outline at the cursor; Enter places exactly that PCell; one Ctrl+Z removes it.
- [ ] Each command in §2 works end to end on a sky130 layout.
- [ ] "No, W 3" while the card is open changes W only.
- [ ] Below-minimum L, nonexistent layer, or "move up 2" with nothing selected → error on the card, nothing changes.
- [ ] "Two point eight" vs "twenty-eight" ambiguity is highlighted when the alternatives disagree.
- [ ] Cloud engine disabled or network off → local engine takes over within the timeout; the card says so.
- [ ] Killing the helper mid-utterance → no change to the layout; helper restarts.
- [ ] Parser corpus passes 100 %; end-to-end on 200 recorded commands: ≥ 95 % correct on first try, **0 wrong actions executed** (every error caught at the card).
- [ ] UI stays responsive while recognition runs.

## 7. Privacy

- Local engine: audio never leaves the machine.
- Cloud engine: only push-to-talk audio is sent, only when that engine is enabled. The Setup page says which provider receives it.
- The helper uses stdin/stdout to KLayout, no network sockets of its own besides the cloud API.
