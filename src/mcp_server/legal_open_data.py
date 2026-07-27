from __future__ import annotations

from datetime import date, datetime
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
ORGAO_HINTS = {
    "turma": [";turma."],
    "secao": [";secao."],
    "pleno": [";pleno"],
    "camara": [";camara"],
    "carf": ["carf", "conselho.administrativo.recursos.fiscais"],
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


def _parse_date_safe(value: str | None) -> date | None:
    if not value:
        return None
    raw = value.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _extract_date_from_urn(urn: str) -> date | None:
    match = re.search(r";(\d{4}-\d{2}-\d{2});", urn)
    if not match:
        return None
    return _parse_date_safe(match.group(1))


def _matches_orgao(urn: str, orgao: str | None) -> bool:
    if not orgao or not orgao.strip():
        return True
    normalized = _normalize(orgao.strip())
    tokens = ORGAO_HINTS.get(normalized, [normalized])
    haystack = _normalize(urn)
    return any(token in haystack for token in tokens)


def _build_prompt_summary(
    consulta: str,
    tribunal: str | None,
    orgao: str | None,
    data_inicio: str | None,
    data_fim: str | None,
    itens: list[dict[str, Any]],
) -> str:
    lines = [
        "Contexto da pesquisa de jurisprudencia:",
        f"- Consulta: {consulta}",
        f"- Tribunal: {tribunal or 'nao informado'}",
        f"- Orgao: {orgao or 'nao informado'}",
        f"- Periodo: {data_inicio or 'aberto'} ate {data_fim or 'aberto'}",
        "",
        "Resultados selecionados:",
    ]

    for idx, item in enumerate(itens, start=1):
        ementa = (item.get("ementa") or "")[:700]
        lines.extend(
            [
                f"{idx}. {item.get('titulo') or 'Sem titulo'}",
                f"   - Data: {item.get('data') or 'nao informada'}",
                f"   - Autoridade: {item.get('autoridade') or 'nao informada'}",
                f"   - URN: {item.get('urn') or 'nao informada'}",
                f"   - URL: {item.get('url') or 'nao informada'}",
                f"   - Ementa (trecho): {ementa or 'nao disponivel'}",
            ]
        )

    lines.extend(
        [
            "",
            "Tarefa sugerida para o modelo:",
            "Com base nos resultados acima, faca uma analise comparativa de fundamentos,",
            "identifique convergencias/divergencias e extraia teses juridicas relevantes.",
        ]
    )
    return "\n".join(lines)


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


def buscar_jurisprudencia_avancada_lexml(
    consulta: str,
    tribunal: str | None = None,
    orgao: str | None = None,
    data_inicio: str | None = None,
    data_fim: str | None = None,
    limite: int = 5,
) -> dict[str, Any]:
    """Busca jurisprudencia com filtros adicionais e resumo pronto para prompt."""
    inicio = _parse_date_safe(data_inicio) if data_inicio else None
    fim = _parse_date_safe(data_fim) if data_fim else None
    if (data_inicio and not inicio) or (data_fim and not fim):
        raise ValueError("Datas invalidas. Use YYYY-MM-DD ou DD/MM/YYYY.")
    if inicio and fim and inicio > fim:
        raise ValueError("data_inicio nao pode ser maior que data_fim.")

    limite = max(1, min(limite, 10))
    base = buscar_jurisprudencia_lexml(consulta=consulta, tribunal=tribunal, limite=30)
    selecionados: list[dict[str, Any]] = []

    for item in base["resultados"]:
        urn = item.get("urn") or ""
        if not _matches_orgao(urn, orgao):
            continue

        data_item = _extract_date_from_urn(urn)
        if inicio and data_item and data_item < inicio:
            continue
        if fim and data_item and data_item > fim:
            continue

        detalhe = detalhe_jurisprudencia_lexml(item["url"])
        data_detalhe = _parse_date_safe(detalhe.get("data"))
        data_ref = data_item or data_detalhe
        if (inicio or fim) and not data_ref:
            continue
        if inicio and data_ref and data_ref < inicio:
            continue
        if fim and data_ref and data_ref > fim:
            continue

        selecionados.append(
            {
                "titulo": detalhe.get("titulo") or item.get("titulo"),
                "data": detalhe.get("data"),
                "autoridade": detalhe.get("autoridade"),
                "ementa": detalhe.get("ementa"),
                "urn": detalhe.get("nome_uniforme") or item.get("urn"),
                "url": item.get("url"),
            }
        )

        if len(selecionados) >= limite:
            break

    return {
        "fonte": "LexML Brasil",
        "consulta": consulta,
        "tribunal": tribunal,
        "orgao": orgao,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "quantidade": len(selecionados),
        "resultados": selecionados,
        "resumo_prompt": _build_prompt_summary(
            consulta=consulta,
            tribunal=tribunal,
            orgao=orgao,
            data_inicio=data_inicio,
            data_fim=data_fim,
            itens=selecionados,
        ),
        "observacao": (
            "Resultado para apoio em pesquisa jurisprudencial. "
            "Valide sempre com as publicacoes oficiais do orgao julgador."
        ),
    }
