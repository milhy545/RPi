# Specifikace tracku: Synchronizace produkčního repozitáře RPi

## Cíl

Sjednotit produkční checkout na Raspberry Pi s aktuální větví GitHub `main`, aniž by se ztratila současná práce uživatele nebo změnilo místní nastavení přehrávání.

## Požadavky

- Ověřit SSH cíl a zapsat jeho živou adresu do `~/.gemini/GEMINI.md`.
- Před změnou produkčního checkoutu zachovat historii commitů, necommitnuté soubory a místní konfiguraci RPi.
- Za zdroj pravdy pro aplikaci a CI považovat aktuální GitHub `main`. Neimportovat celý zastaralý snapshot zavřeného PR #85, který by odstranil současné testy a ochrany CI.
- Zachovat `.dlnain-mode.json` jako místní stav zařízení; výběr ručního audio sinku na RPi nepublikovat do sdíleného repozitáře.
- Zachovat dvě aktuálně necommitnutá hlášení, protože uživatel výslovně požádal o synchronizaci současné práce na RPi.
- Pushovat a slučovat pouze z Milhy-PC po úspěšných povinných kontrolách a Kilo review. RPi nikdy nepushuje.
- Aktualizovat checkout RPi až poté, co přesný commit bude na GitHub `main`; nerestartovat služby ani nepřerušit přehrávání.
- Upozornit uživatele, aby aplikaci ručně ověřil. Větve nemazat, dokud uživatel nepotvrdí výsledek testu.

## Kritéria přijetí

- Záznam adresy odpovídá hostu ověřenému přes SSH alias `RPi`.
- Existuje ověřená záloha původního commitu a necommitnutých souborů na RPi.
- Požadovaná hlášení jsou na GitHub `main`, aniž by se vrátily změny aplikace, testy nebo CI z aktuální větve main.
- Checkout RPi ukazuje na přesné SHA GitHub `main` a místní audio režim je zachovaný.
- Z RPi nebyl proveden push a nebyla restartována žádná služba.
- Uživatel ví, že ruční ověření čeká; úklid větví zůstává odložený.
