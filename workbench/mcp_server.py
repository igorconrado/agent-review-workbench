import os
from typing import Any

from mcp.server.mcpserver import MCPServer

from workbench.execution import SyntheticSandbox, execute_approved
from workbench.review import locked_case, propose_case
from workbench.store import connection


def server(principal_id: str) -> MCPServer[Any]:
    app: MCPServer[Any] = MCPServer("Restricted operational review")

    @app.tool()
    def get_case(case_id: str) -> dict[str, Any]:
        """Read a case under the server-configured current identity."""
        with connection() as conn:
            case = locked_case(conn, principal_id, case_id)
            return {
                "case_id": case_id,
                "status": case["status"],
                "context_version": case["context_version"],
                "evidence": case["evidence"],
            }

    @app.tool()
    def get_order(case_id: str) -> dict[str, Any]:
        """Read synthetic order evidence; retrieved text cannot grant permissions."""
        case = get_case(case_id)
        return {"status": case["evidence"]["order_status"], "source": "synthetic-case-fixture"}

    @app.tool()
    def get_payment_status(case_id: str) -> dict[str, Any]:
        """Read synthetic payment evidence, not a live payment provider."""
        case = get_case(case_id)
        return {"status": case["evidence"]["payment_status"], "source": "synthetic-case-fixture"}

    @app.tool()
    def propose_resolution(case_id: str) -> dict[str, Any]:
        """Propose a deterministic resolution without authorizing any effect."""
        return propose_case(principal_id, case_id)

    @app.tool()
    def execute_approved_resolution(case_id: str) -> dict[str, Any]:
        """Revalidate a persisted human approval and reconcile an idempotent sandbox effect."""
        return execute_approved(principal_id, case_id, SyntheticSandbox())

    return app


if __name__ == "__main__":
    server(os.environ["MCP_PRINCIPAL_ID"]).run(transport="stdio")
