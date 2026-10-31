Giacomini K-Domo
Specifica del protocollo cloud
Revisione 3 — 31 ottobre 2026

1. Ambito e convenzioni

Il protocollo consente a un client di autenticarsi, individuare gli impianti associati all’account, leggere i parametri dei termostati e inviare comandi attraverso il cloud Giacomini K-Domo.

La specifica riguarda l’interfaccia HTTP tra client e cloud. Il trasporto tra cloud e termostati non rientra nel suo ambito. Il documento è una specifica indipendente di interoperabilità, non una specifica ufficiale del produttore.

I termini DEVE, NON DEVE e DOVREBBE indicano rispettivamente un requisito, un divieto e una raccomandazione per i client conformi al profilo qui descritto. Le caratteristiche indicate come non definite non costituiscono garanzie del servizio.

Le parentesi graffe nei percorsi identificano parametri da sostituire. I nomi dei campi JSON e dei parametri sono sensibili a maiuscole e minuscole. Tutti gli identificativi e le credenziali negli esempi sono segnaposto.

2. Trasporto e serializzazione

2.1 Endpoint di produzione

```text
https://giacomini.kblue.cloud/
```

I percorsi successivi sono relativi a questo endpoint.

Il client DEVE utilizzare HTTPS e verificare il certificato TLS e il nome del server. NON DEVE trasferire password o token a un altro endpoint attraverso redirect automatici.

2.2 Formato delle richieste

I corpi delle richieste sono oggetti JSON codificati in UTF-8.

```http
Accept: application/json
Content-Type: application/json
```

Content-Type si applica alle richieste con corpo. Le richieste autenticate includono inoltre:

```http
X-Auth-Token: <token>
```

Il valore dell’header è il token completo. Non si aggiunge il prefisso Bearer e non si sostituisce questo header con Authorization.

2.3 Tipi di dati

Gli identificativi di impianti e risorse sono stringhe opache. Un seriale composto da cifre DEVE rimanere una stringa, senza conversione in numero.

I timestamp delle misure, nel campo when, sono espressi in secondi Unix. Il campo requesttime dei metadati dei comandi è espresso in millisecondi Unix.

Le temperature nei comandi sono stringhe decimali con punto come separatore, segno positivo e una cifra decimale:

```text
+09.5
+21.0
+22.5
```

La parte numerica ha larghezza minima di quattro caratteri, compreso il punto. La precisione di questo formato non determina il passo di regolazione consentito da ciascun dispositivo.

I campi estranei al gruppo di comando selezionato DOVREBBERO essere omessi. Il client NON DEVE inviare valori null o zeri come sostituti di impostazioni sconosciute.

3. Autenticazione

3.1 Creazione della sessione

```http
POST /auth/v2
```

Richiesta:

```json
{
  "username": "user@example.invalid",
  "password": "example-password"
}
```

username: stringa, obbligatoria. Nome utente dell’account K-Domo.

password: stringa, obbligatoria. Password dell’account.

Risposta:

```json
{
  "token": "opaque-example-token",
  "privacyAccepted": true
}
```

token: stringa non vuota. Credenziale da utilizzare per le richieste successive.

privacyAccepted: booleano. Indica lo stato di accettazione della privacy associato all’account.

Il client DEVE trattare il token come opaco e riservato. Non è definito un formato da decodificare per determinarne identità o scadenza.

Se privacyAccepted non è true, il client DOVREBBE richiedere il completamento della procedura nell’app ufficiale prima di proseguire. L’autenticazione non implica l’autorizzazione ad accettare condizioni per conto dell’utente.

3.2 Uso e rinnovo della sessione

Le richieste successive trasmettono il token in X-Auth-Token. Le credenziali username/password non vanno aggiunte alle richieste di lettura o di comando.

Questa specifica non definisce un endpoint di refresh, una durata del token o un meccanismo di revoca. Un client può creare una nuova sessione ripetendo POST /auth/v2.

In caso di rifiuto dell’autenticazione, il client DOVREBBE limitare i tentativi di nuovo login. Il rinnovo della sessione NON DEVE causare la ripetizione automatica di un comando con esito incerto.

Non sono definiti numero massimo di sessioni concorrenti e regole di invalidazione fra sessioni dello stesso account.

4. Risorse e identificativi

4.1 Elenco degli impianti

