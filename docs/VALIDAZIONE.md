# Validazione

## Release 0.4.0 — 31 ottobre 2026

158 test Python passati su HA 2026.10.4 / Python 3.14.8 (copertura 93,94%) e HA 2026.2.3 / Python 3.13.16 (94,40%). Quattordici test frontend DOM passati con Node.js e jsdom 26.1.0. Ruff lint/formato, Prettier e Hassfest locale superati: 1 integrazione, 0 non valide, nessun warning finale. Hassfest usa lo stesso adattamento del pool a due thread già descritto sotto.

La suite Python verifica codec riscaldamento/raffrescamento, sette giorni completi, otto fasce massime, ordine domenica–sabato, padding conservato sui giorni invariati, rifiuto di programmi misti o dati incompleti, revisione obsoleta, conferma logica e timestamp dei giorni modificati. Verifica permessi HA per lettura e scrittura, ConfigEntry scaricata, abilitazione separata e revoca dei controlli durante la lettura, backoff, reauth e assenza di replay/rollback.

Il percorso completo usa vere azioni HA, client aiohttp e cloud sintetico per inviare il gruppo 03 e verificarne la rilettura, conservando gli altri giorni, modalità, programma, setpoint e stato acceso/spento. Un test HTTP HA verifica che il modulo JavaScript incluso sia effettivamente servito al percorso documentato.

I test frontend montano il vero custom element in jsdom e verificano modifica delle bozze senza invio, split/merge, copia dei giorni, riepilogo, salvataggio confermato, conflitti esterni, errore incerto senza reinvio, controllo tramite range senza ricreare il campo durante il movimento, trascinamento pointer, selettore accessibile, cambio delle opzioni, offline, conversione Fahrenheit e inserimento sicuro dei testi. jsdom non misura il layout reale: la resa responsiva, il tema e il tocco sui dispositivi reali restano da controllare in HA.

Nessuna installazione domestica, richiesta all’account reale o scrittura di pianificazioni durante lo sviluppo. Il gruppo 03, il minuto finale 23:59 e i comportamenti firmware restano da collaudare fisicamente con istruzione esplicita. Non vengono creati calendari nativi né lette settimane di programmi inattivi. Il precedente problema climate spento/automatico resta fuori da questa modifica.

La CI della 0.4.0 include i due ambienti Python e un job Node 22 per test frontend e formato. Il suo esito remoto va verificato separatamente sul commit pubblicato; questi risultati documentano l’esecuzione locale.

## Release 0.3.0 — 30 ottobre 2026

124 test passati su HA 2026.10.4 / Python 3.14.8, copertura 92,84%. Gli stessi 124 test passano su HA 2026.2.3 / Python 3.13.16, copertura 93,13%. Ruff lint e formato superati. Hassfest locale sul sorgente ufficiale HA 2026.10.4: 1 integrazione, 0 non valide, con la stessa sostituzione del pool processi descritta nel resoconto storico.

Le nuove verifiche coprono tutte e dieci le temperature, payload completi dei gruppi 10/11 e conservazione dei campi non modificati; campi mancanti o invalidi, precisione non preservabile, valori fuori intervallo, scala sconosciuta o cambiata; no-op, scritture disabilitate, conferme incomplete o con timestamp precedenti e nessun rollback/replay.

Il test completo attraversa HA, servizi number, client aiohttp e cloud sintetico su loopback. Verifica anche due richieste contemporanee per temperature diverse dello stesso gruppo, senza perdita di aggiornamenti, una modifica del gruppo raffrescamento e conservazione di modalità, stato, programma e setpoint climate. La conversione Celsius/Fahrenheit passa attraverso il servizio number reale di HA.

Nessuna lettura o scrittura dell’account reale è stata eseguita durante lo sviluppo di 0.3.0. Le nuove scritture richiedono ancora un collaudo fisico autorizzato. Il problema già osservato della conferma del setpoint climate con termostato spento/automatico resta aperto.

## Release 0.1.0 — resoconto storico

Eseguita il 26 ottobre 2026. Nessun nuovo comando è stato inviato all’impianto reale durante lo sviluppo del componente Home Assistant.

