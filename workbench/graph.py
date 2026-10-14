from typing import Any, TypedDict

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from workbench.execution import SyntheticSandbox, execute_approved
from workbench.review import Conflict, locked_case, propose_case
from workbench.store import connection, database_url


class ReviewState(TypedDict, total=False):
    case_id: str
    proposal: dict[str, Any]
    result: dict[str, Any]


def run_graph(principal_id: str, case_id: str, resume: bool = False) -> dict[str, Any]:
    # Authorize before reading any checkpoint; identity is a trusted server argument,
    # never an editable graph state field or model-supplied tool parameter.
    with connection() as conn:
        current = locked_case(conn, principal_id, case_id)
        if resume and current["status"] not in {"approved", "uncertain", "executed"}:
            raise Conflict("No approved workflow is available to resume")

    def proposal(state: ReviewState) -> dict[str, Any]:
        return {"proposal": propose_case(principal_id, state["case_id"])}

    def review(state: ReviewState) -> dict[str, Any]:
        interrupt({"requires_human_review": True, **state["proposal"]})
        with connection() as conn:
            case = locked_case(conn, principal_id, state["case_id"])
            if case["status"] not in {"approved", "uncertain", "executed"}:
                raise Conflict("Resuming a checkpoint does not grant approval")
        return {}

    def execution(state: ReviewState) -> dict[str, Any]:
        return {"result": execute_approved(principal_id, state["case_id"], SyntheticSandbox())}

    with PostgresSaver.from_conn_string(database_url()) as saver:
        saver.setup()
        builder = StateGraph(ReviewState)
        builder.add_node("propose", proposal)
        builder.add_node("human_review", review)
        builder.add_node("execute", execution)
        builder.add_edge(START, "propose")
        builder.add_edge("propose", "human_review")
        builder.add_edge("human_review", "execute")
        builder.add_edge("execute", END)
        graph = builder.compile(checkpointer=saver)
        result = graph.invoke(
            Command(resume=True) if resume else {"case_id": case_id},
            {"configurable": {"thread_id": case_id}, "recursion_limit": 8},
        )
        return dict(result)
