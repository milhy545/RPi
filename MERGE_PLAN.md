# Slucovani vetvi do main – plan a stav

Pporadi mergu (od nejmene kontroverzniho):
1. runtime(+runtime-v2) -> main  ... zaklad, zadne konflikty
2. add_uda_mcp_server  -> main  ... cisty merge
3. feature/code-preview-> main  ... pred sloucenim synchronizovan s ancestorem add_uda_mcp_server
4. arena_harness       -> main  ... prvni cast cista
5. runtime(v2 changes) -> main  ... RESENO: Dockerfile v2, entrypoint unie, file_viewer runtime verze

Duplicitni vetev runtime-v2 smazana (obsah je soucasti runtime).
Vsechny source vetve smazany po overeni, ze jsou plne obsazeny v main.
