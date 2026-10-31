# Giacomini K-Domo per Home Assistant

Integrazione indipendente per controllare i termostati Giacomini K-Domo attraverso il cloud. Espone dispositivi, entità clima, temperatura, umidità e stato della connessione in Home Assistant.

Versione 0.4.0 alpha. I controlli partono disabilitati e si attivano dalle opzioni. Le pianificazioni vengono modificate soltanto tramite le nuove azioni dedicate e con l’opzione specifica abilitata.

Il progetto usa un’interfaccia cloud non ufficiale. Non è affiliato o approvato da Giacomini.

## Funzioni

- Configurazione dalla UI con account K-Domo e scelta dell’impianto.
- Una entità clima per termostato.
- Sensori di temperatura, umidità e connessione cloud.
- Setpoint in manuale temporaneo, accensione e spegnimento.
- Ritorno al programma automatico corrente.
- Dieci temperature predefinite modificabili con entità number: sei per riscaldamento e quattro per raffrescamento.
- Lettura e modifica della settimana del programma corrente, con editor visuale incluso.
- Bozze, riepilogo delle modifiche e controllo delle revisioni prima del salvataggio.
- Lettura di conferma dopo i comandi.
- Polling condiviso, gestione degli errori e riautenticazione.
- Traduzioni italiane e inglesi.

Non sono esposti comandi per manuale permanente, selezione di un preset attivo, fan-coil, cambio di programma/stagione o geofence.

## Compatibilità

Richiede Home Assistant 2026.2.3 o successivo, un account funzionante nell’app ufficiale K-Domo e accesso HTTPS a giacomini.kblue.cloud. L’accettazione della privacy va completata nell’app ufficiale.

Le versioni HA coperte dalla suite sono 2026.2.3 e 2026.10.4. Il collaudo sulla specifica istanza HA e sul firmware dell’installazione resta necessario. Raffrescamento e Fahrenheit non hanno una validazione fisica completa.

È una custom integration per Home Assistant Core. Non richiede un add-on, un broker MQTT o una connessione locale ai termostati.

## Installazione

Questa integrazione è in versione alpha. Prima di installarla, leggere i limiti e verificare la compatibilità con il proprio impianto.

1. Scaricare il repository oppure clonarlo:

```sh
git clone https://github.com/MarcoBBo/ha-giacomini-kdomo-public.git
```

2. Copiare la cartella custom_components/kdomo nella directory di configurazione di HA. Il percorso finale deve essere config/custom_components/kdomo/manifest.json.
3. Riavviare Home Assistant.
4. Aprire Impostazioni → Dispositivi e servizi → Aggiungi integrazione.
5. Cercare Giacomini K-Domo e seguire la configurazione.

### HACS / Marketplace

Aggiungere `https://github.com/MarcoBBo/ha-giacomini-kdomo-public` come repository personalizzato di tipo **Integrazione**, quindi scaricare la versione desiderata e riavviare Home Assistant. Il progetto non è presente nel catalogo predefinito. In Home Assistant 2026.11 e successivi, verificare la disponibilità del Marketplace integrato. Conservare la configurazione esistente quando si aggiorna; non rimuovere e ricreare l'integrazione. La scheda visuale richiede inoltre la registrazione della risorsa descritta sotto.

## Configurazione

Inserire username e password dell’account K-Domo. Scegliere l’impianto da importare e confrontare le entità create con l’app ufficiale.

I controlli sono inizialmente disabilitati. Per attivarli, aprire le opzioni dell’integrazione e abilitare “Abilita i controlli dei termostati”. L’attivazione dell’opzione non invia comandi.

Il polling predefinito è di 60 secondi, configurabile tra 60 e 600. Dopo l’aggiunta o la rimozione di termostati nell’app, ricaricare l’integrazione per aggiornare l’inventario.

## Entità

Ogni termostato crea una entità climate, un sensore temperatura, un sensore umidità e un sensore binario di connessione. Sono presenti anche dieci entità number nella sezione Configurazione del dispositivo. Le entità condividono le stesse letture.

La climate riporta anche gli attributi kdomo_mode, kdomo_status, kdomo_program e kdomo_fancoil. Lo stato “acceso” non indica necessariamente che il relè stia erogando calore. L’integrazione non deduce hvac_action dalla differenza fra temperatura e target.

Se il cloud riporta il termostato offline, il sensore connessione mostra spento e le altre entità diventano indisponibili.

## Utilizzo

### Accendere in manuale temporaneo a 22 °C

Con un programma di riscaldamento attivo:

```yaml
action: climate.set_temperature
target:
  entity_id: climate.example_room
data:
  hvac_mode: heat
  temperature: 22
```

La temperatura usa l’unità configurata in HA. Per cambiare il target conservando lo stato acceso/spento, omettere hvac_mode.

### Riprendere il programma automatico

```yaml
action: climate.set_hvac_mode
target:
  entity_id: climate.example_room
data:
  hvac_mode: auto
```

Questa azione accende il termostato e riprende il programma selezionato in K-Domo.

### Spegnere

