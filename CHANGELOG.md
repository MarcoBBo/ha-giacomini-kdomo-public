# Changelog

## 0.4.2 — 2026-10-31

La scheda compatta mostra umidità e icone colorate per le modalità spento, acceso e automatico.

## 0.4.1 — 2026-10-31

Aggiunge una scheda compatta dei termostati con un pannello dedicato: stato corrente, temperature predefinite e programmazione settimanale. Le temperature aprono i controlli nativi di Home Assistant; in questo pannello la programmazione è sempre in sola lettura. La scheda della 0.4.0 resta disponibile separatamente con le proprie opzioni.

## 0.4.0 — 2026-10-31

Lettura e modifica della settimana del programma corrente. Editor visuale incluso nel componente: sette giorni, confini trascinabili, orari numerici, livelli termici, divisione/unione, copia dei giorni, bozza e riepilogo prima/dopo. Registrazione della risorsa e aggiunta della scheda alla dashboard documentate.

Azioni HA get_schedule e set_schedule con permessi per entità; revisione obbligatoria, conservazione dei giorni invariati, un solo invio del gruppo 03 e verifica di tutti i giorni con timestamp freschi per quelli modificati. Nessun cambio di programma, accensione, replay o rollback. Nuova opzione schedule_write_enabled disabilitata per impostazione predefinita.

Test del codice Python, interfaccia DOM e percorso completo HA → HTTP cloud sintetico → conferma. Nessuna installazione domestica o prova di scrittura reale durante lo sviluppo. Il collaudo del gruppo 03 e la semantica del minuto finale restano da verificare sul dispositivo. Non è inclusa una piattaforma calendar.

## 0.3.0 — 2026-10-30

Aggiunge dieci entità number per tutte le temperature predefinite documentate: Comfort, Comfort+, Notte, Economy, Economy+ e Antigelo per riscaldamento; Comfort, Comfort+, Notte ed Economy per raffrescamento.

Scritture dei gruppi 10/11 con lettura preventiva, conservazione di tutti i campi, lock condiviso con il clima, conferma fresca e nessun replay o rollback. Blocco su gruppo incompleto, scala sconosciuta o cambiata. Traduzioni italiane/inglesi e conversione delle unità gestita da HA.

Nessuna modifica alla programmazione settimanale, alla selezione del programma o alla logica del comando climate. Non risolve il caso di conferma climate con dispositivo spento/automatico. Verifiche offline; nessun comando inviato all'impianto durante lo sviluppo di 0.3.0. Collaudo fisico dei gruppi 10/11 ancora da eseguire.

La numerazione passa da 0.1.0 a 0.3.0 su richiesta del proprietario; non è stata distribuita una 0.2.0.

## 0.1.0 — 2026-10-26

Prima alpha indipendente: configurazione UI con scelta impianto, entità clima, temperatura/umidità/connessione, polling condiviso, setpoint temporaneo, accensione/spegnimento e ritorno al programma corrente. Scritture inizialmente disabilitate, readback dopo i comandi, nessun replay POST o modifica della pianificazione.

Include documentazione del protocollo, specifica OpenAPI, istruzioni, diagnostica limitata, test offline su due versioni HA e workflow CI. Il componente non è ancora stato installato sull’istanza HA del proprietario. La distribuzione iniziale è prevista in repository privato, senza pubblicazione HACS.
