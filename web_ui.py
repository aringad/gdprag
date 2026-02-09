#!/usr/bin/env python3
"""
=============================================================
Web UI — Interfaccia Gradio per GDPRag
=============================================================
RAG GDPR-compliant con Mistral AI.
Apri il browser su http://localhost:7860
=============================================================
"""

import os
import gradio as gr
from pathlib import Path
from rag_engine import RAGEngine, RAGConfig, get_supported_formats_status
from config_manager import ConfigManager

# ── Configurazione ──
config_manager = ConfigManager()


def _build_engine() -> RAGEngine:
    """Costruisce il RAGEngine con la config corrente."""
    cfg = RAGConfig(
        api_key=config_manager.get_api_key(),
        chroma_path=os.environ.get("CHROMA_PATH", "./chroma_db"),
        chat_model=config_manager.get_chat_model(),
    )
    return RAGEngine(cfg)


engine = _build_engine()


def _reload_engine():
    """Ricarica il motore con la config aggiornata."""
    global engine
    config_manager.reload()
    engine = _build_engine()


# ── Tab: Chat ────────────────────────────────────────────

def chat_fn(message: str, history: list) -> str:
    if not message.strip():
        return ""

    if not config_manager.has_api_key():
        return ("⚠️ API key non configurata. "
                "Vai nella tab **⚙️ Impostazioni** per inserire la tua API key Mistral.")

    try:
        result = engine.query(message)
        answer = result["answer"]
        sources = set(s["filename"] for s in result["sources"])
        answer += f"\n\n---\n📚 *Fonti: {', '.join(sources)}*"
        return answer

    except Exception as e:
        error_msg = str(e)
        if "collection" in error_msg.lower():
            return ("⚠️ Nessun documento indicizzato. "
                    "Vai alla tab **📥 Gestione Documenti** per caricare i documenti.")
        return f"❌ Errore: {error_msg}"


# ── Tab: Gestione Documenti ──────────────────────────────

def ingest_from_paths(paths_text: str, append: bool,
                      progress=gr.Progress(track_tqdm=True)) -> str:
    if not paths_text.strip():
        return "⚠️ Inserisci almeno un percorso"

    if not config_manager.has_api_key():
        return "⚠️ API key non configurata. Vai nella tab ⚙️ Impostazioni."

    paths = [p.strip() for p in paths_text.strip().splitlines()
             if p.strip() and not p.startswith("#")]

    if not paths:
        return "⚠️ Nessun percorso valido trovato"

    valid_paths = []
    errors = []
    for p in paths:
        expanded = Path(p).expanduser().resolve()
        if expanded.exists():
            valid_paths.append(str(expanded))
        else:
            errors.append(f"❌ Non trovato: {p}")

    if not valid_paths:
        return "❌ Nessun percorso valido.\n" + "\n".join(errors)

    try:
        messages = []
        if errors:
            messages.extend(errors)

        stats = engine.ingest(
            paths=valid_paths,
            append=append,
            progress_callback=lambda step, msg: progress(0.5, desc=msg)
        )

        messages.append(f"\n✅ Ingestione completata!")
        messages.append(f"📄 Documenti processati: {stats['documents']}")
        messages.append(f"✂️ Chunk creati: {stats['chunks']}")
        messages.append(f"💰 Costo stimato: ${stats['cost_est']:.4f}")

        if stats.get("errors"):
            for err in stats["errors"]:
                messages.append(f"⚠️ {err}")

        return "\n".join(messages)

    except Exception as e:
        return f"❌ Errore: {e}"


def ingest_uploaded_files(files, append: bool) -> str:
    if not files:
        return "⚠️ Nessun file selezionato"

    if not config_manager.has_api_key():
        return "⚠️ API key non configurata. Vai nella tab ⚙️ Impostazioni."

    try:
        paths = [f.name for f in files]
        stats = engine.ingest(paths=paths, append=append)
        return (
            f"✅ Indicizzati {stats['documents']} file → "
            f"{stats['chunks']} chunk. "
            f"Costo: ${stats['cost_est']:.4f}"
        )
    except Exception as e:
        return f"❌ Errore: {e}"


def ingest_configured_folders(append: bool,
                              progress=gr.Progress(track_tqdm=True)) -> str:
    """Indicizza tutte le cartelle configurate nelle impostazioni."""
    folders = config_manager.get_all_folder_paths()
    if not folders:
        return "⚠️ Nessuna cartella configurata. Vai nella tab ⚙️ Impostazioni per aggiungere cartelle."

    if not config_manager.has_api_key():
        return "⚠️ API key non configurata. Vai nella tab ⚙️ Impostazioni."

    valid_paths = [p for p in folders if Path(p).exists()]
    if not valid_paths:
        return "❌ Nessuna cartella configurata risulta accessibile."

    try:
        stats = engine.ingest(
            paths=valid_paths,
            append=append,
            progress_callback=lambda step, msg: progress(0.5, desc=msg)
        )
        msg = [
            f"✅ Ingestione completata!",
            f"📁 Cartelle processate: {len(valid_paths)}",
            f"📄 Documenti: {stats['documents']}",
            f"✂️ Chunk: {stats['chunks']}",
            f"💰 Costo: ${stats['cost_est']:.4f}",
        ]
        if stats.get("errors"):
            for err in stats["errors"]:
                msg.append(f"⚠️ {err}")
        return "\n".join(msg)
    except Exception as e:
        return f"❌ Errore: {e}"


