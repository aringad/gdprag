# 🛡️ GDPRag — RAG GDPR-Compliant

**GDPRag** (GDPR + RAG) è un sistema di Retrieval-Augmented Generation che ti permette di chattare con i tuoi documenti aziendali usando intelligenza artificiale **europea**.

Tutto configurabile dal browser — nessun file da modificare a mano.

## Perché GDPRag?

| | GDPRag | Soluzioni USA |
|---|---|---|
| **Provider AI** | Mistral AI (Parigi, Francia) | OpenAI, Google, etc. |
| **Giurisdizione** | GDPR (UE) | CLOUD Act (USA) |
| **Documenti** | Restano in locale | Spesso uploadati su cloud USA |
| **Training sui dati** | No | Dipende dal provider |
| **AI Act compliance** | Disclaimer incluso | Da implementare |

## Quick Start (3 minuti)

```bash
# 1. Clona il repository
git clone <repo-url> gdprag
cd gdprag

# 2. Configura
cp env.example .env
# Modifica DOCUMENTS_ROOT nel .env con il percorso dei tuoi documenti

# 3. Avvia
docker compose up -d

# 4. Apri il browser
open http://localhost:7860
```

Al primo avvio, vai nella tab **⚙️ Impostazioni** per:
1. Inserire la tua API key Mistral (gratuita su [console.mistral.ai](https://console.mistral.ai/))
2. Navigare le cartelle montate e selezionare quelle da indicizzare
3. Scegliere il modello AI

Poi vai in **📥 Gestione Documenti** → **📁 Cartelle configurate** → **🚀 Indicizza**.

## Come funziona

```
I tuoi documenti (PDF, DOCX, XLSX, PPTX, TXT, ...)
  │
  ▼
Estrazione testo + chunking (locale)
  │
  ▼
Mistral Embed API → vettori (cloud EU, $0.10/M token)
  │
  ▼
ChromaDB → database vettoriale (locale)
  │
  ▼  (domanda)
Ricerca similarità (locale)
  │
  ▼
Top 5 frammenti → Mistral Chat API (cloud EU)
  │
  ▼
Risposta con fonti
```

## Tab dell'interfaccia

| Tab | Funzione |
|---|---|
| **💬 Chat** | Chatta con i tuoi documenti |
| **📥 Gestione Documenti** | Indicizza cartelle configurate, percorsi manuali o upload |
| **⚙️ Impostazioni** | API key, modello AI, gestione cartelle |
| **ℹ️ Info** | Architettura, compliance, costi |

## Formati supportati

PDF, DOCX, DOC, XLSX, XLS, PPTX, HTML, TXT, MD, CSV, JSON, ODT, RTF

## Configurazione

### File .env (minimo)

| Variabile | Descrizione | Default |
|---|---|---|
| `DOCUMENTS_ROOT` | Cartella radice dei documenti | `./documenti` |
| `MISTRAL_API_KEY` | API key (opzionale — configurabile da UI) | — |

### Dalla UI (tab ⚙️ Impostazioni)

- **API Key Mistral** — inserisci, salva e verifica con un click
- **Modello AI** — Small (veloce/economico), Medium, Large (massima qualità)
- **Cartelle** — naviga `/data/`, aggiungi/rimuovi cartelle da indicizzare

La configurazione viene salvata su un volume Docker persistente — sopravvive ai riavvii.

## Share di rete / NAS

Le share di rete funzionano purché siano montate come cartelle.

**Mac**: le share SMB appaiono in `/Volumes/NomeShare` dal Finder.
Imposta `DOCUMENTS_ROOT=/Volumes/NomeShare` nel `.env`.

**Linux**: monta la share e usa il mountpoint come `DOCUMENTS_ROOT`:
```bash
sudo mount -t cifs //192.168.1.100/documenti /mnt/share -o username=utente
# poi in .env: DOCUMENTS_ROOT=/mnt/share
```

## Costi indicativi (Mistral AI)

| Operazione | Costo |
|---|---|
| Indicizzare 100 documenti (~50 pag.) | ~$0.25 |
| 50 domande/giorno per un mese | ~$3/mese |
| Uso intensivo (500 domande/giorno) | ~$30/mese |

## Comandi utili

```bash
# Avvia
docker compose up -d

# Vedi i log
docker compose logs -f

# Ferma
docker compose down

# Ricostruisci dopo aggiornamento
docker compose up -d --build

# Cancella il database vettoriale
docker volume rm gdprag_gdprag_chroma

# Cancella la configurazione salvata
docker volume rm gdprag_gdprag_config

# Entra nel container
docker exec -it gdprag bash

# CLI dentro il container
docker exec -it gdprag python rag_engine.py --stats
docker exec -it gdprag python rag_engine.py --files
docker exec -it gdprag python rag_engine.py --formats
```

## Senza Docker

```bash
pip install -r requirements.txt
export MISTRAL_API_KEY="la-tua-chiave"
python web_ui.py
# Apri http://localhost:7860
```

## Compliance

- **Mistral AI** (Parigi) — piena giurisdizione GDPR, non soggetto a CLOUD Act USA
- **AI Act Art. 50** — disclaimer di trasparenza incluso nell'interfaccia
- **Documenti originali** — restano sempre in locale, mai caricati sul cloud
- **Dati al cloud** — solo i frammenti rilevanti alla domanda
- **Training** — Mistral non usa i dati API per addestrare i modelli

---

*GDPRag — Sviluppato da Mediaform s.c.r.l.*