## Risultati

| Controllo | Esito |
| --- | --- |
| Suite su Home Assistant 2026.10.4 / Python 3.14.8 | 68 test passati |
| Suite su Home Assistant 2026.2.3 / Python 3.13.16 | 68 test passati |
| Copertura delle istruzioni del componente, versione attuale | 91,40% |
| Soglia CI | 90%, raggiunta |
| Ruff lint e formato | Passati |
| OpenAPI 3.1, `openapi-spec-validator` | Valida |
| Hassfest locale, sorgenti Core tag 2026.10.4 | 1 integrazione, 0 non valide |
| Workflow GitHub Actions remoto | Preparato, non eseguito su repository pubblico |
| Validatore HACS sul repository remoto | Non eseguito; URL/maintainer da assegnare |
| Installazione nella specifica istanza HA del proprietario | Non eseguita |

Hassfest è stato eseguito dal codice ufficiale al commit `357cae5c598dfcd7a0ea7dc5b1facccd4ec6037b`, usando HA 2026.10.4 installato. L’ambiente virtuale non consentiva il socket del forkserver usato per il pool dei processi: la sola esecuzione parallela dell’analisi delle dipendenze è stata sostituita con un pool di due thread, mantenendo tutti i controlli. Nessun plugin di validazione è stato saltato. Questa prova locale non sostituisce il futuro workflow ufficiale su GitHub.

I metadati sono configurati per MarcoBBo/ha-giacomini-kdomo e maintainer MarcoBBo. La verifica locale non prova l’esistenza del repository remoto. La prima pubblicazione autorizzata è privata; non eseguire una distribuzione pubblica o HACS senza nuova autorizzazione.

## Cosa verificano i test

- Login e uso letterale di `X-Auth-Token`, senza Bearer.
- Redirect bloccati, anche per richieste autenticate.
- Nuovo login e un solo replay delle letture; nessun replay dei comandi.
- Privacy non accettata automaticamente.
- Limite di dimensione delle risposte, JSON non valido, 401/403/429/500 e timeout.
- Selezione dell’impianto e uso del seriale anziché dell’id interno.
- Precedenza dei valori tipizzati e timestamp dei doppioni.
- Conservazione di programma, fan-coil e stato acceso/spento quando appropriato.
- Rifiuto di target fuori intervallo, scale sconosciute, stato incompleto e dispositivi offline.
- Differenza fra accettazione HTTP e conferma di stato; nessun rollback su mancata conferma.
- Configurazione UI, duplicati, opzioni e riautenticazione sulla stessa ConfigEntry.
- Creazione di tutte le piattaforme, disponibilità, unload e diagnostica priva di identificativi.
- Errore isolato di un termostato e backoff del cloud.
- Mapping della modalità e conversione HA Celsius → dispositivo Fahrenheit.
- Percorso completo config flow → setup → client aiohttp → cloud locale → servizio clima → conferma → unload.

I test HTTP effettuano richieste reali solo a un server sintetico su loopback. I test di coordinatore sostituiscono il client cloud. Non vengono caricati account o chiavi reali. I risultati non equivalgono a una prova su tutti i modelli o firmware.

## Evidenza reale precedente

Il client indipendente della sessione di ricerca ha già eseguito login, elenco dispositivi, letture e topic 02 sul cloud reale con account autorizzato. Il proprietario ha confermato fisicamente il passaggio del setpoint da 21 a 22 °C. Il manuale temporaneo mode=2 è stato osservato nel cloud; il manuale permanente mode=0 non è stato convalidato.

Successivamente il proprietario ha spento il termostato a mano. La nuova integrazione non è stata utilizzata per una ulteriore scrittura reale. Questa separazione evita di presentare un test simulato come una installazione già riuscita in casa.

## Procedura del prossimo collaudo reale

Installare inizialmente in sola lettura, confrontare nome dell’impianto, dispositivi e misure con l’app, poi scegliere un solo termostato osservabile. Il proprietario abilita i controlli e richiede un comando preciso. Verificare insieme UI HA, stato cloud e display fisico. Un eventuale ripristino deve essere esplicito; non modificare la pianificazione per questa prova.
