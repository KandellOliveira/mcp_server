# Servidor MCP em Python

Projeto base de um servidor MCP (Model Context Protocol) em Python, pronto para conectar em clientes MCP.

## Requisitos

- Python 3.10+

## Instalar

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Executar

```bash
mcp-server-python
```

O servidor sobe em modo `stdio`, que e o formato mais comum para integrar com clientes MCP locais.

## Tools disponiveis

- `ping() -> str`
- `soma(a: float, b: float) -> float`
- `agora() -> str`
- `inverter_lista(itens: list[str]) -> list[str]`

## Estrutura

- `src/mcp_server/server.py`: definicao do servidor e tools.
- `src/mcp_server/__main__.py`: ponto de entrada para execucao.
- `pyproject.toml`: metadados, dependencias e script CLI.
