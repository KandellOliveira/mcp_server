# Servidor MCP em Python

Projeto base de um servidor MCP (Model Context Protocol) em Python, pronto para conectar em clientes MCP.

## Requisitos

- Python 3.10+

## Instalar

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Executar

```bash
mcp-server-python
```

O servidor sobe em modo `stdio`, que e o formato mais comum para integrar com clientes MCP locais.

## Configurar cliente MCP

### VS Code

1. Copie `examples/vscode.mcp.example.json` para `.vscode/mcp.json`.
2. Se necessario, ajuste `command` para o Python da sua venv.
3. Reinicie o cliente MCP no VS Code.

Exemplo:

```json
{
	"servers": {
		"python-mcp-server": {
			"type": "stdio",
			"command": "${workspaceFolder}/.venv/bin/python",
			"args": ["-m", "mcp_server"]
		}
	}
}
```

### Claude Desktop

1. Abra o arquivo de configuracao do Claude Desktop.
2. Copie o conteudo de `examples/claude_desktop_config.example.json`.
3. Troque `/CAMINHO/ABSOLUTO/PARA/...` pelo caminho real do projeto.

Exemplo:

```json
{
	"mcpServers": {
		"python-mcp-server": {
			"command": "/CAMINHO/ABSOLUTO/PARA/mcp_server/.venv/bin/python",
			"args": ["-m", "mcp_server"]
		}
	}
}
```

## Tools disponiveis

- `ping() -> str`
- `soma(a: float, b: float) -> float`
- `agora() -> str`
- `inverter_lista(itens: list[str]) -> list[str]`
- `buscar_jurisprudencia(consulta: str, tribunal: str | None = None, limite: int = 10) -> dict`
- `detalhe_jurisprudencia(url_ou_urn: str) -> dict`

## Jurisprudencia com dados abertos

O servidor inclui um modulo para consulta de jurisprudencia em fonte aberta via LexML Brasil.

### Fluxo recomendado

1. Use `buscar_jurisprudencia` com termos como `icms creditamento`, `dano moral consumidor`, `prisao preventiva`.
2. Pegue a `url` ou `urn` de um resultado.
3. Use `detalhe_jurisprudencia` para obter metadados e ementa.

Exemplos de parametros:

- `buscar_jurisprudencia(consulta="icms energia", tribunal="stj", limite=5)`
- `detalhe_jurisprudencia(url_ou_urn="urn:lex:br:superior.tribunal.justica;turma.1:acordao;resp:2006-03-09;601056-676848")`

## Estrutura

- `src/mcp_server/server.py`: definicao do servidor e tools.
- `src/mcp_server/legal_open_data.py`: integracao com dados juridicos abertos.
- `src/mcp_server/__main__.py`: ponto de entrada para execucao.
- `pyproject.toml`: metadados, dependencias e script CLI.