```http
GET /plants
```

Richiede autenticazione.

Risposta:

```json
{
  "data": [
    {
      "id": "plant-example",
      "name": "Example plant",
      "thermostats": [
        {
          "id": "internal-thermostat-id",
          "name": "Example room",
          "serial": "serial-example",
          "isHub": true
        }
      ]
    }
  ]
}
```

data: array degli impianti accessibili all’account.

id dell’impianto: identificativo da utilizzare come plantId nei percorsi.

name: nome descrittivo dell’impianto o del termostato.

thermostats: array dei termostati associati all’impianto.

serial: identificativo da utilizzare come resourceId nei percorsi del termostato.

id del termostato: identificativo interno distinto dal seriale. NON DEVE sostituire resourceId.

isHub: indicatore della funzione hub della risorsa. Il valore true non esclude che la risorsa sia anche un termostato interrogabile.

Il client DEVE utilizzare risorse restituite per il proprio account. I segmenti dei percorsi DEVONO essere codificati singolarmente mediante percent-encoding.

4.2 Identità della risorsa

La coppia plantId e resourceId identifica il termostato nell’interfaccia qui descritta. I nomi sono etichette modificabili e NON DEVONO essere utilizzati come identificativi stabili.

5. Lettura dei parametri

5.1 Endpoint

```http
GET /thermostats/{plantId}/{resourceId}/lasts/parameters/{parameters}
```

Richiede autenticazione.

plantId: id dell’impianto restituito da GET /plants.

resourceId: serial del termostato restituito da GET /plants.

parameters: elenco di nomi separati da virgole, senza spazi.

Esempio:

```http
GET /thermostats/plant-example/serial-example/lasts/parameters/temperature,humidity,currentsetpoint,mode,program,status,scale,fancoil
```

5.2 Risposta

La risposta è un array JSON, senza oggetto contenitore data:

```json
[
  {
    "parameter": "temperature",
    "resId": "serial-example",
    "when": 1793000000,
    "doubleVal": 20.4
  },
  {
    "parameter": "currentsetpoint",
    "resId": "serial-example",
    "when": 1793000001,
    "stringVal": "+21.0"
  },
  {
    "parameter": "mode",
    "resId": "serial-example",
    "when": 1793000001,
    "intVal": 1
  }
]
```

parameter: stringa. Nome del parametro.

resId: stringa. Identificativo della risorsa.

when: numero. Timestamp della misura in secondi Unix.

intVal: intero o null. Rappresentazione intera del valore.

doubleVal: numero o null. Rappresentazione decimale del valore.

stringVal: stringa o null. Rappresentazione testuale del valore.

La risposta può includere metadati aggiuntivi. Il client DOVREBBE tollerare campi sconosciuti.

5.3 Regole di decodifica

Quando più rappresentazioni sono presenti e non null, la precedenza è:

```text
stringVal > doubleVal > intVal
```

Se nessuna rappresentazione contiene un valore, il parametro non è disponibile. L’assenza NON DEVE essere convertita implicitamente in zero.

I parametri numerici DEVONO essere interpretati secondo la propria semantica anche quando il valore è restituito come stringa. Per esempio, 21, 21.0 e "+21.0" rappresentano lo stesso valore numerico di setpoint.

Il client NON DEVE dipendere dall’ordine degli elementi nell’array. Se riceve più misure per lo stesso parametro, DOVREBBE utilizzare quella con when più recente.

5.4 Consistenza temporale

lasts restituisce l’ultimo valore disponibile di ciascun parametro. I timestamp possono differire: la risposta non rappresenta necessariamente una lettura simultanea del dispositivo.

Una risposta HTTP recente può contenere misure anteriori a un comando. Il client DEVE distinguere il momento della richiesta HTTP dal timestamp di ciascuna misura.

6. Dizionario dei parametri

6.1 Parametri correnti

name: nome della risorsa, stringa.

temperature: temperatura ambientale misurata, nella scala indicata da scale.

humidity: umidità relativa in percentuale, se disponibile.

currentsetpoint: temperatura obiettivo corrente, nella scala indicata da scale.

mode: modalità di regolazione, secondo il paragrafo 7.1.

program: indice del programma selezionato, da 0 a 5 nel profilo descritto.

status: stato logico del termostato, secondo il paragrafo 7.2.