def get_stats_fn() -> str:
    stats = engine.get_stats()
    if "error" in stats:
        return f"❌ {stats['error']}\n\nProbabilmente non hai ancora indicizzato documenti."

    files = engine.list_indexed_files()

    lines = [
        f"📊 **Statistiche**\n",
        f"- Chunk indicizzati: **{stats['total_chunks']}**",
        f"- Dimensione DB: **{stats['db_size_mb']} MB**",
        f"- File indicizzati: **{len(files)}**\n",
    ]

    if files:
        lines.append("📁 **File:**")
        for f in files:
            lines.append(f"  - 📄 {f}")

    return "\n".join(lines)


def clear_fn() -> str:
    engine.clear()
    return "✅ Tutti i documenti sono stati rimossi dall'indice."


def get_formats_fn() -> str:
    lines = ["📋 **Formati supportati:**\n"]
    for fmt, (status, note) in get_supported_formats_status().items():
        lines.append(f"  {status} **{fmt}** — {note}")
    return "\n".join(lines)


# ── Tab: Impostazioni ───────────────────────────────────

def save_api_key(key: str) -> str:
    if not key.strip():
        return "⚠️ Inserisci una API key valida"

    config_manager.set_api_key(key)
    _reload_engine()

    # Test connessione
    try:
        from mistralai import Mistral
        client = Mistral(api_key=key.strip())
        client.models.list()
        return "✅ API key salvata e verificata! Connessione a Mistral riuscita."
    except Exception as e:
        return f"⚠️ API key salvata, ma la verifica ha fallito: {e}"


def get_api_key_status() -> str:
    if config_manager.has_api_key():
        key = config_manager.get_api_key()
        masked = key[:4] + "•" * (len(key) - 8) + key[-4:] if len(key) > 8 else "•" * len(key)
        source = "configurazione" if config_manager._config.get("api_key") else "variabile d'ambiente"
        return f"✅ Configurata ({masked}) — fonte: {source}"
    return "❌ Non configurata"


def save_model(model: str) -> str:
    config_manager.set_chat_model(model)
    _reload_engine()
    return f"✅ Modello aggiornato: {model}"


def get_current_model() -> str:
    return config_manager.get_chat_model()


def browse_data_dir(path: str) -> str:
    """Naviga le cartelle disponibili in /data."""
    if not path.strip():
        path = "/data"

    folders = config_manager.browse_directory(path)
    if not folders:
        p = Path(path)
        if not p.exists():
            return f"❌ Percorso non trovato: {path}"
        return f"📁 **{path}** — nessuna sottocartella trovata"

    lines = [f"📁 **Contenuto di {path}:**\n"]
    for f in folders:
        lines.append(f"  📂 `{f['path']}` — {f['file_count']} file supportati")
    lines.append(f"\n*Copia il percorso desiderato e usa \"Aggiungi cartella\" qui sotto.*")
    return "\n".join(lines)


def add_folder_fn(path: str, label: str) -> tuple[str, str]:
    result = config_manager.add_folder(path, label)
    return result, _get_folders_list()


def remove_folder_fn(path: str) -> tuple[str, str]:
    result = config_manager.remove_folder(path)
    return result, _get_folders_list()


def _get_folders_list() -> str:
    folders = config_manager.get_folders()
    if not folders:
        return "Nessuna cartella configurata. Usa il browser qui sopra per trovare e aggiungere cartelle."

    lines = ["📁 **Cartelle configurate:**\n"]
    for f in folders:
        count = config_manager.count_files_in_path(f.path)
        exists = "✅" if Path(f.path).exists() else "❌"
        lines.append(f"  {exists} **{f.label}** — `{f.path}` ({count} file)")
    return "\n".join(lines)


# ── Costruzione UI ───────────────────────────────────────

