# Distribuzione del progetto

Repository: https://github.com/MarcoBBo/ha-giacomini-kdomo. Maintainer: MarcoBBo.

## Installazione e aggiornamenti

Aggiungere il repository come integrazione personalizzata in HACS o nel Marketplace compatibile. Il progetto non è incluso nel catalogo predefinito. Le release GitHub identificano le versioni distribuite; il numero di versione della release deve corrispondere al manifest. Seguire il README per registrare la risorsa della scheda visuale e riavviare Home Assistant quando richiesto.

La versione 0.4.0 è alpha. Le scritture delle pianificazioni sono disabilitate per default e non hanno ancora un collaudo fisico completo; consultare README e VALIDAZIONE.md per limiti e prove.

## Contenuti e controlli

Il repository contiene l'integrazione, specifica di interoperabilità, documentazione, test e workflow. Non caricare APK, sorgenti decompilati, chiavi, token, credenziali, seriali reali o risposte private degli account.

Prima di una release verificare la suite, i validatori e la compatibilità con Home Assistant; non confondere test sintetici e collaudo fisico. La pubblicazione di una release o la richiesta di inclusione nel catalogo sono operazioni distinte dalla visibilità del repository.

## Pacchetti

```sh
python scripts/build_release.py
```

La build produce l'archivio completo, lo ZIP installabile e i checksum sotto dist. Gli output non vanno aggiunti alla cronologia Git del sorgente; possono essere allegati alle release.