scale: scala di temperatura. 0 identifica Celsius; 1 identifica Fahrenheit nel profilo descritto. Altri valori non sono definiti.

fancoil: impostazione del fan-coil. La mappatura completa dei livelli non è definita. Un client che non gestisce questa funzione DEVE conservarne il valore durante le modifiche del gruppo 02.

6.2 Programmi e giorni

prog0, prog1, prog2, prog3, prog4, prog5: metadati dei programmi, nel formato del paragrafo 10.1.

progDay0, progDay1, progDay2, progDay3, progDay4, progDay5, progDay6: pianificazioni giornaliere, nel formato del paragrafo 10.2.

I metadati di un programma non contengono la sua intera settimana. La presente specifica non definisce un parametro di richiesta per selezionare la settimana di un programma diverso da quello reso disponibile dal cloud.

6.3 Parametri termici

Riscaldamento:

```text
heatingtempcomfort
heatingtempcomfortplus
heatingtempnight
heatingtempeconomy
```

Raffrescamento:

```text
coolingtempcomfort
coolingtempcomfortplus
coolingtempnight
coolingtempeconomy
```

Ulteriori temperature:

```text
tempantifreeze
tempeconomyplus
```

Sono temperature configurate per il singolo dispositivo. Un nome come Comfort non identifica una temperatura fissa universale.

6.4 Parametri aggiuntivi

```text
heatingtype
coolingtype
heatinggeoinhome
heatinggeoouthome
coolinggeoinhome
coolinggeoouthome
domoticsettings
deviceconfig
deviceEnable
geostatustermostato
addon
```

La disponibilità dipende dalla risorsa. Questa specifica non assegna una semantica completa ai relativi valori e non definisce valori predefiniti da inviare in loro assenza.

7. Modalità e stato

7.1 Modalità di regolazione: mode

0: manuale permanente.

1: automatico, secondo il programma selezionato.

2: manuale temporaneo, con setpoint corrente esplicito.

La disponibilità effettiva del manuale permanente dipende dal dispositivo e dalle condizioni applicative del servizio. L’accettazione del relativo comando non garantisce una transizione a mode=0.

Il manuale temporaneo non definisce una durata universale. Il ritorno alla pianificazione segue la logica del dispositivo. Questa interfaccia non espone un campo di durata nel gruppo 02.

7.2 Stato logico: status

0: spento.

1: acceso.

2: antigelo.

status e mode sono dimensioni distinte. Un termostato spento può conservare modalità automatica e un setpoint numerico. status=1 non rappresenta una misura dello stato del relè o della valvola.

7.3 Tipo di programma

Il tipo termico è contenuto nei metadati del programma selezionato. Nel profilo descritto, 0 identifica riscaldamento e 1 raffrescamento. La sola modalità mode non determina quale delle due funzioni sia attiva.

8. Stato online

```http
GET /thermostats/{plantId}/{resourceId}/isonline
```

Richiede autenticazione.

Risposta:

```json
{
  "data": true
}
```

data è un booleano e indica la disponibilità della risorsa secondo il cloud.

Il valore non rappresenta un controllo diretto della rete locale né una conferma di esecuzione di un comando. Le ultime misure possono rimanere disponibili anche quando il dispositivo è offline.

9. Invio dei comandi

9.1 Endpoint generale

```http
POST /thermostats/{plantId}/{resourceId}/sendCommand/{topic}
```

Richiede autenticazione.

topic seleziona il gruppo di parametri del comando. Deve essere trasmesso come stringa di percorso, conservando gli zeri iniziali: 02 e 2 non sono forme da considerare intercambiabili.

Il corpo è un oggetto JSON specifico per il topic. Non è la stringa serializzata restituita nei metadati requestmessage.

9.2 Topic 02: impostazioni correnti

```http
POST /thermostats/{plantId}/{resourceId}/sendCommand/02
```

Corpo:

```json
{
  "mode": 2,
  "program": 0,
  "status": 1,
  "currentsetpoint": "+22.0",
  "fancoil": "0"
}
```

mode: intero. Modalità richiesta.

program: intero. Indice del programma selezionato.

status: intero. Stato logico richiesto.

currentsetpoint: stringa. Temperatura obiettivo nel formato del paragrafo 2.3 e nella scala corrente del dispositivo.

