#!/usr/bin/env python3
"""
=============================================================
Config Manager — Configurazione persistente per GDPRag
=============================================================
Gestisce il file config.json su volume Docker persistente.
Permette di configurare API key, cartelle e modello dalla UI.
=============================================================
"""

import os
import json
import logging
import fcntl
from pathlib import Path
from dataclasses import dataclass, field

log = logging.getLogger("gdprag.config")

DEFAULT_CONFIG_DIR = "/app/config"
CONFIG_FILENAME = "config.json"


@dataclass
class FolderConfig:
    path: str
    label: str = ""

    def to_dict(self) -> dict:
        return {"path": self.path, "label": self.label or Path(self.path).name}

    @classmethod
    def from_dict(cls, d: dict) -> "FolderConfig":
        return cls(path=d["path"], label=d.get("label", ""))


class ConfigManager:
    """Gestisce la configurazione persistente di GDPRag."""

    def __init__(self, config_dir: str = None):
        self.config_dir = Path(config_dir or os.environ.get(
            "GDPRAG_CONFIG_DIR", DEFAULT_CONFIG_DIR
        ))
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_path = self.config_dir / CONFIG_FILENAME
        self._config = self._load()

    def _default_config(self) -> dict:
        return {
            "api_key": "",
            "chat_model": "mistral-small-latest",
            "folders": [],
        }

    def _load(self) -> dict:
        if not self.config_path.exists():
            return self._default_config()
        try:
            with open(self.config_path, "r") as f:
                fcntl.flock(f, fcntl.LOCK_SH)
                data = json.load(f)
                fcntl.flock(f, fcntl.LOCK_UN)
            merged = self._default_config()
            merged.update(data)
            return merged
        except Exception as e:
            log.error(f"Errore caricamento config: {e}")
            return self._default_config()

    def _save(self):
        try:
            tmp_path = self.config_path.with_suffix(".tmp")
            with open(tmp_path, "w") as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                json.dump(self._config, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
                fcntl.flock(f, fcntl.LOCK_UN)
            tmp_path.replace(self.config_path)
            log.info("Configurazione salvata")
        except Exception as e:
            log.error(f"Errore salvataggio config: {e}")
            raise

    def reload(self):
        self._config = self._load()

    # ── API Key ──

    def get_api_key(self) -> str:
        """Ritorna la API key. Priorità: config salvata > env var."""
        saved = self._config.get("api_key", "")
        if saved:
            return saved
        return os.environ.get("MISTRAL_API_KEY", "")

    def set_api_key(self, key: str):
        self._config["api_key"] = key.strip()
        self._save()

    def has_api_key(self) -> bool:
        return bool(self.get_api_key())

    # ── Modello ──

    def get_chat_model(self) -> str:
        saved = self._config.get("chat_model", "")
        if saved:
            return saved
        return os.environ.get("CHAT_MODEL", "mistral-small-latest")

    def set_chat_model(self, model: str):
        self._config["chat_model"] = model
        self._save()

    # ── Cartelle ──

    def get_folders(self) -> list[FolderConfig]:
        return [FolderConfig.from_dict(f) for f in self._config.get("folders", [])]

    def add_folder(self, path: str, label: str = "") -> str:
        """Aggiunge una cartella. Ritorna messaggio di stato."""
        path = path.strip()
        if not path:
            return "Percorso vuoto"

        p = Path(path)
        if not p.exists():
            return f"Percorso non trovato: {path}"
        if not p.is_dir():
            return f"Non e' una cartella: {path}"

        # Controlla duplicati
        for f in self._config.get("folders", []):
            if f["path"] == path:
                return f"Cartella gia' configurata: {path}"

        folder = FolderConfig(path=path, label=label or p.name)
        self._config.setdefault("folders", []).append(folder.to_dict())
        self._save()
        return f"Cartella aggiunta: {path}"

    def remove_folder(self, path: str) -> str:
        """Rimuove una cartella dalla configurazione."""
        folders = self._config.get("folders", [])
        self._config["folders"] = [f for f in folders if f["path"] != path]
        self._save()
        return f"Cartella rimossa: {path}"

    def get_all_folder_paths(self) -> list[str]:
        """Ritorna tutti i path delle cartelle configurate."""
        return [f.path for f in self.get_folders()]

    # ── Browse filesystem ──

    @staticmethod
    def browse_directory(base_path: str = "/data") -> list[dict]:
        """Elenca le sottocartelle di un percorso per il file browser."""
        base = Path(base_path)
        if not base.exists() or not base.is_dir():
            return []

        result = []
        try:
            for item in sorted(base.iterdir()):
                if item.name.startswith("."):
                    continue
                if item.is_dir():
                    # Conta file supportati
                    from rag_engine import SUPPORTED_EXTENSIONS
                    file_count = sum(
                        1 for f in item.rglob("*")
                        if f.is_file()
                        and f.suffix.lower() in SUPPORTED_EXTENSIONS
                        and not f.name.startswith(".")
                    )
                    result.append({
                        "name": item.name,
                        "path": str(item),
                        "file_count": file_count,
                    })
        except PermissionError:
            pass

        return result

    @staticmethod
    def count_files_in_path(path: str) -> int:
        """Conta i file supportati in un percorso."""
        p = Path(path)
        if not p.exists():
            return 0
        from rag_engine import SUPPORTED_EXTENSIONS
        return sum(
            1 for f in p.rglob("*")
            if f.is_file()
            and f.suffix.lower() in SUPPORTED_EXTENSIONS
            and not f.name.startswith(".")
        )
