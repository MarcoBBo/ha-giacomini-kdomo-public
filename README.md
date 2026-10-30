# Giacomini K-Domo per Home Assistant

Integrazione indipendente per controllare i termostati Giacomini K-Domo attraverso il cloud. Espone dispositivi, entità clima, temperatura, umidità e stato della connessione in Home Assistant.

Versione 0.3.0 alpha. I controlli partono disabilitati e si attivano dalle opzioni. L’integrazione conserva le pianificazioni già impostate in K-Domo.

Il progetto usa un’interfaccia cloud non ufficiale. Non è affiliato o approvato da Giacomini.

## Funzioni

- Configurazione dalla UI con account K-Domo e scelta dell’impianto.
- Una entità clima per termostato.
- Sensori di temperatura, umidità e connessione cloud.
- Setpoint in manuale temporaneo, accensione e spegnimento.
- Ritorno al programma automatico corrente.
- Dieci temperature predefinite modificabili con entità number: sei per riscaldamento e quattro per raffrescamento.
- Lettura di conferma dopo i comandi.
- Polling condiviso, gestione degli errori e riautenticazione.
- Traduzioni italiane e inglesi.

Non sono esposti comandi per manuale permanente, modifica delle fasce orarie, selezione di un preset attivo, fan-coil, cambio di programma/stagione o geofence.

## Compatibilità

Richiede Home Assistant 2026.2.3 o successivo, un account funzionante nell’app ufficiale K-Domo e accesso HTTPS a giacomini.kblue.cloud. L’accettazione della privacy va completata nell’app ufficiale.

Le versioni HA coperte dalla suite sono 2026.2.3 e 2026.10.4. Il collaudo sulla specifica istanza HA e sul firmware dell’installazione resta necessario. Raffrescamento e Fahrenheit non hanno una validazione fisica completa.

È una custom integration per Home Assistant Core. Non richiede un add-on, un broker MQTT o una connessione locale ai termostati.

## Installazione

Il repository è destinato inizialmente all’accesso privato. Usare l’installazione manuale con un account GitHub autorizzato.

1. Scaricare il repository oppure clonarlo:

```sh
git clone https://github.com/MarcoBBo/ha-giacomini-kdomo.git
```

2. Copiare la cartella custom_components/kdomo nella directory di configurazione di HA. Il percorso finale deve essere config/custom_components/kdomo/manifest.json.
3. Riavviare Home Assistant.
4. Aprire Impostazioni → Dispositivi e servizi → Aggiungi integrazione.
5. Cercare Giacomini K-Domo e seguire la configurazione.

HACS richiede un repository pubblico. L’installazione tramite HACS verrà documentata quando sarà autorizzata una distribuzione pubblica; il progetto non è incluso nel catalogo predefinito.

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

### Aggiornamento da 0.1.0

Sostituire la cartella custom_components/kdomo con quella di 0.3.0 e riavviare HA. Non rimuovere e ricreare la configurazione: le entità esistenti e le opzioni vengono mantenute. Se i controlli erano già abilitati, restano abilitati anche per le nuove temperature. L'aggiornamento non invia comandi.

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

Usare le [issue del repository](https://github.com/MarcoBBo/ha-giacomini-kdomo/issues), indicando versione HA, versione dell’integrazione, comportamento atteso e osservato. Allegare solo diagnostica anonimizzata.

Per sviluppo, test e build consultare CONTRIBUTING.md. Il progetto è distribuito con [licenza MIT](LICENSE); i nomi e i marchi di terzi restano dei rispettivi titolari, come indicato in [NOTICE.md](NOTICE.md).

English: independent Giacomini K-Domo cloud integration for Home Assistant. UI setup, plant selection, climate and environmental entities, temporary manual targets, native schedule resume and ten configurable temperature levels. Controls are disabled by default. Fixed manual mode and schedule editing are not exposed.
