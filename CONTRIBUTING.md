# Contribuire

Usare esclusivamente account propri o esplicitamente autorizzati per eventuali prove reali. La suite del repository non richiede un account e non deve inviare comandi a un impianto.

## Test riproducibili

Per la release attuale:

```sh
python3.14 -m venv .venv
.venv/bin/python -m pip install -r requirements-test.txt
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/pytest --cov=custom_components.kdomo --cov-report=term-missing --cov-fail-under=90
```

Per la versione minima usare Python 3.13 e `requirements-test-min.txt`. Il pacchetto di fixture porta con sé la versione HA corrispondente. I due set devono essere installati in ambienti separati.

I test HTTP puntano a un server aiohttp su loopback. Gli altri test sostituiscono il client con risposte sintetiche. `pytest-socket` blocca le connessioni non consentite; le fixture dei server abilitano i socket necessari ai test locali. Non aggiungere test che carichino variabili d’ambiente con credenziali reali o snapshot del proprietario.

`test_end_to_end.py` attraversa config flow, setup, opzioni, client HTTP, comando e conferma, poi verifica l’unload. Non simula Home Assistant con classi locali inventate.

## Test dell’interfaccia

Il frontend non richiede librerie esterne a runtime. Per i test usare Node.js 20 o successivo:

```sh
npm ci
npm test
npm run format:check
```

jsdom e Prettier sono sole dipendenze di sviluppo, fissate in package-lock.json. I test montano il vero custom element, simulano solo l’API HA e verificano bozze, selezione, split/merge, copia, salvataggio, conflitti, errori, permessi UI, conversione e trattamento sicuro del testo ricevuto. Nessuna richiesta a un account reale. Il trascinamento e la resa su dispositivi reali richiedono anche verifica visuale nel frontend HA.

## Modifiche al protocollo

Separare sempre evidenza statica, risposta cloud, conferma fisica e test sintetici. Non descrivere un comando come supportato solo perché ritorna HTTP 200. Aggiungere un caso di errore e un criterio di verifica per ogni nuova scrittura.

Il client non deve diventare un servizio per inviare topic arbitrari. Le scritture di programmi, preset o configurazione richiedono una implementazione separata, conservazione dei dati esistenti e prove specifiche. Evitare retry di comandi con esito incerto.

## Build

```sh
python scripts/build_release.py
```

Lo script genera un archivio del repository, un archivio installabile con `custom_components/kdomo` e `dist/SHA256SUMS.txt`. Include solo file pubblici previsti e usa timestamp ZIP fissi. Nessuna credenziale è necessaria.

Prima di una release eseguire i workflow di validazione descritti in [PUBBLICAZIONE.md](docs/PUBBLICAZIONE.md). Le Actions incluse sono configurate, ma non sono state eseguite su un repository GitHub pubblico in questa preparazione.

## Riferimenti di formato

La struttura editoriale adotta le convenzioni comuni delle custom integration: funzioni, compatibilità, installazione, configurazione, esempi, limiti e supporto. Riferimenti consultati: [Integration Blueprint](https://github.com/ludeeus/integration_blueprint), [SmartThinQ Sensors](https://github.com/ollo69/ha-smartthinq-sensors) e [Template Climate](https://github.com/jcwillox/hass-template-climate). Sono riferimenti per organizzazione e leggibilità; il codice di questa integrazione è indipendente.