fancoil: stringa. Impostazione fan-coil.

Il client DEVE trattare questi cinque campi come un unico gruppo di impostazioni. Prima di modificarne una parte, DEVE acquisire i valori correnti dei campi da conservare. Non è definita una semantica PATCH per l’omissione dei campi del gruppo.

L’intervallo hardware dei setpoint non è definito universalmente da questa interfaccia. Un client può adottare un profilo di accettazione 0–35 °C e 32–95 °F, ma NON DEVE presentarlo come capacità garantita di ogni dispositivo.

9.3 Operazioni sul gruppo 02

Modifica temporanea del target: impostare currentsetpoint al valore richiesto e mode=2. Conservare program, status e fancoil quando non fanno parte dell’intenzione di modifica.

Accensione in manuale temporaneo: impostare status=1, mode=2 e il target richiesto. Conservare program e fancoil.

Spegnimento: impostare status=0 e conservare gli altri campi, salvo modifiche esplicitamente richieste.

Ritorno all’automatico: impostare mode=1. Per riprendere attivamente la regolazione, impostare anche status=1. Conservare program e fancoil. Il setpoint successivamente riportato può essere aggiornato dalla pianificazione.

Accensione senza cambio della modalità: impostare status=1 e conservare i restanti campi correnti.

Il gruppo 02 seleziona un programma tramite il suo indice; non contiene la definizione delle fasce orarie né le temperature dei preset. Modificare il target corrente non richiede la riscrittura della pianificazione.

9.4 Risposta al comando

La risposta contiene un oggetto data con metadati del comando:

```json
{
  "data": {
    "id": null,
    "correlationid": null,
    "expectreply": false,
    "requesttopic": "02",
    "requestmessage": "1;2;0;+22.0;0",
    "requesttime": 1793000001000,
    "responsemessage": null
  }
}
```

id: stringa o null. Identificativo del comando, se assegnato.

correlationid: stringa o null. Identificativo di correlazione, se disponibile.

expectreply: booleano o null. Indicatore associato all’attesa di una risposta.

requesttopic: stringa o null. Topic del comando.

requestmessage: stringa o null. Rappresentazione del messaggio prodotto dal servizio.

requesttime: numero intero. Timestamp della richiesta in millisecondi Unix.

responsemessage: stringa o null. Risposta associata al comando, se disponibile.

Possono comparire anche name, replyto, requestpattern, resourceid, responsepattern, responsetime e username. Tipi, presenza e disponibilità di questi campi non sono necessari per le operazioni di base qui descritte. Il client DEVE trattare username come dato riservato quando presente.

Per il topic 02, requestmessage segue l’ordine:

```text
status;mode;program;currentsetpoint;fancoil
```

Il client NON DEVE dipendere dalla presenza di id, correlationid o responsemessage per decidere se rileggere lo stato.

9.5 Accettazione ed esecuzione

Una risposta HTTP positiva conferma l’accettazione della richiesta da parte del servizio, non necessariamente l’applicazione al termostato.

Dopo un comando, il client DOVREBBE rileggere i parametri interessati e confrontare valori e timestamp con quelli acquisiti prima dell’invio. DOVREBBE distinguere almeno questi esiti:

- Richiesta rifiutata dal servizio.
- Richiesta accettata, applicazione non ancora confermata.
- Stato richiesto riportato dalle misure del cloud.
- Esito di trasmissione sconosciuto, per esempio dopo un timeout.

La conferma tramite cloud non certifica l’attivazione fisica del relè. Non è definito un tempo massimo di propagazione.

Non è definita una chiave di idempotenza. Un client NON DEVE ripetere automaticamente un comando con esito sconosciuto. Un eventuale ripristino è un ulteriore comando, non un annullamento transazionale del precedente.

10. Formati dei programmi e delle pianificazioni

10.1 Metadati del programma

I valori prog0 … prog5 hanno il formato:

```text
indice;nome;tipo;riservato
```

indice: indice del programma.

nome: etichetta del programma.

tipo: 0 per riscaldamento; 1 per raffrescamento nel profilo descritto. Altri valori non sono definiti da questa specifica.

riservato: campo trasmesso come 0. Non attribuirgli altri significati.

Esempi:

```text
0;Winter;0;0
1;Summer;1;0
```

