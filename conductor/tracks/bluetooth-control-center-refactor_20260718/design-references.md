# Design References: Bluetooth Control Center

## Source location

The original visual concepts are attached to the ChatGPT project/conversation **RPi-TV**. They are not public web assets and this track deliberately does not invent a fake public URL.

When running `conductor implement` from Codex with the user's connected ChatGPT/project/file context, search the project attachments by the exact names and file IDs below. If a connector exposes a project-files browser, use it. If the attachments are unavailable in that execution context, continue from the binding design brief in this document rather than blocking implementation.

## Original concept attachments

1. **Futuristic Bluetooth adapter management dashboard.png**
   - ChatGPT file ID: `file_00000000780071f495b87c608a2cbb2d`
   - Original project runtime path observed during track authoring: `/mnt/data/Futuristic Bluetooth adapter management dashboard.png`

2. **Koncepty rozhraní pro správu Bluetooth.png**
   - ChatGPT file ID: `file_00000000770871f49afb270ca3c6689c`
   - Original project runtime path observed during track authoring: `/mnt/data/Koncepty rozhraní pro správu Bluetooth.png`

3. **Bluetooth control center dashboard UI.png**
   - ChatGPT file ID: `file_00000000ffb871f48d50cb389d66e306`
   - Original project runtime path observed during track authoring: `/mnt/data/Bluetooth control center dashboard UI.png`

4. **Futuristický ovládací panel Bluetooth.png**
   - ChatGPT file ID: `file_000000000ff071f48afdea0c5f7dfd0c`
   - Original project runtime path observed during track authoring: `/mnt/data/Futuristický ovládací panel Bluetooth.png`

5. **Bluetooth management dashboard interface.png**
   - ChatGPT file ID: `file_00000000d59871f4ba3e3c05e28c4db1`
   - Original project runtime path observed during track authoring: `/mnt/data/Bluetooth management dashboard interface.png`

## Contact sheets created in the ChatGPT project

These combine the concepts for easier visual comparison. They are optional convenience references, not additional requirements.

- **bluetooth_concepts_contact_sheet.jpg**
  - ChatGPT file ID: `file_00000000dd948243b8b023b539f37e40`
  - Observed path: `/mnt/data/user-ySg5BdyNQQwUUVfLrsRR0qp5/6787761d5aa840918890d368f266da06/mnt/data/bluetooth_concepts_contact_sheet.jpg`

- **bluetooth_design_contact_sheet.jpg**
  - ChatGPT file ID: `file_0000000008d882439b9678ca3a85bf8f`
  - Observed path: `/mnt/data/bluetooth_design_contact_sheet.jpg`

Runtime `/mnt/data` paths are contextual and may not exist in a later Codex session. The file IDs and exact filenames are the durable project-context lookup keys available from this track.

## Binding visual interpretation

The images are concept explorations. They do not override repository behaviour, accessibility, responsive constraints, or backend truth. Implement the shared concepts below.

### 1. A control centre, not another settings list

The Bluetooth tab should feel like an operational overview:

- immediate backend/BlueZ health;
- visible physical adapters;
- visible devices associated with each adapter;
- direct but safe operations;
- diagnostics and readiness in the same surface;
- recent operation/event feedback.

The user should be able to answer these questions without opening logs:

- Are both adapters present and powered?
- Which current `hciN` corresponds to which stable adapter?
- Which adapter owns or sees each device?
- Is discovery running, and on which adapter?
- Is a device merely known, paired, trusted, connected, or actually profile-ready?
- Why is the soundbar or Xbox/Steam Link workflow not ready?

### 2. Two explicit adapter zones

Wide WebUI layouts should show two adapter zones/cards side by side. Each must include:

- stable user label/role;
- adapter address;
- current BlueZ path/index (`hciN`) as secondary diagnostic text;
- presence and backend health;
- power and discovery status;
- device count and active operations;
- controls whose enabled/disabled state comes from the backend.

On narrow screens, stack the same zones vertically. The meaning must not depend on a decorative line stretching between columns.

The TUI should express the same separation through two panels, an adapter selector, or clearly grouped rows. It does not need to imitate glowing graphical cards.

### 3. Device-to-adapter relationship

Every device card/row must visibly identify its adapter. Grouping by adapter is preferred. A selected-device panel may show a compact relationship path such as:

```text
[USB BT Adapter / controllers] -> [Xbox Wireless Controller]
```

or

```text
[Onboard BT / audio] -> [[Samsung] Soundbar J-Series]
```

Never draw a connection merely because two objects exist. Relationship lines/grouping must reflect the backend's `adapter_id`.

### 4. State is textual and evidence-based

Use badges/labels for distinct states:

- present / absent
- powered / powered off
- discovering / idle
- known / newly discovered
- paired / unpaired
- trusted / untrusted
- connected / disconnected
- services resolved / unresolved / unknown
- audio sink present / missing / unknown
- input device present / missing / unknown
- operation pending / succeeded / failed / cancelled

Colour can reinforce state but cannot be the only indicator. Do not compress all success into a single green dot.

### 5. Signal and battery

Show RSSI and battery only when the backend provides real values.

- RSSI should use dBm or a clearly documented derived quality range.
- Do not show invented percentages from concept art.
- Unknown values should display `Unknown` / `Neznámé`, not `0%`.
- Battery belongs to devices exposing BlueZ battery information.

### 6. Operations and safety

Place context-appropriate actions near the selected adapter/device. Avoid showing every destructive action at equal visual weight.

Recommended hierarchy:

- primary: connect or disconnect, pair when needed;
- secondary: trust/untrust, discovery controls, refresh;
- destructive: remove/forget with confirmation;
- diagnostic: copy identity, inspect blockers, view recent event/error.

Every operation must visibly show pending state and final backend result. Disable or reject conflicting actions rather than letting the user trigger races.

### 7. Soundbar readiness

The known Samsung soundbar should have a dedicated readiness card or details block. Show the ladder defined in `spec.md`, separating BlueZ transport from PipeWire/audio routing.

The visual design may use a vertical checklist or compact pipeline:

```text
Adapter -> Known -> Paired -> Trusted -> Connected -> A2DP/Profile -> PipeWire sink -> Route/Loopback
```

Each failed or unknown step should expose a reason. Bluetooth must not pretend to own Audio controls.

### 8. Controller and Steam Link readiness

Use a compact preflight block:

- selected/connected controller;
- adapter;
- BlueZ/HID/profile evidence;
- Linux input device evidence;
- driver/module hints;
- ERTM diagnostic;
- Steam Link executable;
- final blocker list.

Avoid a single unexplained `READY` badge. The user needs to know what remains missing.

### 9. Recent events and diagnostics

Include a bounded, lightweight event/operation list such as:

- adapter appeared/disappeared;
- discovery started/stopped;
- device found;
- pairing requested/rejected/completed;
- connection changed;
- services resolved;
- backend permission or timeout error.

Do not create an unbounded in-memory log. Use a small ring buffer or existing logging infrastructure.

### 10. Existing product language

Blend the useful hierarchy of the concepts with the current RPi-TV dashboard:

- dark background and existing card vocabulary;
- cyan/blue accents are acceptable but not mandatory;
- readable on TV, desktop, and phone;
- no expensive or mandatory animations;
- no excessive glow reducing text contrast;
- no new navigation sidebar;
- preserve Czech/English support;
- TUI remains ASCII-safe and low-resource.

## Non-binding concept elements

Do not implement these unless they serve real state and remain cheap/accessibile:

- animated radio waves;
- rotating radar effects;
- moving neon connection paths;
- arbitrary throughput graphs;
- fictional security scores;
- decorative adapter toggles not wired to BlueZ;
- fabricated signal or battery percentages;
- exact pixel placement from any single image.

## Design acceptance checklist

- [ ] Two adapters remain distinguishable even if their `hciN` indexes swap.
- [ ] Every device visibly belongs to an adapter.
- [ ] Zero, one, and two-adapter states all have useful layouts.
- [ ] Missing/unknown information is honest and readable.
- [ ] Backend errors and pending operations are visible.
- [ ] Soundbar transport and Audio readiness are separate.
- [ ] Xbox/Steam Link readiness lists concrete blockers.
- [ ] Mobile WebUI stacks cleanly without relying on drawn topology.
- [ ] TUI offers equivalent core information/actions without graphical imitation.
- [ ] No action or toggle exists only because it looked attractive in a concept image.