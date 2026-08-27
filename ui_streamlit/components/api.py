"""HTTP-клиент для FastAPI-бэкенда."""

import os

import requests
import streamlit as st

BACKEND_URL = os.getenv("MTR_BACKEND_URL", "http://localhost:8000").rstrip("/")
TIMEOUT = 60


def _headers(use_auth: bool = True) -> dict:
    headers = {"Content-Type": "application/json"}
    if use_auth:
        token = st.session_state.get("token")
        if token:
            headers["Authorization"] = f"Bearer {token}"
    return headers


def _safe(fn, *args, **kwargs):
    try:
        resp = fn(*args, timeout=TIMEOUT, **kwargs)
        return resp
    except requests.exceptions.ConnectionError:
        st.error(f"Не удалось подключиться к бэкенду: {BACKEND_URL}")
        st.stop()
    except requests.exceptions.Timeout:
        st.error("Превышено время ожидания ответа от бэкенда.")
        st.stop()


def login(username: str, password: str):
    
    return _safe(
        requests.post,
        f"{BACKEND_URL}/api/v1/auth/login",
        json={"username": username, "password": password},
        headers=_headers(use_auth=False),
    )
    


def me():
    return _safe(requests.get, f"{BACKEND_URL}/api/v1/auth/me", headers=_headers())


def search(query: str, mode: str = "deterministic", filters: dict = None, top_k: int = 20):
    body = {"query": query, "mode": mode, "top_k": top_k}
    if filters:
        body["filters"] = filters
    return _safe(
        requests.post, f"{BACKEND_URL}/api/v1/search/", json=body, headers=_headers()
    )


def search_history(limit: int = 20):
    return _safe(
        requests.get,
        f"{BACKEND_URL}/api/v1/search/history",
        params={"limit": limit},
        headers=_headers(),
    )


def upload_passport(file_bytes, filename: str):
    return _safe(
        requests.post,
        f"{BACKEND_URL}/api/v1/passport/upload",
        files={"file": (filename, file_bytes, "application/pdf")},
    )


def passport_status(document_id: str):
    return _safe(
        requests.get, f"{BACKEND_URL}/api/v1/passport/status/{document_id}", headers=_headers(use_auth=False)
    )


def passport_extracted(document_id: str):
    return _safe(
        requests.get, f"{BACKEND_URL}/api/v1/passport/extracted/{document_id}", headers=_headers(use_auth=False)
    )


def component(ksm_code: str, detail_level: str = "full"):
    return _safe(
        requests.get,
        f"{BACKEND_URL}/api/v1/component/{ksm_code}",
        params={"detail_level": detail_level},
        headers=_headers(use_auth=False),
    )


def compare(ksm_code_1: str, ksm_code_2: str):
    return _safe(
        requests.post,
        f"{BACKEND_URL}/api/v1/compare/",
        json={"ksm_code_1": ksm_code_1, "ksm_code_2": ksm_code_2},
        headers=_headers(use_auth=False),
    )


def norms_search(query: str, limit: int = 20):
    return _safe(
        requests.post,
        f"{BACKEND_URL}/api/v1/norms/search",
        json={"query": query, "limit": limit},
        headers=_headers(use_auth=False),
    )


def expert_reviews():
    return _safe(requests.get, f"{BACKEND_URL}/api/v1/expert/reviews", headers=_headers())


def expert_review_decision(review_id: int, decision: str, reason: str = None):
    body = {"decision": decision, "reason": reason}
    return _safe(
        requests.post,
        f"{BACKEND_URL}/api/v1/expert/review/{review_id}",
        json=body,
        headers=_headers(),
    )


def expert_pending_passports():
    return _safe(
        requests.get, f"{BACKEND_URL}/api/v1/expert/passports/pending", headers=_headers()
    )


def expert_link_passport(document_id: str, ksm_code: str):
    return _safe(
        requests.post,
        f"{BACKEND_URL}/api/v1/expert/passports/link",
        json={"document_id": document_id, "ksm_code": ksm_code},
        headers=_headers(),
    )


def audit_logs(filters: dict = None, limit: int = 200):
    params = {}
    if filters:
        params = {k: v for k, v in filters.items() if v}
    params["limit"] = limit
    return _safe(requests.get, f"{BACKEND_URL}/api/v1/audit/logs", params=params, headers=_headers())


def admin_dict_get(name: str):
    return _safe(requests.get, f"{BACKEND_URL}/api/v1/admin/dictionaries/{name}", headers=_headers())


def admin_dict_post(name: str, data: dict):
    return _safe(
        requests.post, f"{BACKEND_URL}/api/v1/admin/dictionaries/{name}", json=data, headers=_headers()
    )


def admin_dict_put(name: str, item_id: int, data: dict):
    return _safe(
        requests.put,
        f"{BACKEND_URL}/api/v1/admin/dictionaries/{name}/{item_id}",
        json=data,
        headers=_headers(),
    )


def admin_dict_delete(name: str, item_id: int):
    return _safe(
        requests.delete,
        f"{BACKEND_URL}/api/v1/admin/dictionaries/{name}/{item_id}",
        headers=_headers(),
    )


def admin_dict_reload():
    return _safe(
        requests.post, f"{BACKEND_URL}/api/v1/admin/dictionaries/reload", headers=_headers()
    )