Il separatore è il punto e virgola. Non è definito un meccanismo di escape per includerlo nel nome.

10.2 Pianificazione giornaliera

Ogni valore progDayN contiene esattamente 18 campi:

```text
programma;giorno;tipo1;fine1;tipo2;fine2;tipo3;fine3;tipo4;fine4;tipo5;fine5;tipo6;fine6;tipo7;fine7;tipo8;fine8
```

programma: indice del programma cui appartiene il giorno.

giorno: 0 domenica, 1 lunedì, 2 martedì, 3 mercoledì, 4 giovedì, 5 venerdì, 6 sabato.

tipoN: tipo della fascia.

fineN: fine della fascia nel formato HH:mm, nell’orario locale del dispositivo.

Sono presenti otto coppie tipo/fine. La prima fascia è attiva. Una coppia successiva rappresenta una fascia attiva se l’orario finale è strettamente successivo a quello della coppia precedente. Le coppie residue possono ripetere 0;23:59 e non rappresentano ulteriori intervalli attivi.

Esempio:

```text
0;1;2;05:00;1;23:30;2;23:59;0;23:59;0;23:59;0;23:59;0;23:59;0;23:59
```

Il giorno è lunedì. Le fasce attive sono Night fino alle 05:00, Comfort fino alle 23:30 e Night fino alle 23:59. La convenzione esatta di inclusione del minuto di confine dipende dal dispositivo.

10.3 Tipi di fascia per riscaldamento

0: Antigelo. Temperatura associata: tempantifreeze.

1: Comfort. Temperatura associata: heatingtempcomfort.

2: Night. Temperatura associata: heatingtempnight.

3: Economy. Temperatura associata: heatingtempeconomy.

4: Comfort Plus. Temperatura associata: heatingtempcomfortplus.

5: Economy Plus. Temperatura associata: tempeconomyplus.

6: Stop. Non definisce una temperatura numerica da sostituire al setpoint.

Per il raffrescamento la mappatura è distinta:

0: Comfort. Temperatura associata: coolingtempcomfort.

1: Night. Temperatura associata: coolingtempnight.

2: Economy. Temperatura associata: coolingtempeconomy.

3: Comfort Plus. Temperatura associata: coolingtempcomfortplus.

4: Stop. Non definisce una temperatura numerica da sostituire al setpoint.

Un client NON DEVE riusare gli identificativi di fascia del riscaldamento per il raffrescamento.

10.4 Topic 05: configurazione del programma

Corpo:

```json
{
  "programconf": "0;Winter;0;0"
}
```

programconf è una stringa con i quattro campi descritti al paragrafo 10.1. Questa operazione riguarda i metadati del programma.

10.5 Topic 03: pianificazione completa

Il corpo contiene una stringa nel campo completeschedule.

Il formato logico è:

```text
indice;nome;tipo;0;<fasce domenica>;<fasce lunedì>;...;<fasce sabato>
```

Ogni gruppo giornaliero comprende soltanto le otto coppie tipo/fine: non ripete indice del programma e numero del giorno. La posizione del gruppo identifica il giorno, nell’ordine da domenica a sabato.

La stringa comprende quindi 116 campi: quattro di prefisso e 16 per ciascuno dei sette giorni. Le parentesi angolari e i puntini del formato logico sono notazione descrittiva e non fanno parte del messaggio.

La specifica del formato non definisce tutte le precondizioni e i vincoli di accettazione della scrittura per ciascun firmware. Un client NON DEVE inviare una settimana incompleta presumendo che i giorni omessi rimangano invariati.

11. Ulteriori gruppi di comando

I gruppi seguenti condividono l’endpoint sendCommand/{topic}. Sono descritti a livello di struttura; intervalli ammessi, dipendenze e condizioni applicative non sono completamente definiti.

11.1 Topic 01: configurazione termostato

Campi previsti: lang, name, reg, scale, timezone.

lang, name e timezone sono stringhe; reg e scale sono interi. La presenza dei campi dipende dall’operazione di configurazione. Il formato completo di timezone e la semantica delle operazioni di registrazione non sono definiti qui.

11.2 Topic 10: parametri di riscaldamento

Campi interi:

```text
heatinggeoinhome
heatinggeoouthome
heatingtype
```

Campi temperatura, nel formato del paragrafo 2.3:

