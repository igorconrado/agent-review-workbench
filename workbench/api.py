import hashlib
import json
import logging
import os
import time
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from workbench.execution import SyntheticSandbox, execute_approved
from workbench.graph import run_graph
from workbench.identity import identify, login
from workbench.policy import Action, Evidence
from workbench.review import (
    Conflict,
    Forbidden,
    cancel,
    create_case,
    decide,
    edit_proposal,
    replace_evidence,
)
from workbench.store import connection

app = FastAPI(title="Agent Review Workbench", version="0.1.0")
logger = logging.getLogger("workbench")


@app.middleware("http")
async def boundary(request: Request, call_next: Any) -> Response:
    started = time.perf_counter()
    correlation = str(uuid4())
    if request.method != "GET" and request.headers.get("origin") != os.getenv(
        "APP_ORIGIN", "http://127.0.0.1:3200"
    ):
        return JSONResponse({"detail": "Origin rejected"}, status_code=403)
    response: Response = await call_next(request)
    response.headers["x-request-id"] = correlation
    logger.info(
        json.dumps(
            {
                "request_id": correlation,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            }
        )
    )
    return response


@app.exception_handler(Forbidden)
async def forbidden_handler(request: Request, error: Forbidden) -> JSONResponse:
    return JSONResponse({"detail": str(error)}, status_code=403)


@app.exception_handler(Conflict)
async def conflict_handler(request: Request, error: Conflict) -> JSONResponse:
    return JSONResponse({"detail": str(error)}, status_code=409)


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    principal_id: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class Decision(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    action_hash: str = Field(pattern="^[a-f0-9]{64}$")
    approve: bool


class ProposalEdit(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    action_hash: str = Field(pattern="^[a-f0-9]{64}$")
    action: Action


def actor(request: Request) -> str:
    return identify(request.cookies.get("workbench_session", ""))


@app.get("/api/health")
def health() -> dict[str, str]:
    with connection() as conn:
        conn.execute("SELECT 1")
    return {"status": "ok"}


@app.post("/api/session")
def sign_in(credentials: Credentials, response: Response) -> dict[str, str]:
    token = login(credentials.principal_id, credentials.password)
    response.set_cookie(
        "workbench_session",
        token,
        httponly=True,
        samesite="strict",
        secure=os.getenv("COOKIE_SECURE") == "true",
        max_age=28800,
    )
    return {"principal_id": credentials.principal_id}


@app.delete("/api/session")
def sign_out(request: Request, response: Response) -> dict[str, bool]:
    with connection() as conn:
        conn.execute(
            "DELETE FROM sessions WHERE token_hash=%s",
            (hashlib.sha256(request.cookies.get("workbench_session", "").encode()).hexdigest(),),
        )
    response.delete_cookie("workbench_session")
    return {"ok": True}


@app.get("/api/cases")
def list_cases(request: Request) -> dict[str, Any]:
    principal_id = actor(request)
    with connection() as conn:
        principal = conn.execute("SELECT * FROM principals WHERE id=%s", (principal_id,)).fetchone()
        assert principal
        cases = conn.execute(
            "SELECT cases.*, EXISTS(SELECT 1 FROM tool_calls WHERE case_id=cases.id "
            "AND state='unknown') AS reconciliation_required FROM cases "
            "WHERE organization=%s ORDER BY created_at DESC LIMIT 50",
            (principal["organization"],),
        ).fetchall()
        return {"principal_id": principal_id, "role": principal["role"], "cases": cases}


@app.post("/api/cases", status_code=201)
def new_case(request: Request, evidence: Evidence) -> dict[str, str]:
    return {"case_id": create_case(actor(request), evidence)}


@app.post("/api/cases/{case_id}/propose")
def start(request: Request, case_id: str) -> dict[str, Any]:
    state = run_graph(actor(request), case_id)
    return dict(state["proposal"])


@app.post("/api/cases/{case_id}/decision")
def decision(request: Request, case_id: str, body: Decision) -> dict[str, bool]:
    decide(actor(request), case_id, body.action_hash, body.approve)
    return {"ok": True}


@app.post("/api/cases/{case_id}/execute")
def execute(request: Request, case_id: str) -> dict[str, Any]:
    return dict(run_graph(actor(request), case_id, resume=True)["result"])


@app.post("/api/cases/{case_id}/edit")
def edit(request: Request, case_id: str, body: ProposalEdit) -> dict[str, str]:
    return {"action_hash": edit_proposal(actor(request), case_id, body.action_hash, body.action)}


@app.post("/api/cases/{case_id}/reconcile")
def reconcile(request: Request, case_id: str) -> dict[str, Any]:
    return execute_approved(actor(request), case_id, SyntheticSandbox(), cancelled_only=True)


@app.post("/api/cases/{case_id}/cancel")
def cancellation(request: Request, case_id: str) -> dict[str, Any]:
    return cancel(actor(request), case_id)


@app.put("/api/cases/{case_id}/evidence")
def update_evidence(request: Request, case_id: str, evidence: Evidence) -> dict[str, bool]:
    replace_evidence(actor(request), case_id, evidence)
    return {"ok": True}