def build_ui() -> gr.Blocks:

    with gr.Blocks(
        title="GDPRag",
        theme=gr.themes.Soft(),
        css="""
        .disclaimer {
            background-color: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 8px;
            padding: 12px;
            margin: 10px 0;
            font-size: 0.9em;
        }
        .gdprag-header {
            text-align: center;
            padding: 10px 0;
        }
        """
    ) as app:

        gr.Markdown("""
        # 🛡️ GDPRag — RAG GDPR-Compliant

        Chatta con i tuoi documenti usando intelligenza artificiale **europea**.
        I documenti restano sul tuo sistema. Solo i frammenti rilevanti vengono inviati
        a Mistral AI (Parigi, Francia) per generare le risposte.
        """)

        gr.HTML("""
        <div class="disclaimer">
        ⚠️ <strong>AI Act Art. 50 — Trasparenza:</strong> Le risposte sono generate
        da un sistema di intelligenza artificiale (Mistral AI, Parigi — giurisdizione GDPR).
        Verificare sempre le informazioni critiche sui documenti originali.
        </div>
        """)

        with gr.Tabs():

            # ── Tab Chat ──
            with gr.TabItem("💬 Chat"):
                chatbot = gr.ChatInterface(
                    fn=chat_fn,
                    title="",
                    description="Fai domande sui documenti aziendali indicizzati.",
                    examples=[
                        "Quali documenti sono disponibili?",
                        "Riassumi le procedure di sicurezza",
                        "Cosa dice la policy sulla gestione degli incidenti?",
                        "Quali sono le scadenze NIS2?",
                    ],
                )

            # ── Tab Gestione Documenti ──
            with gr.TabItem("📥 Gestione Documenti"):
                gr.Markdown("### Indicizza documenti")

                with gr.Tabs():
                    # Metodo 1: Cartelle configurate
                    with gr.TabItem("📁 Cartelle configurate"):
                        gr.Markdown("""
                        Indicizza tutte le cartelle che hai configurato nella tab **⚙️ Impostazioni**.
                        """)
                        append_configured = gr.Checkbox(
                            label="Aggiungi ai documenti esistenti (non cancellare i precedenti)",
                            value=False
                        )
                        ingest_configured_btn = gr.Button(
                            "🚀 Indicizza cartelle configurate", variant="primary"
                        )
                        ingest_configured_output = gr.Textbox(label="Risultato", lines=8)
                        ingest_configured_btn.click(
                            ingest_configured_folders,
                            inputs=[append_configured],
                            outputs=ingest_configured_output
                        )

                    # Metodo 2: Percorsi manuali
                    with gr.TabItem("✏️ Percorsi manuali"):
                        gr.Markdown("""
                        Inserisci i percorsi delle cartelle o dei file, uno per riga.
                        Le cartelle vengono scansionate ricorsivamente.
                        """)
                        paths_input = gr.Textbox(
                            label="Percorsi",
                            lines=6,
                            placeholder="/data/documenti\n/data/procedure\n/data/manuali"
                        )
                        append_check = gr.Checkbox(
                            label="Aggiungi ai documenti esistenti",
                            value=False
                        )
                        ingest_btn = gr.Button("🚀 Indicizza", variant="primary")
                        ingest_output = gr.Textbox(label="Risultato", lines=8)
                        ingest_btn.click(
                            ingest_from_paths,
                            inputs=[paths_input, append_check],
                            outputs=ingest_output
                        )

                    # Metodo 3: Upload
                    with gr.TabItem("📤 Upload file"):
                        gr.Markdown("Carica file direttamente dal browser (utile per test).")
                        upload_files = gr.File(
                            label="Seleziona file",
                            file_count="multiple",
                            type="filepath"
                        )
                        append_check_upload = gr.Checkbox(
                            label="Aggiungi ai documenti esistenti",
                            value=False
                        )
                        upload_btn = gr.Button("🚀 Indicizza file caricati", variant="primary")
                        upload_output = gr.Textbox(label="Risultato", lines=5)
                        upload_btn.click(
                            ingest_uploaded_files,
                            inputs=[upload_files, append_check_upload],
                            outputs=upload_output
                        )

                gr.Markdown("---")
                gr.Markdown("### Gestione indice")

                with gr.Row():
                    stats_btn = gr.Button("📊 Statistiche")
                    formats_btn = gr.Button("📋 Formati supportati")
                    clear_btn = gr.Button("🗑️ Cancella tutto", variant="stop")

                info_output = gr.Markdown()
                stats_btn.click(get_stats_fn, outputs=info_output)
                formats_btn.click(get_formats_fn, outputs=info_output)
                clear_btn.click(clear_fn, outputs=info_output)

            # ── Tab Impostazioni ──
            with gr.TabItem("⚙️ Impostazioni"):

                # ── API Key ──
                gr.Markdown("### 🔑 API Key Mistral")
                api_status = gr.Markdown(value=get_api_key_status())
                with gr.Row():
                    api_key_input = gr.Textbox(
                        label="API Key",
                        type="password",
                        placeholder="Inserisci la tua API key Mistral",
                        scale=3
                    )
                    save_key_btn = gr.Button("💾 Salva e verifica", scale=1)
                api_key_result = gr.Markdown()
                save_key_btn.click(
                    save_api_key,
                    inputs=[api_key_input],
                    outputs=[api_key_result]
                ).then(
                    get_api_key_status,
                    outputs=[api_status]
                )

                gr.Markdown("---")

                # ── Modello ──
                gr.Markdown("### 🤖 Modello AI")
                model_dropdown = gr.Dropdown(
                    choices=[
                        ("Mistral Small (veloce, economico)", "mistral-small-latest"),
                        ("Mistral Medium (bilanciato)", "mistral-medium-latest"),
                        ("Mistral Large (massima qualita')", "mistral-large-latest"),
                    ],
                    value=get_current_model(),
                    label="Modello per le risposte"
                )
                save_model_btn = gr.Button("💾 Salva modello")
                model_result = gr.Markdown()
                save_model_btn.click(
                    save_model,
                    inputs=[model_dropdown],
                    outputs=[model_result]
                )

                gr.Markdown("---")

                # ── Gestione Cartelle ──
                gr.Markdown("### 📂 Gestione Cartelle")
                gr.Markdown("""
                Naviga i volumi montati e configura le cartelle da indicizzare.
                Le cartelle qui configurate saranno disponibili nella tab **📥 Gestione Documenti**.
                """)

                with gr.Row():
                    browse_path = gr.Textbox(
                        label="Percorso da esplorare",
                        value="/data",
                        placeholder="/data",
                        scale=3
                    )
                    browse_btn = gr.Button("🔍 Esplora", scale=1)
                browse_output = gr.Markdown()
                browse_btn.click(
                    browse_data_dir,
                    inputs=[browse_path],
                    outputs=[browse_output]
                )

                gr.Markdown("#### Aggiungi cartella")
                with gr.Row():
                    folder_path_input = gr.Textbox(
                        label="Percorso cartella",
                        placeholder="/data/documenti",
                        scale=2
                    )
                    folder_label_input = gr.Textbox(
                        label="Nome (opzionale)",
                        placeholder="Documenti aziendali",
                        scale=1
                    )
                    add_folder_btn = gr.Button("➕ Aggiungi", scale=1)

                folder_action_result = gr.Markdown()
                folders_list = gr.Markdown(value=_get_folders_list())
                add_folder_btn.click(
                    add_folder_fn,
                    inputs=[folder_path_input, folder_label_input],
                    outputs=[folder_action_result, folders_list]
                )

                gr.Markdown("#### Rimuovi cartella")
                with gr.Row():
                    remove_path_input = gr.Textbox(
                        label="Percorso da rimuovere",
                        placeholder="/data/documenti",
                        scale=3
                    )
                    remove_folder_btn = gr.Button("🗑️ Rimuovi", variant="stop", scale=1)
                remove_folder_btn.click(
                    remove_folder_fn,
                    inputs=[remove_path_input],
                    outputs=[folder_action_result, folders_list]
                )

            # ── Tab Info ──
            with gr.TabItem("ℹ️ Info"):
                gr.Markdown("""
                ### 🛡️ Perche' GDPRag?

                **GDPRag** = GDPR + RAG. Un sistema di Retrieval-Augmented Generation
                progettato per la compliance europea:

                - **Mistral AI** ha sede a **Parigi, Francia** — piena giurisdizione GDPR
                - **CLOUD Act USA**: NON applicabile (azienda francese)
                - I tuoi documenti **restano sempre in locale**
                - Solo i frammenti rilevanti vengono inviati al cloud EU
                - Mistral **non usa i dati API per training**

                ### Architettura

                ```
                I tuoi documenti (PDF, DOCX, XLSX, PPTX, TXT, ...)
                  │
                  ▼
                Estrazione testo + chunking (locale, sul tuo sistema)
                  │
                  ▼
                Mistral Embed API → vettori numerici (cloud EU, $0.10/M token)
                  │
                  ▼
                ChromaDB locale → database vettoriale su disco
                  │
                  ▼ (quando fai una domanda)
                Ricerca similarita' (locale, istantaneo)
                  │
                  ▼
                Solo i 5 frammenti piu' rilevanti → Mistral Chat API (cloud EU)
                  │
                  ▼
                Risposta
                ```

                ### Costi indicativi

                | Operazione | Costo |
                |---|---|
                | Indicizzare 100 documenti (50 pag.) | ~$0.25 |
                | 50 domande/giorno per un mese | ~$3/mese |
                | Uso intensivo (500 domande/giorno) | ~$30/mese |

                ---

                *GDPRag — Sviluppato da Mediaform s.c.r.l.*
                """)

    return app


# ── Main ─────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    host = os.environ.get("HOST", "0.0.0.0")

    app = build_ui()
    app.launch(
        server_name=host,
        server_port=port,
        share=False,
        show_error=True
    )