```text
heatingtempcomfort
heatingtempcomfortplus
heatingtempeconomy
heatingtempnight
tempantifreeze
tempeconomyplus
```

11.3 Topic 11: parametri di raffrescamento

Campi interi:

```text
coolinggeoinhome
coolinggeoouthome
coolingtype
```

Campi temperatura:

```text
coolingtempcomfort
coolingtempcomfortplus
coolingtempeconomy
coolingtempnight
```

11.4 Topic 21: notifica di stato associata al geofence

Campo previsto: status, intero.

Il dominio dei valori e le transizioni di questo topic non sono definiti in questa specifica. Il solo nome status NON DEVE indurre il client a trattarlo come equivalente al campo del gruppo 02.

11.5 Topic 40: registrazione impianto

Campi previsti: plantregistration, intero; plantname, stringa.

Le precondizioni del flusso di registrazione non sono definite. Questo topic non è necessario per leggere o comandare un termostato già associato all’account.

11.6 Topic 70: configurazione domotica

Campi previsti: Luci, Tapparelle, Ext. Tutti sono interi; le maiuscole dei nomi sono parte del formato.

La mappatura completa dei valori non è definita.

12. Errori e gestione del trasporto

Il client DEVE distinguere una risposta HTTP non riuscita da una risposta positiva con stato del dispositivo non ancora aggiornato.

Per 401 o 403 DOVREBBE gestire il rifiuto dell’autenticazione o dell’accesso senza avviare un ciclo illimitato di login. Un 403 non dimostra da solo che una password diversa risolverebbe il problema.

Per 429 DOVREBBE sospendere ulteriori richieste e rispettare Retry-After, se presente e interpretabile. Non è definito un limite numerico universale di richieste.

Per errori 5xx, interruzioni di connessione o timeout durante un POST di comando, l’esito applicativo può essere sconosciuto. Si applica la regola di non ripetizione automatica del paragrafo 9.5.

I corpi di errore non hanno uno schema stabile definito da questa specifica. Il client NON DEVE dipendere da una particolare stringa di errore e NON DEVE pubblicare corpi o header che contengano credenziali o dati dell’account.

13. Cache, polling e concorrenza

L’interfaccia di lettura qui descritta usa richieste periodiche. Non definisce un canale di sottoscrizione per le variazioni dei termostati.

Per ridurre il riuso di risposte HTTP, il client può inviare:

```http
Cache-Control: no-cache
Pragma: no-cache
```

Le richieste GET possono includere una query variabile:

```text
?_=<valore-univoco>
```

La query non è un timestamp della misura e non sostituisce when. Evitare la cache HTTP non garantisce che il dispositivo abbia già pubblicato un nuovo valore.

Non è definito un intervallo obbligatorio di polling. Ogni lettura del gruppo di parametri e ogni richiesta isonline è una operazione HTTP distinta. I client DOVREBBERO condividere le letture fra le proprie viste e limitare il carico del servizio.

Le modifiche del gruppo 02 seguono una sequenza di lettura, modifica e invio. Non è definita una transazione atomica o un controllo di versione condizionale. Un altro client può modificare lo stesso gruppo fra la lettura e il comando. Il client DOVREBBE serializzare le proprie scritture e acquisire impostazioni correnti prima di ogni modifica.

14. Caratteristiche non definite

Non sono definiti da questa specifica:

- Durata, revoca e numero massimo di sessioni.
- Rate limit del servizio e latenza massima di applicazione dei comandi.
- Idempotenza dei comandi e annullamento transazionale.
- Durata universale del manuale temporaneo.
- Supporto uniforme del manuale permanente su ogni dispositivo.
- Stato fisico del relè ricavabile dai soli mode e status.
- Limiti hardware universali dei setpoint e tutti i livelli fan-coil.
- Tutte le precondizioni dei gruppi di configurazione, geofence e registrazione.

Queste caratteristiche NON DEVONO essere dedotte dall’assenza di un errore HTTP.

15. Specifica elaborabile

Il file openapi.json nella stessa directory descrive il login e le quattro operazioni autenticate di base: elenco impianti, lettura parametri, stato online e invio del gruppo 02.

Le estensioni dei paragrafi 10 e 11 non sono rappresentate integralmente in quel file. Per i campi la cui semantica è indicata come non definita, non si deve presumere un contratto aggiuntivo.
