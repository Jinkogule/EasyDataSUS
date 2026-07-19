import os
import re
import socket
from typing import Dict, Iterable

import requests

from config.datasets import DATASETS_CONFIG
from db.clickhouse import get_client
from llm.router import get_model_identifier


WRITE_PRIVILEGES = {
    "INSERT",
    "ALTER",
    "CREATE",
    "DROP",
    "TRUNCATE",
    "OPTIMIZE",
    "SYSTEM",
    "ALL",
}


def _contains_write_privilege(grants: Iterable[str]) -> bool:
    for grant in grants:
        match = re.search(r"\bGRANT\s+(.+?)\s+ON\b", grant.upper())
        if not match:
            continue
        privilege_clause = match.group(1)
        if any(re.search(rf"\b{re.escape(privilege)}\b", privilege_clause) for privilege in WRITE_PRIVILEGES):
            return True
    return False


def check_runtime_readiness(model_alias: str = "deepseek-local") -> Dict[str, object]:
    """Verifica dependências necessárias antes de uma execução experimental."""
    checks: Dict[str, object] = {}

    configured_model = get_model_identifier(model_alias)
    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    try:
        response = requests.get(f"{ollama_host}/api/tags", timeout=5)
        response.raise_for_status()
        models = response.json().get("models", [])
        model_by_name = {model.get("name"): model for model in models if model.get("name")}
        model_info = model_by_name.get(configured_model)
        checks["ollama"] = {
            "ready": model_info is not None,
            "configured_model": configured_model,
            "available_models": sorted(model_by_name),
            "model_digest": model_info.get("digest") if model_info else None,
        }
    except Exception as exc:
        checks["ollama"] = {
            "ready": False,
            "configured_model": configured_model,
            "error": str(exc),
        }

    expected_tables = sorted(config["table_name"] for config in DATASETS_CONFIG.values())
    try:
        clickhouse_host = os.getenv("CLICKHOUSE_HOST", "localhost")
        clickhouse_port = int(os.getenv("CLICKHOUSE_PORT", "8123"))
        with socket.create_connection((clickhouse_host, clickhouse_port), timeout=1):
            pass
        client = get_client()
        placeholders = ", ".join(f"'{table}'" for table in expected_tables)
        table_rows = client.query(
            "SELECT name FROM system.tables "
            f"WHERE database = currentDatabase() AND name IN ({placeholders})"
        ).result_rows
        available_tables = sorted(row[0] for row in table_rows)
        current_user = client.query("SELECT currentUser()").result_rows[0][0]
        grant_rows = client.query("SHOW GRANTS").result_rows
        grants = [str(row[0]) for row in grant_rows]
        missing_tables = sorted(set(expected_tables) - set(available_tables))
        read_only = not _contains_write_privilege(grants)
        checks["clickhouse"] = {
            "ready": not missing_tables and read_only,
            "current_user": current_user,
            "read_only": read_only,
            "expected_tables": expected_tables,
            "available_tables": available_tables,
            "missing_tables": missing_tables,
            "grants": grants,
        }
    except Exception as exc:
        checks["clickhouse"] = {
            "ready": False,
            "expected_tables": expected_tables,
            "error": str(exc),
        }

    return {
        "ready": all(bool(check.get("ready")) for check in checks.values()),
        "checks": checks,
    }
