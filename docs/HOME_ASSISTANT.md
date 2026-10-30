# Architettura Home Assistant

Architettura della release 0.3.0 alpha, aggiornata il 30 ottobre 2026.

## Perché una integrazione

Una integrazione connette HA a un dispositivo o servizio ed espone entità. Un add-on, ora denominato anche app nella documentazione HA, esegue invece un programma separato gestito dal Supervisor. Per questa API HTTP è sufficiente un client asincrono nel processo Core: nessun demone, porta locale, broker o bridge necessario.

La custom integration funziona senza Supervisor. Una eventuale futura web app potrà riusare la semantica del protocollo, ma richiederà un backend che custodisca le credenziali; non è corretto incorporare password/token in un frontend pubblico.

## Struttura

| Modulo | Responsabilità |
| --- | --- |
| `api.py` | HTTP asincrono aiohttp, autenticazione, discovery, letture, POST topic 02, 10 e 11 |
| `models.py` | Decodifica tipizzata, enum validi, limiti, costruzione del gruppo e conferma fresca |
| `config_flow.py` | Login, scelta impianto, blocco duplicati, riautenticazione e opzioni |
| `coordinator.py` | Polling condiviso, errori, backoff, serializzazione delle transazioni |
| `entity.py` | Identità stabile, registro dispositivi e disponibilità |
| `climate.py` | Mapping HVAC e servizi clima standard |
| `number.py` | Dieci temperature predefinite, servizi number standard e conversione unità |
| `sensor.py` | Temperatura e umidità |
| `binary_sensor.py` | Online riportato dal cloud |
| `diagnostics.py` | Diagnostica con whitelist di campi non identificativi |
| `__init__.py` | Setup, primo refresh, inoltro piattaforme e unload |

La sessione HTTP è fornita da HA; l’integrazione non blocca l’event loop con chiamate sincrone. Non aggiunge dipendenze PyPI a runtime: aiohttp è già parte di HA. `manifest.json` dichiara `cloud_polling`, `integration_type=hub` e `config_flow=true`.

## ConfigEntry e identità

Una ConfigEntry rappresenta un account più un impianto scelto. `data` conserva username/password, plant_id e titolo. `options` contiene solo abilitazione scritture e intervallo di polling.

La unique_id della ConfigEntry combina SHA-256 dello username esatto con plant_id. Non è una cifratura e non sostituisce la protezione della configurazione. Serve a evitare l’email in questo identificativo e impedire aggiunte duplicate dello stesso account/impianto. Non si normalizza la maiuscola dello username senza sapere se il servizio lo consenta. Alias diversi dello stesso account possono quindi eludere il blocco duplicati: un limite noto in assenza di account_id stabile verificato.

Ogni dispositivo usa `(plant_id, serial)` e ogni entità aggiunge un suffisso stabile. Gli identificativi non dipendono dal nome della stanza, che può cambiare. L’integrazione non conosce un modello hardware affidabile per tutti i dispositivi: il registro dichiara genericamente “K-Domo cloud thermostat”.

All’avvio si scoprono i dispositivi dell’impianto scelto e si esegue il primo refresh prima di creare entità. La discovery non viene ripetuta a ogni ciclo; ricaricare per cambi dell’inventario. Il coordinatore viene conservato in `entry.runtime_data` e scarica le piattaforme alla rimozione.

## Comandi e concorrenza

Un lock per ConfigEntry serializza sia l’intero polling sia una transazione di comando con verifica. Questo evita che un refresh concorrente reintroduca un vecchio snapshot dopo la conferma. Le piattaforme di lettura non avviano polling autonomi. La piattaforma clima limita inoltre la concorrenza dei servizi a una operazione.

La serializzazione non impedisce a un’altra app o al termostato di cambiare impostazioni fra GET e POST. Il backend non ha esposto un controllo di versione verificato. Non esiste quindi una garanzia di atomicità fra client diversi.

Non viene effettuata una scrittura di ripristino in caso di errore: una richiesta con timeout può essere già stata applicata. L’utente vede l’errore, il polling successivo mostra il valore riportato dal cloud e la decisione di ripetere resta esplicita.

