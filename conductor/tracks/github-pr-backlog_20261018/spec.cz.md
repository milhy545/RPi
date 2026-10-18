# Specifikace tracku: Vyřešení fronty GitHub PR

## Kontext a cíl

Repozitář má velkou skupinu otevřených a překrývajících se pull requestů. Některé jsou zařazené k automatickému sloučení bez výslovného rozhodnutí maintaineru a několik PR obsahuje zastaralé generované reporty nebo změny pro nesouvisející repozitáře. Frontu vyřešíme z Milhy-PC, jediné brány pro GitHub push a merge, při zachování uživatelských dat a lokálních commitů ve vývojovém checkoutu.

## Závazná rozhodnutí

1. Během kontroly fronty vypneme existující požadavky na auto-merge.
2. Auto-merge bude povolen pouze po přidání štítku `merge-approved`. Odebrání štítku zruší případné čekající automatické sloučení.
3. PR #85 rozdělíme a ověříme; nesloučíme ho v současném stavu. Platné Conductor reporty zachováme a prověříme duplicity. Runtime reporty vynecháme.
4. PR pro nesouvisející projekty uzavřeme s vysvětlením. Duplicitní PR uzavřeme až po začlenění jejich unikátních změn do ověřeného nástupce.
5. Každý slučovaný kandidát musí vycházet z aktuální větve `main`, projít povinnými kontrolami a review a být sloučen samostatně v souladu s pravidlem lineární historie.
6. Lokální commity ve vývojovém checkoutu zachováme a v rámci této práce je nepushneme.
7. Kontroly kandidáta na RPi provedeme v izolovaném worktree s neinvazivním hardwarovým guardem. Z RPi se nepushuje a nesmí se narušit přehrávání, hraní, TUI, audio, Bluetooth, CEC ani systémové služby.

## Kritéria přijetí

- Auto-merge workflow vyžaduje výslovný štítek, má pouze nutná oprávnění a testovanou cestu pro jeho odebrání.
- Každé PR z počátečního seznamu má zaznamenaný konečný stav: sloučeno, uzavřeno jako neplatné, uzavřeno jako nahrazené konkrétním nástupcem, nebo ponecháno otevřené s přesnou překážkou.
- Unikátní a platné změny z duplicitních PR zůstanou v otestovaném nástupci. Přidání ani mazání generovaných `reports/*.json` se nesloučí.
- PR #85 bude rozdělené do konkrétních nástupců; nesloučí se neprověřený balík nesouvisejícího kódu a uživatelských reportů.
- Sloučení proběhnou postupně. Před každým ověříme základní větev a úspěšné povinné kontroly GitHubu.
- Závěrečný report uvede všechny překážky, přesná čísla PR, SHA commitů, důkazy kontrol a případný CI receipt pro výsledný `main`.
