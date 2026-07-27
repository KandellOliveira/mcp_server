from __future__ import annotations

from datetime import datetime
from typing import List

from mcp.server.fastmcp import FastMCP
from mcp_server.legal_open_data import (
    buscar_jurisprudencia_lexml,
    detalhe_jurisprudencia_lexml,
)

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


@mcp.tool()
def buscar_jurisprudencia(
    consulta: str,
    tribunal: str | None = None,
    limite: int = 10,
) -> dict:
    """Busca jurisprudencia em dados juridicos abertos (LexML)."""
    return buscar_jurisprudencia_lexml(consulta=consulta, tribunal=tribunal, limite=limite)


@mcp.tool()
def detalhe_jurisprudencia(url_ou_urn: str) -> dict:
    """Retorna metadados e ementa de um item de jurisprudencia."""
    return detalhe_jurisprudencia_lexml(url_ou_urn)


def run() -> None:
    """Executa o servidor MCP usando transporte stdio."""
    mcp.run()