## Disponibilità ed errori

- Errore totale di polling → `UpdateFailed`, entità indisponibili e retry del coordinatore.
- Credenziali rifiutate dopo nuovo login → `ConfigEntryAuthFailed` durante aggiornamento/setup; HA propone reauth.
- Errore di autenticazione durante servizio → avvio del flusso reauth e azione fallita, senza ripetere il POST.
- Offline esplicito → sensore connessione spento; clima e ambiente indisponibili.
- Errore su un singolo termostato → solo quello marcato in errore, mentre le altre letture proseguono.
- HTTP 429 → backoff per l’impianto; non si forza una nuova richiesta tramite i servizi.

La diagnostica non serializza l’intera ConfigEntry o oggetti aiohttp: restituisce solo versione, opzioni, esito dell’ultimo aggiornamento e indicatori numerici di stato, senza identità dei dispositivi.

## Mapping clima

`OFF` corrisponde a status 0. `AUTO` corrisponde a status 1 e mode 1. `HEAT`/`COOL` rappresentano manuale attivo e sono scelti usando il tipo del programma corrente, non una ipotesi sulla stagione dell’anno. Un mode 0 già presente può essere letto e mostrato, ma non viene offerto un comando per selezionarlo.

I livelli termici sono esposti come entità number di configurazione, non come selezione del preset climate. I gruppi 10/11 preservano tutte le temperature e i selettori interi; un gruppo incompleto blocca la scrittura. Sono disponibili anche i livelli della stagione non attiva. Non si cambia il programma per modificarli. La conferma richiede che tutti i campi inviati coincidano e che i campi modificati abbiano timestamp successivi al comando; la scala deve restare invariata. Le nuove scritture non sono ancora collaudate sul dispositivo reale. `hvac_action` resta sconosciuto perché non è stata verificata la telemetria del relè.

## Compatibilità realmente verificata

La matrice di test usa Home Assistant 2026.2.3 con Python 3.13 e 2026.10.4 con Python 3.14. Il secondo è stato risolto dalla release PyPI disponibile il giorno delle prove. Le fixture eseguono veri setup, config flow, piattaforme, registro entità e chiamate dei servizi; non sono semplici stub di Home Assistant.

Le pagine di documentazione online sono aggiornabili e, alla consultazione, includevano anche API clima `native_*` non presenti nel pacchetto 2026.10.4 installato. Il codice si basa quindi sulle API effettivamente disponibili e testate: `temperature_unit`, `current_temperature`, `target_temperature`. Non dichiara compatibilità con future rimozioni. La configurazione usa `probatio` dove disponibile e `voluptuous` per il minimo supportato.

I test HTTP usano un server aiohttp locale; il test completo attraversa configurazione HA, client HTTP, cloud simulato e servizio clima. Nessuna credenziale reale viene caricata nei test. Resta distinta la prova cloud reale precedente, effettuata con il client indipendente: questa release non è ancora stata installata nell’istanza domestica del proprietario.

## Riferimenti ufficiali consultati

- [Building integrations](https://contributors.home-assistant.io/core/integrations/).
- [Manifest](https://contributors.home-assistant.io/core/integrations/manifest/).
- [Config flow](https://contributors.home-assistant.io/core/integrations/config-flow/).
- [Fetching data / DataUpdateCoordinator](https://contributors.home-assistant.io/core/integrations/fetching-data/).
- [Climate entity](https://contributors.home-assistant.io/core/entities/climate/).
- [Apps / add-ons](https://contributors.home-assistant.io/apps/).
- [HACS integration repository requirements](https://www.hacs.dev/docs/publish/integration/).
- [HACS validation action](https://github.com/hacs/action).
- [Home Assistant Core, tag 2026.10.4](https://github.com/home-assistant/core/tree/2026.10.4), commit `357cae5c598dfcd7a0ea7dc5b1facccd4ec6037b`.

Le scelte del protocollo derivano dalle nostre prove e dall’APK; i riferimenti HA spiegano i meccanismi dell’integrazione, non convalidano il protocollo privato K-Domo.
