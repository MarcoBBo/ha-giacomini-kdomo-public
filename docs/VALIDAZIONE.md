# Validazione della release 0.1.0

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
