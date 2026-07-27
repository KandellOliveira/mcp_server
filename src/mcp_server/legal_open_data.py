from __future__ import annotations

from html import unescape
from typing import Any
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
import unicodedata
import re

LEXML_BASE_URL = "https://www.lexml.gov.br"
LEXML_SEARCH_PATH = "/busca/search"
DEFAULT_TIMEOUT_SECONDS = 20
TRIBUNAL_HINTS = {
    "stj": ["superior.tribunal.justica"],
    "stf": ["supremo.tribunal.federal"],
    "tst": ["tribunal.superior.trabalho"],
    "tjdft": ["tribunal.justica.distrito.federal.territorios"],
    "carf": ["conselho.administrativo.recursos.fiscais", "carf"],
}


def _clean_text(value: str) -> str:
    no_tags = re.sub(r"<[^>]+>", " ", value)
    normalized = re.sub(r"\s+", " ", unescape(no_tags))
    return normalized.strip()


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.lower())
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def _fetch_text(url: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> str:
    req = Request(
        url,
        headers={
            "User-Agent": "mcp-server-python/0.1 (jurisprudencia-open-data)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urlopen(req, timeout=timeout) as response:
        content_type = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(content_type, errors="replace")


def buscar_jurisprudencia_lexml(
    consulta: str,
    tribunal: str | None = None,
    limite: int = 10,
) -> dict[str, Any]:
    """Busca jurisprudencia em fonte juridica aberta (LexML Brasil)."""
    if not consulta or not consulta.strip():
        raise ValueError("A consulta nao pode ser vazia.")

    limite = max(1, min(limite, 30))
    keyword = consulta.strip()
    if tribunal and tribunal.strip():
        keyword = f"{keyword} {tribunal.strip()}"

    encoded_keyword = quote_plus(keyword)
    # O filtro abaixo restringe a categoria para jurisprudencia.
    url = (
        f"{LEXML_BASE_URL}{LEXML_SEARCH_PATH}?keyword={encoded_keyword}"
        ";f1-tipoDocumento=Jurisprud%C3%AAncia"
    )

    html = _fetch_text(url)

    hits = re.findall(r'<a href="(/urn/[^"]+)">([^<]+)</a>', html, flags=re.IGNORECASE)
    unique_items: list[dict[str, str]] = []
    seen: set[str] = set()
    tribunal_tokens: list[str] = []
    if tribunal and tribunal.strip():
        normalized = _normalize(tribunal.strip())
        tribunal_tokens = TRIBUNAL_HINTS.get(normalized, [normalized])

    for href, titulo in hits:
        if tribunal_tokens:
            haystack = _normalize(f"{href} {titulo}")
            if not any(token in haystack for token in tribunal_tokens):
                continue

        full_url = f"{LEXML_BASE_URL}{href}"
        if full_url in seen:
            continue
        seen.add(full_url)
        unique_items.append(
            {
                "titulo": _clean_text(titulo),
                "url": full_url,
                "urn": href.removeprefix("/urn/"),
                "fonte": "LexML Brasil",
            }
        )
        if len(unique_items) >= limite:
            break

    total_match = re.search(r'<span id="itemCount">\s*([0-9]+)\s*</span>', html)
    total = int(total_match.group(1)) if total_match else len(unique_items)

    return {
        "fonte": "LexML Brasil",
        "consulta": consulta,
        "tribunal": tribunal,
        "total_aproximado": total,
        "resultados": unique_items,
        "observacao": (
            "Dados obtidos de fonte juridica aberta. "
            "Sempre valide a decisao diretamente no tribunal de origem."
        ),
    }


def detalhe_jurisprudencia_lexml(url_ou_urn: str) -> dict[str, Any]:
    """Retorna metadados e ementa de uma decisao do LexML via URL ou URN."""
    if not url_ou_urn or not url_ou_urn.strip():
        raise ValueError("Informe uma URL ou URN valida.")

    value = url_ou_urn.strip()
    if value.startswith("urn:lex:"):
        url = f"{LEXML_BASE_URL}/urn/{value}"
    elif value.startswith("/urn/"):
        url = f"{LEXML_BASE_URL}{value}"
    elif value.startswith("http://") or value.startswith("https://"):
        url = value
    else:
        raise ValueError("Formato invalido. Use URL LexML ou URN iniciando com urn:lex:.")

    html = _fetch_text(url)

    def extract_field(label: str) -> str | None:
        pattern = (
            rf"<strong>{re.escape(label)}</strong></div>"
            rf"<div class=\"col-xs-12 col-sm-12 col-md-11 col-lg-11 text-left\">(.*?)</div>"
        )
        match = re.search(pattern, html, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return None
        return _clean_text(match.group(1))

    return {
        "fonte": "LexML Brasil",
        "url": url,
        "localidade": extract_field("Localidade"),
        "autoridade": extract_field("Autoridade"),
        "titulo": extract_field("Título") or extract_field("Titulo"),
        "data": extract_field("Data"),
        "ementa": extract_field("Ementa"),
        "nome_uniforme": extract_field("Nome Uniforme"),
        "mais_detalhes": extract_field("Mais detalhes"),
        "observacao": (
            "Dados obtidos de fonte juridica aberta. "
            "Use para apoio em pesquisa, nao como orientacao juridica definitiva."
        ),
    }