```yaml
action: climate.turn_off
target:
  entity_id: climate.example_room
```

HEAT e COOL sono disponibili in base al tipo del programma corrente. Non cambiano automaticamente la stagione o il programma. Il manuale è temporaneo secondo la logica nativa K-Domo: non viene aggiunto un timer di ripristino.

### Modificare le temperature predefinite

Aprire il dispositivo K-Domo in Impostazioni → Dispositivi e servizi e la sezione Configurazione. Sono disponibili:

- Riscaldamento: Comfort, Comfort+, Notte, Economy, Economy+ e Antigelo.
- Raffrescamento: Comfort, Comfort+, Notte ed Economy.

Le entità sono utilizzabili in dashboard e automazioni tramite number.set_value. Copiare l'entity_id effettivo dall'istanza HA; il seguente è solo un esempio:

```yaml
action: number.set_value
target:
  entity_id: number.example_room_heating_comfort
data:
  value: 22
```

L'unità è quella visualizzata da Home Assistant; HA gestisce la conversione rispetto alla scala del dispositivo. Passo UI di 0,5 nell'unità nativa; precisione del protocollo 0,1. I limiti conservativi sono 0–35 °C o 32–95 °F e non attestano tutti i limiti del firmware.

Cambiare una temperatura predefinita cambia il livello usato dalle fasce che lo richiamano, senza modificare gli orari, selezionare un programma, accendere il termostato o passare in manuale. Se quel livello è in uso, la regolazione può risentirne subito.

La modifica usa i gruppi cloud 10/11: lettura preventiva dell'intero gruppo, conservazione delle altre temperature e dei selettori di regolazione/geofence, un solo invio e conferma tramite rilettura. Se mancano campi necessari, l'azione fallisce senza inviare il comando. I campi assenti o non numerici e le scale sconosciute rendono indisponibili i relativi controlli. I valori non vengono inventati.

Le nuove scritture sono coperte da test su cloud simulato; il collaudo fisico dei gruppi 10/11 resta da eseguire. Il problema già osservato nella conferma del setpoint climate con termostato spento/in automatico non viene risolto da questa versione.

### Aggiornamento da 0.1.0 o 0.3.0

Sostituire la cartella custom_components/kdomo con quella di 0.4.0 e riavviare HA. Non rimuovere e ricreare la configurazione: le entità esistenti e le opzioni vengono mantenute. Se i controlli erano già abilitati, restano abilitati anche per le nuove temperature. L'aggiornamento non invia comandi.

### Editor visuale della settimana

La scheda è inclusa nel componente e viene servita da Home Assistant. Non richiede un sito esterno, un account aggiuntivo, una modifica al codice Core o una seconda copia del JavaScript in www.

Dopo l’aggiornamento alla 0.4.0:

1. Aprire Impostazioni → Dashboard → menu → Risorse, con la modalità avanzata del profilo se necessaria.
2. Aggiungere /kdomo/kdomo-schedule-card.js?v=0.4.0 come modulo JavaScript. Se le risorse della propria istanza sono gestite in YAML, aggiungere lì la stessa risorsa senza cambiare modalità.
3. Ricaricare il browser e aggiungere alla dashboard la scheda “K-Domo · Programmazione”. Selezionare il termostato nell’editor della scheda.

Configurazione equivalente:

```yaml
type: custom:kdomo-schedule-card
entity: climate.studio
```

La scheda mostra i sette giorni e le fasce del programma corrente. Selezionare una fascia per cambiarne livello o orario finale; sul desktop si può trascinare il confine destro della fascia selezionata. Il controllo sottostante e l’orario numerico sono disponibili anche da telefono e tastiera. Il selettore “Seleziona fascia” permette di raggiungere anche gli intervalli troppo brevi per un tocco preciso sulla settimana. La temperatura dei livelli usa le unità preferite in HA.

Sono disponibili divisione e unione delle fasce, fino a otto per giorno, e copia della giornata sui feriali, sul fine settimana o sull’intera settimana. Le modifiche restano nella bozza del browser finché non vengono salvate; ricaricare o chiudere la pagina può perderle. “Ricarica” richiede di scartare esplicitamente una bozza modificata.

Per inviare un programma occorre abilitare sia i controlli generali sia “Abilita modifica pianificazioni (sperimentale)” nelle opzioni K-Domo. Quest’ultima parte disabilitata anche se i vecchi controlli erano già attivi. Setup, installazione della risorsa e letture non scrivono all’impianto.

“Salva settimana” mostra i giorni modificati con un riepilogo prima/dopo; “Conferma invio” esegue una sola scrittura cloud e ne verifica la rilettura. Se app o termostato hanno cambiato programma o pianificazione mentre si lavorava, l’azione viene rifiutata: ricaricare prima di riprovare. Questo controllo non rende atomica la modifica rispetto a un altro client che scriva esattamente tra lettura e invio.

Si modifica solo la settimana del programma corrente e non se ne cambia la selezione. Nome, tipo, giorni invariati e relativi campi wire vengono conservati. Una settimana incompleta o composta da giorni di programmi diversi viene rifiutata senza sostituirla con un esempio. Gli orari sono quelli locali del termostato; fine giornata è rappresentata come 24:00 nella scheda e come 23:59 nel protocollo. La semantica esatta del minuto finale richiede collaudo sul firmware.

