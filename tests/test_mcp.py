import asyncio
import os
import sys

import pytest
from mcp import Client, StdioServerParameters

from tests.test_review import database, new_case  # noqa: F401

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="Real PostgreSQL required")


def test_real_stdio_transport_exposes_only_restricted_tools():
    case_id = new_case()

    async def scenario():
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "workbench.mcp_server"],
            env={**os.environ, "MCP_PRINCIPAL_ID": "ana"},
        )
        async with Client(params) as client:
            result = await client.list_tools()
            assert {tool.name for tool in result.tools} == {
                "get_case",
                "get_order",
                "get_payment_status",
                "propose_resolution",
                "execute_approved_resolution",
            }
            for tool in result.tools:
                assert "organization" not in tool.input_schema.get("properties", {})
                assert "principal_id" not in tool.input_schema.get("properties", {})
            assert not (await client.call_tool("get_case", {"case_id": case_id})).is_error
            assert (
                await client.call_tool("execute_approved_resolution", {"case_id": case_id})
            ).is_error
            assert (await client.call_tool("delete_database", {})).is_error
            assert (await client.call_tool("get_case", {"case_id": "invalid"})).is_error

    asyncio.run(scenario())


def test_stdio_server_identity_rejects_cross_tenant():
    case_id = new_case()

    async def scenario():
        async with Client(
            StdioServerParameters(
                command=sys.executable,
                args=["-m", "workbench.mcp_server"],
                env={**os.environ, "MCP_PRINCIPAL_ID": "cedro"},
            )
        ) as client:
            assert (await client.call_tool("get_case", {"case_id": case_id})).is_error

    asyncio.run(scenario())
