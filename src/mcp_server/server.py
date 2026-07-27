from __future__ import annotations

from datetime import datetime
from typing import List

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("python-mcp-server")


@mcp.tool()
def ping() -> str:
    """Retorna um status simples para validar se o servidor esta funcionando."""
    return "pong"


@mcp.tool()
def soma(a: float, b: float) -> float:
    """Soma dois numeros."""
    return a + b


@mcp.tool()
def agora() -> str:
    """Retorna data e hora atuais no formato ISO 8601."""
    return datetime.now().isoformat()


@mcp.tool()
def inverter_lista(itens: List[str]) -> List[str]:
    """Retorna uma nova lista com os itens em ordem inversa."""
    return list(reversed(itens))


def run() -> None:
    """Executa o servidor MCP usando transporte stdio."""
    mcp.run()