Non viene creato un secondo pianificatore HA: dopo il salvataggio K-Domo esegue i suoi orari anche se HA è spento. La 0.4.0 fornisce la scheda dedicata e le azioni sotto indicate; non crea un’entità calendar, non seleziona programmi inattivi e non presume di poter leggere tutte le loro settimane.

La scrittura del gruppo 03 è verificata con un cloud sintetico e non ancora collaudata fisicamente sul termostato. Prima di usarla su una settimana reale, eseguire un collaudo controllato e autorizzato su un solo dispositivo e conservare la pianificazione iniziale.

### Azioni per script e automazioni

kdomo.get_schedule riceve entity_id di un singolo climate K-Domo e restituisce il programma corrente, days, levels, scale, write_enabled e revision. L’azione richiede una risposta, per esempio con response_variable:

```yaml
action: kdomo.get_schedule
data:
  entity_id: climate.studio
response_variable: programma_studio
```

kdomo.set_schedule riceve entity_id, revision restituita dalla lettura e l’intera lista days. Ogni giorno ha day (0=domenica…6=sabato) e slots; ogni slot ha level (id dalla risposta levels) ed end in minuti da mezzanotte. Gli orari devono crescere, senza buchi, terminare a 1440 e avere da una a otto fasce per giorno. Il minuto 1439 è riservato alla rappresentazione wire del confine finale: usare 1440.

La revisione comprende metadati, sette giorni e temperature/scala dei livelli per rilevare una bozza non più attuale. L’azione richiede una settimana completa; non inviare solo i giorni modificati. Non registrare password o token in YAML o nella scheda. Il backend verifica i permessi HA di lettura/controllo della singola entità. Non è necessario passare identificativi cloud o credenziali al browser.

## Limiti

La risposta positiva a un comando non garantisce che il dispositivo lo abbia applicato. L’integrazione rilegge lo stato prima di confermare l’azione. In caso di mancata conferma, l’azione restituisce errore e conserva l’ultimo stato letto.

Un comando può richiedere diversi secondi. Dopo un timeout o un errore, controllare app e termostato prima di ripetere. Non vengono eseguiti replay o rollback automatici.

Il manuale permanente non è disponibile fra i controlli. La durata del manuale temporaneo e la compatibilità con altri firmware richiedono ulteriore verifica.

## Credenziali e diagnostica

Home Assistant conserva username e password nella ConfigEntry sotto .storage, per consentire un nuovo login. Non viene aggiunta una cifratura proprietaria; proteggere configurazione e backup. Il token resta in memoria.

La diagnostica dell’integrazione omette credenziali, nomi, seriali e identificativi degli impianti. Non allegare alle issue configurazioni complete, token, header HTTP o risposte grezze dell’account.

## Risoluzione problemi

Integrazione assente dall’elenco: controllare il percorso dei file, riavviare HA e aggiornare completamente la pagina.

Accesso rifiutato: verificare le credenziali nell’app ufficiale e completare eventuali richieste di accettazione della privacy. Usare il flusso di riautenticazione quando proposto da HA.

Controlli disabilitati: abilitarli nelle opzioni.

HEAT o COOL non disponibile: il programma corrente appartiene all’altra stagione oppure mancano metadati affidabili. Il programma non viene cambiato automaticamente.

Comando non confermato: controllare lo stato reale e attendere prima di ripetere.

## Documentazione

- [Specifica del protocollo cloud](docs/PROTOCOLLO_KDOMO.md).
- [Specifica OpenAPI](docs/openapi.json).
- [Architettura Home Assistant](docs/HOME_ASSISTANT.md).
- [Validazione e compatibilità](docs/VALIDAZIONE.md).
- [Distribuzione del repository](docs/PUBBLICAZIONE.md).
- [Contributi e sviluppo locale](CONTRIBUTING.md).
- [Changelog](CHANGELOG.md).
- [Segnalazioni di sicurezza](SECURITY.md).

La specifica del protocollo descrive il contratto tecnico. I risultati della validazione sono conservati separatamente.

## Supporto e contributi

Usare le [issue del repository](https://github.com/MarcoBBo/ha-giacomini-kdomo-public/issues), indicando versione HA, versione dell’integrazione, comportamento atteso e osservato. Allegare solo diagnostica anonimizzata.

Per sviluppo, test e build consultare CONTRIBUTING.md. Il progetto è distribuito con [licenza MIT](LICENSE); i nomi e i marchi di terzi restano dei rispettivi titolari, come indicato in [NOTICE.md](NOTICE.md).

English: independent Giacomini K-Domo cloud integration for Home Assistant. UI setup, plant selection, climate and environmental entities, temporary manual targets, native schedule resume and ten configurable temperature levels. Controls are disabled by default. Fixed manual mode and inactive-program selection are not exposed. Current-program weekly editing is available through a bundled custom card; schedule writes require a separate opt-in and physical validation.
