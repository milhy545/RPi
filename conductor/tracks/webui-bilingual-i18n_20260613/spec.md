# Spec: WebUI Bilingual Czech/English Switch

## Goal
Add a lightweight bilingual switch to the WebUI so the main dashboard can be displayed in Czech or English, with small flag buttons placed to the right of the `RPi-TV` heading.

## Requirements
- Keep the current layout intact.
- Place the language switch on the far right side of the main header.
- Use small, visually pleasant flag buttons for GB and CZ.
- Support the existing dashboard tabs and key controls in both languages.
- Persist the chosen language in the browser.
- Do not alter runtime behavior; this is a UI language layer only.

## Acceptance Criteria
- English/Czech toggle changes the visible UI labels.
- Flag buttons appear to the right of the main title.
- The selected language survives a browser refresh.
- Existing functionality and tests still pass.
