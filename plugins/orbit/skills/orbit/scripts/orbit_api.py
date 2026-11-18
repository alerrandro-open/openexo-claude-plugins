#!/usr/bin/env python3
"""Cliente da API do Orbit para as skills orbit e dia.

Só usa a biblioteca padrão. O token pessoal (orb_...) vem de ORBIT_API_TOKEN
ou, no macOS, do Keychain (serviço orbit-api-token). O script nunca imprime o
token. A saída é sempre JSON.

  orbit_api.py token                      confere se há token e se a API aceita
  orbit_api.py me
  orbit_api.py listas [--busca TXT]
  orbit_api.py meta LISTA                 etiquetas, membros, status, sprint atual
  orbit_api.py tarefas --lista LISTA [--busca TXT] [--minhas] [--encerradas] [--desde AAAA-MM-DD]
  orbit_api.py entregar ARQUIVO.json [--simular]
  orbit_api.py horas TAREFA --data AAAA-MM-DD --inicio HH:MM --duracao "1h 30m" [--nota TXT] [--chave K] [--simular]
  orbit_api.py atualizar TAREFA [--status S [--lista LISTA]] [--descricao TXT [--substituir]] [--etiquetas "A,B"] [--simular]

LISTA e TAREFA aceitam o id ou o link do Orbit (/l/<id>/list, /t/<id>).
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get("ORBIT_API_URL", "https://orbit.openexo.com.br/api/v1").rstrip("/")
SERVICO_KEYCHAIN = "orbit-api-token"
LOTE = 50
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")

COMO_CRIAR = (
    "Crie um token no Orbit (Configurações > Perfil · Tokens de API) e guarde no "
    "Keychain rodando no Terminal: security add-generic-password -U -a \"$USER\" "
    "-s orbit-api-token -w  (cole o token quando pedir). Fora do macOS, use a "
    "variável ORBIT_API_TOKEN."
)


class ErroApi(Exception):
    def __init__(self, status, corpo):
        self.status = status
        self.corpo = corpo
        super().__init__("HTTP %s" % status)


def sair(msg, codigo=1, **extra):
    json.dump(dict({"ok": False, "erro": msg}, **extra), sys.stdout, ensure_ascii=False, indent=1)
    print()
    sys.exit(codigo)


def ler_token():
    tok = os.environ.get("ORBIT_API_TOKEN", "").strip()
    if tok:
        return tok, "variável ORBIT_API_TOKEN"
    if sys.platform == "darwin":
        try:
            r = subprocess.run(
                ["security", "find-generic-password", "-s", SERVICO_KEYCHAIN, "-w"],
                capture_output=True, text=True, timeout=15)
            tok = r.stdout.strip()
            if r.returncode == 0 and tok:
                return tok, "Keychain (%s)" % SERVICO_KEYCHAIN
        except Exception:
            pass
    return None, None


def chamar(metodo, caminho, corpo=None, consulta=None):
    tok, _ = ler_token()
    if not tok:
        sair("Sem token da API do Orbit. " + COMO_CRIAR, codigo=2)
    url = BASE + caminho
    if consulta:
        consulta = {k: v for k, v in consulta.items() if v not in (None, "", False)}
        if consulta:
            url += "?" + urllib.parse.urlencode(consulta)
    dados = json.dumps(corpo, ensure_ascii=False).encode() if corpo is not None else None
    for tentativa in range(4):
        req = urllib.request.Request(url, data=dados, method=metodo)
        req.add_header("Authorization", "Bearer " + tok)
        req.add_header("Accept", "application/json")
        req.add_header("User-Agent", "orbit-skill")
        if dados is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                texto = r.read().decode() or "{}"
                return json.loads(texto)
        except urllib.error.HTTPError as e:
            texto = e.read().decode(errors="replace")
            try:
                corpo_erro = json.loads(texto)
            except ValueError:
                corpo_erro = {"texto": texto[:500]}
            # 429 e 5xx: as escritas são idempotentes (external_key / entry_key),
            # então repetir é seguro.
            if (e.code == 429 or e.code >= 500) and tentativa < 3:
                espera = e.headers.get("Retry-After")
                time.sleep(float(espera) if espera and espera.isdigit() else 2 * (tentativa + 1))
                continue
            raise ErroApi(e.code, corpo_erro)
        except urllib.error.URLError as e:
            if tentativa < 3:
                time.sleep(2 * (tentativa + 1))
                continue
            sair("Sem conexão com a API do Orbit: %s" % e.reason)


def mostrar(obj):
    json.dump(obj, sys.stdout, ensure_ascii=False, indent=1)
    print()


def id_de(valor):
    m = UUID.search(valor or "")
    if not m:
        sair("Não encontrei um id (uuid) em %r." % valor)
    return m.group(0)


def tratar_erro_http(e):
    if e.status == 401:
        sair("A API recusou o token (401): inválido, vencido ou revogado. " + COMO_CRIAR,
             status=401, resposta=e.corpo)
    sair("A API respondeu %s." % e.status, status=e.status, resposta=e.corpo)


# ---------------------------------------------------------------- comandos

def cmd_token(args):
    tok, origem = ler_token()
    if not tok:
        sair("Sem token. " + COMO_CRIAR, codigo=2)
    try:
        me = chamar("GET", "/me")
    except ErroApi as e:
        tratar_erro_http(e)
    mostrar({"ok": True, "origem": origem, "usuario": (me.get("user") or {}).get("full_name"),
             "organizacoes": [o.get("name") for o in me.get("organizations", [])]})


def cmd_me(args):
    mostrar(chamar("GET", "/me"))


def cmd_listas(args):
    d = chamar("GET", "/lists", consulta={"q": args.busca})
    mostrar([{"id": l["id"], "nome": l["name"], "espaco": (l.get("space") or {}).get("name"),
              "pasta": (l.get("folder") or {}).get("name"), "url": l.get("url")}
             for l in d.get("data", [])])


def cmd_meta(args):
    mostrar(chamar("GET", "/lists/%s/meta" % id_de(args.lista)))


def cmd_tarefas(args):
    consulta = {"list_id": id_de(args.lista), "q": args.busca,
                "assignee": "me" if args.minhas else None,
                "include_closed": "true" if args.encerradas else None,
                "updated_since": args.desde}
    saida, depois = [], None
    for _ in range(50):
        d = chamar("GET", "/tasks", consulta=dict(consulta, after=depois))
        saida.extend(d.get("data", []))
        depois = d.get("next_cursor")
        if not depois:
            break
    mostrar([{
        "id": t["id"], "titulo": t["title"], "status": (t.get("status") or {}).get("name"),
        "tipo": (t.get("status") or {}).get("type"),
        "horas": round((t.get("tracked_total") or 0) / 3600, 2),
        "estimativa_min": t.get("time_estimate_minutes"),
        "sprint": [s.get("name") for s in t.get("sprint") or []],
        "etiquetas": [g.get("name") for g in t.get("tags") or []],
        "inicio": t.get("start_date"), "vencimento": t.get("due_date"),
        "external_keys": t.get("external_keys") or [],
        "atualizada": t.get("updated_at"), "url": t.get("url"),
        "descricao": (t.get("description") or "")[:300],
    } for t in saida])


# Atalhos de status. A API resolve "doing" pelo primeiro status do tipo
# (na lista OpenExO, "Waiting - Impedido"), então o script troca o atalho
# pelo nome do status certo da lista antes de mandar.
ATALHOS = {
    "doing": ("doing", ("doing", "em andamento"), "Doing - Em Andamento"),
    "closed": ("closed", ("closed", "encerrad"), "Closed - Encerrada"),
    "open": ("open", ("to do", "a fazer"), "To Do - A Fazer"),
}
_status_cache = {}


def status_da_lista(lid):
    if lid not in _status_cache:
        try:
            _status_cache[lid] = chamar("GET", "/lists/%s/meta" % lid).get("statuses", [])
        except ErroApi:
            _status_cache[lid] = []
    return _status_cache[lid]


def resolver_status(valor, lid=None):
    """Troca doing/closed/open pelo nome do status certo da lista."""
    if not isinstance(valor, str) or valor.strip().lower() not in ATALHOS:
        return valor
    tipo, termos, padrao = ATALHOS[valor.strip().lower()]
    if lid:
        candidatos = [s for s in status_da_lista(lid) if s.get("type") == tipo]
        for termo in termos:
            for s in candidatos:
                if termo in s.get("name", "").lower():
                    return s["name"]
    return padrao


def nomes_de_status(list_ids):
    nomes = {}
    for lid in set(filter(None, list_ids)):
        try:
            for s in chamar("GET", "/lists/%s/meta" % lid).get("statuses", []):
                nomes[s["id"]] = s["name"]
        except ErroApi:
            pass
    return nomes


def cmd_entregar(args):
    with open(args.arquivo, encoding="utf-8") as f:
        dados = json.load(f)
    itens = dados if isinstance(dados, list) else dados.get("items", [])
    if not itens:
        sair("O arquivo não tem itens (use {\"items\": [...]} ou uma lista).")
    for i in itens:
        if i.get("list_id"):
            i["list_id"] = id_de(i["list_id"])
        if i.get("final_status"):
            i["final_status"] = resolver_status(i["final_status"], i.get("list_id"))
    resultados = []
    for n in range(0, len(itens), LOTE):
        lote = itens[n:n + LOTE]
        try:
            d = chamar("POST", "/deliveries", {"dry_run": bool(args.simular), "items": lote})
        except ErroApi as e:
            tratar_erro_http(e)
        resultados.extend(d.get("results", []))
    nomes = nomes_de_status(i.get("list_id") for i in itens)
    saida = []
    for item, r in zip(itens, resultados):
        linha = {"titulo": item.get("title"), "external_key": item.get("external_key"),
                 "ok": r.get("ok")}
        if r.get("ok"):
            linha.update({"acao": r.get("action"), "status": nomes.get(r.get("status"), r.get("status")),
                          "horas_total": round((r.get("tracked_total") or 0) / 3600, 2),
                          "avisos": r.get("warnings") or []})
            if not args.simular:
                linha.update({"task_id": r.get("task_id"), "url": r.get("url")})
        else:
            linha.update({"erro": r.get("error_code"), "mensagem": r.get("message")})
        saida.append(linha)
    falhas = sum(1 for r in saida if not r["ok"])
    mostrar({"simulacao": bool(args.simular), "itens": len(saida), "falhas": falhas, "resultados": saida})
    sys.exit(1 if falhas else 0)


def cmd_horas(args):
    tarefa = id_de(args.tarefa)
    chave = args.chave or "%s:%s:%s:%s" % (tarefa, args.data, args.inicio, re.sub(r"\s+", "", args.duracao))
    corpo = {"dry_run": bool(args.simular), "date": args.data, "start": args.inicio,
             "duration": args.duracao, "person": "me", "note": args.nota or "", "entry_key": chave}
    try:
        r = chamar("POST", "/tasks/%s/time-entries" % tarefa, corpo)
    except ErroApi as e:
        tratar_erro_http(e)
    mostrar(r)


def cmd_atualizar(args):
    corpo = {"dry_run": bool(args.simular)}
    if args.status:
        corpo["status"] = resolver_status(args.status, id_de(args.lista) if args.lista else None)
    if args.descricao:
        corpo["description"] = args.descricao
        corpo["description_mode"] = "replace" if args.substituir else "append"
    if args.etiquetas is not None:
        corpo["tags"] = [t.strip() for t in args.etiquetas.split(",") if t.strip()]
    if len(corpo) == 1:
        sair("Nada para atualizar: use --status, --descricao ou --etiquetas.")
    try:
        r = chamar("PATCH", "/tasks/%s" % id_de(args.tarefa), corpo)
    except ErroApi as e:
        tratar_erro_http(e)
    mostrar(r)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("token").set_defaults(func=cmd_token)
    sub.add_parser("me").set_defaults(func=cmd_me)

    s = sub.add_parser("listas")
    s.add_argument("--busca")
    s.set_defaults(func=cmd_listas)

    s = sub.add_parser("meta")
    s.add_argument("lista")
    s.set_defaults(func=cmd_meta)

    s = sub.add_parser("tarefas")
    s.add_argument("--lista", required=True)
    s.add_argument("--busca")
    s.add_argument("--minhas", action="store_true")
    s.add_argument("--encerradas", action="store_true", help="inclui as encerradas")
    s.add_argument("--desde", help="atualizadas desde AAAA-MM-DD")
    s.set_defaults(func=cmd_tarefas)

    s = sub.add_parser("entregar")
    s.add_argument("arquivo")
    s.add_argument("--simular", action="store_true", help="dry_run: valida sem gravar")
    s.set_defaults(func=cmd_entregar)

    s = sub.add_parser("horas")
    s.add_argument("tarefa")
    s.add_argument("--data", required=True)
    s.add_argument("--inicio", required=True)
    s.add_argument("--duracao", required=True)
    s.add_argument("--nota")
    s.add_argument("--chave", help="entry_key; padrão: tarefa:data:inicio:duracao")
    s.add_argument("--simular", action="store_true")
    s.set_defaults(func=cmd_horas)

    s = sub.add_parser("atualizar")
    s.add_argument("tarefa")
    s.add_argument("--status", help="closed, doing, open ou o nome do status")
    s.add_argument("--lista", help="lista da tarefa, para achar o nome certo do status")
    s.add_argument("--descricao")
    s.add_argument("--substituir", action="store_true", help="troca a descrição em vez de acrescentar")
    s.add_argument("--etiquetas", help="lista completa, separada por vírgula")
    s.add_argument("--simular", action="store_true")
    s.set_defaults(func=cmd_atualizar)

    args = p.parse_args()
    try:
        args.func(args)
    except ErroApi as e:
        tratar_erro_http(e)


if __name__ == "__main__":
    main()
