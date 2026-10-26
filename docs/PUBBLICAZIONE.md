# Distribuzione del progetto

Repository: https://github.com/MarcoBBo/ha-giacomini-kdomo

Maintainer: MarcoBBo. Ramo principale: main. Versione iniziale: 0.1.0 alpha.

Repository creato dal proprietario e verificato il 26 ottobre 2026 come privato, con ramo principale main. La destinazione è configurata nel manifest, nei riferimenti OpenAPI e in CODEOWNERS.

## Visibilità

La prima pubblicazione è autorizzata esclusivamente come repository privato. La presenza di licenza MIT o istruzioni di installazione non autorizza a renderlo pubblico.

Durante questa fase si distribuisce il codice attraverso gli accessi autorizzati del repository e si usa l’installazione manuale. Non viene richiesta l’inclusione nel catalogo HACS.

## Contenuti del repository

Codice della custom integration, specifica del protocollo, OpenAPI, istruzioni, test, workflow CI, template per issue e pull request.

Non caricare APK, sorgenti decompilati, chiavi, token, credenziali, seriali reali o risposte private degli account. La cronologia della ricerca non fa parte della specifica del protocollo.

## Controlli dopo il primo push

Verificare owner, nome, ramo e visibilità privata tramite GitHub autenticato. Verificare che la specifica sia leggibile in docs/PROTOCOLLO_KDOMO.md e raggiungibile dal README.

Il workflow Offline tests verifica le due versioni Python/HA. L’esecuzione remota va distinta dai risultati locali già registrati in VALIDAZIONE.md.

Il workflow Publication validators può essere avviato separatamente. La verifica HACS richiede un repository pubblico e non è un requisito per il collaudo privato; non cambiare la visibilità per farla passare.

## Rilascio pubblico futuro

Solo dopo una nuova autorizzazione: rivalutare compatibilità e limiti, completare il collaudo HA reale, verificare i requisiti correnti HACS e brand, predisporre un canale di segnalazione di sicurezza e risolvere gli errori dei validatori.

Una eventuale release GitHub e l’inclusione nel catalogo HACS sono operazioni distinte dalla pubblicazione del repository privato.

## Pacchetti

```sh
python scripts/build_release.py
```

La build produce l’archivio completo, lo ZIP installabile e i checksum sotto dist. Questi output non vanno aggiunti alla cronologia Git del sorgente; possono essere allegati a una release quando richiesta.

Lo script configure_repository.py rimane disponibile per configurare una copia o un futuro cambio di destinazione. La configurazione corrente usa già MarcoBBo/ha-giacomini-kdomo.
