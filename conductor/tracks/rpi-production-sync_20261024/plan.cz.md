# Implementační plán: Synchronizace produkčního repozitáře RPi

## Fáze 1 — Ověřit a zachovat

- [x] Ověřit, že SSH alias míří na `rpi-tv` s adresou `192.168.0.205`.
- [x] Opravit adresu RPi v `~/.gemini/GEMINI.md` a ponechat časovanou zálohu.
- [x] Uložit ověřený Git bundle, necommitnutý diff, reporty a místní DLNA režim.
- [x] Porovnat větev RPi s aktuálním GitHub main. Opravy zdrojového kódu už jsou v aktuálním main; zastaralý strom zavřeného PR #85 se nemá slučovat celý.

## Fáze 2 — Sjednotit na GitHubu

- [x] Ponechat ruční výběr sinku na RPi jako místní konfiguraci.
- [x] Přenést dvě aktuální necommitnutá hlášení na výslovnou žádost uživatele.
- [ ] Spustit povinné kontroly gateway, otevřít zaměřený PR a počkat na povinné kontroly i Kilo review.
- [ ] Sloučit ověřený PR a ověřit přesné SHA main a receipt.

## Fáze 3 — Synchronizovat RPi

- [ ] Zálohovat zbývající místní stav a nastavit produkční checkout na přesné SHA GitHub main bez pushování z RPi.
- [ ] Zachovat místní DLNA režim a nerestartovat služby ani nepřerušit přehrávání.
- [ ] Ověřit výsledné SHA a zaznamenat přesný stav checkoutu.

## Fáze 4 — Uživatelské ověření a úklid větví

- [ ] Oznámit uživateli, že může začít ruční test aplikace.
- [ ] Počkat na výsledek uživatelského testu.
- [ ] Teprve po potvrzení zvlášť inventarizovat a odstranit větve mimo main.

## Záznam postupu

- 2026-10-24: Ověřili jsme identitu hostu i mapování adresy. Produkční checkout má pět commitů navíc oproti zastaralému místnímu `origin/main`, zatímco GitHub main se mezitím posunul samostatně. Aktuální pracovní strom obsahuje dvě zástupná hlášení a sledovaný místní DLNA režim. Celý historický snapshot PR #85 vynecháváme, protože by vrátil novější stav projektu; jeho objekty a necommitnutý pracovní strom jsou zazálohované.
