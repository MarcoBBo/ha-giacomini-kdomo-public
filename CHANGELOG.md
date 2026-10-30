# Changelog

## 0.3.0 — 2026-10-30

Aggiunge dieci entità number per tutte le temperature predefinite documentate: Comfort, Comfort+, Notte, Economy, Economy+ e Antigelo per riscaldamento; Comfort, Comfort+, Notte ed Economy per raffrescamento.

Scritture dei gruppi 10/11 con lettura preventiva, conservazione di tutti i campi, lock condiviso con il clima, conferma fresca e nessun replay o rollback. Blocco su gruppo incompleto, scala sconosciuta o cambiata. Traduzioni italiane/inglesi e conversione delle unità gestita da HA.

Nessuna modifica alla programmazione settimanale, alla selezione del programma o alla logica del comando climate. Non risolve il caso di conferma climate con dispositivo spento/automatico. Verifiche offline; nessun comando inviato all'impianto durante lo sviluppo di 0.3.0. Collaudo fisico dei gruppi 10/11 ancora da eseguire.

La numerazione passa da 0.1.0 a 0.3.0 su richiesta del proprietario; non è stata distribuita una 0.2.0.

## 0.1.0 — 2026-10-26

Prima alpha indipendente: configurazione UI con scelta impianto, entità clima, temperatura/umidità/connessione, polling condiviso, setpoint temporaneo, accensione/spegnimento e ritorno al programma corrente. Scritture inizialmente disabilitate, readback dopo i comandi, nessun replay POST o modifica della pianificazione.

Include documentazione del protocollo, specifica OpenAPI, istruzioni, diagnostica limitata, test offline su due versioni HA e workflow CI. Il componente non è ancora stato installato sull’istanza HA del proprietario. La distribuzione iniziale è prevista in repository privato, senza pubblicazione HACS.
