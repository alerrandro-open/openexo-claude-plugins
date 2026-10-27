#!/usr/bin/env python3
"""Coleta o que a pessoa fez no Claude e no git desde a última varredura.

Usado pela skill orbit:dia. Só lê os históricos locais do Claude
(~/.claude/projects/*/*.jsonl) e o git; a única escrita é o estado da
varredura em ~/.claude/orbit-varredura.json (subcomandos marcar e concluir).

  coletar_dia.py coletar [--desde ISO] [--ate ISO]
  coletar_dia.py marcar --task "Título" [--lista URL] CHAVE [CHAVE ...]
  coletar_dia.py concluir --ate ISO
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta

CLAUDE_DIR = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
ESTADO = os.path.join(CLAUDE_DIR, "orbit-varredura.json")
PERFIL = os.path.join(CLAUDE_DIR, "orbit-perfil.md")
MARCA = "[varredura-orbit]"
PAUSA_MAX = timedelta(minutes=15)
MINUTOS_POR_BLOCO = 5
JANELA_MAX = timedelta(days=3)


def agora():
    return datetime.now().astimezone()


def ler_ts(texto):
    try:
        return datetime.fromisoformat(texto.replace("Z", "+00:00")).astimezone()
    except Exception:
        return None


def ler_estado():
    try:
        with open(ESTADO, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"ultima_varredura": None, "registradas": {}}


def gravar_estado(estado):
    tmp = ESTADO + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)
    os.replace(tmp, ESTADO)


def pastas_do_perfil():
    try:
        texto = open(PERFIL, encoding="utf-8").read()
    except Exception:
        return []
    m = re.search(r"^- Pastas de projetos:\s*(.+)$", texto, re.M)
    if not m:
        return []
    return [os.path.expanduser(p.strip()) for p in m.group(1).split(",") if p.strip()]


def texto_da_mensagem(msg):
    conteudo = (msg or {}).get("content")
    if isinstance(conteudo, str):
        return conteudo
    partes = []
    for bloco in conteudo or []:
        if isinstance(bloco, dict) and bloco.get("type") == "text":
            partes.append(bloco.get("text", ""))
    return "\n".join(partes)


def eh_pedido_humano(linha):
    if linha.get("type") != "user":
        return False
    origem = (linha.get("origin") or {}).get("kind") or linha.get("turnOrigin")
    if origem and origem != "human":
        return False
    return bool(texto_da_mensagem(linha.get("message")).strip())


def raiz_do_repo(cwd):
    m = re.match(r"^(.*?)/\.claude/worktrees/[^/]+", cwd or "")
    base = m.group(1) if m else cwd
    try:
        saida = subprocess.run(
            ["git", "-C", base, "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=10,
        )
        if saida.returncode == 0:
            return saida.stdout.strip()
    except Exception:
        pass
    return base


def ler_sessao(caminho, desde, ate):
    titulo = None
    cwd = None
    branch = None
    pedido = None
    relatorio = None
    marcas = []
    mensagens = 0
    eh_varredura = False
    primeira_mensagem = True
    with open(caminho, encoding="utf-8", errors="replace") as f:
        for bruta in f:
            try:
                linha = json.loads(bruta)
            except Exception:
                continue
            if linha.get("customTitle"):
                titulo = linha["customTitle"]
            if linha.get("isSidechain"):
                continue
            cwd = linha.get("cwd") or cwd
            branch = linha.get("gitBranch") or branch
            tipo = linha.get("type")
            if tipo not in ("user", "assistant"):
                continue
            ts = ler_ts(linha.get("timestamp", ""))
            humano = eh_pedido_humano(linha)
            texto_user = texto_da_mensagem(linha.get("message")).strip() if tipo == "user" else ""
            if texto_user and primeira_mensagem:
                # Só a tarefa agendada abre o chat com a marca; a skill carregada
                # no meio de outro chat também cita a marca e não pode excluí-lo.
                eh_varredura = texto_user.startswith(MARCA)
                primeira_mensagem = False
            if not ts or ts < desde or ts > ate:
                continue
            if tipo == "assistant":
                texto = texto_da_mensagem(linha.get("message")).strip()
                if texto:
                    relatorio = texto
                marcas.append(ts)
                mensagens += 1
            elif humano:
                if pedido is None:
                    pedido = texto_da_mensagem(linha.get("message")).strip()
                marcas.append(ts)
                mensagens += 1
    if eh_varredura or not marcas:
        return None
    marcas.sort()
    intervalos = []
    for ts in marcas:
        if intervalos and ts - intervalos[-1][1] <= PAUSA_MAX:
            intervalos[-1][1] = ts
        else:
            intervalos.append([ts, ts])
    for intervalo in intervalos:
        intervalo[1] += timedelta(minutes=MINUTOS_POR_BLOCO)
    return {
        "chave": "sessao:" + os.path.splitext(os.path.basename(caminho))[0],
        "titulo": titulo,
        "cwd": cwd,
        "repo": raiz_do_repo(cwd) if cwd else None,
        "branch": branch,
        "inicio": marcas[0].isoformat(timespec="minutes"),
        "fim": marcas[-1].isoformat(timespec="minutes"),
        "minutos_ativos": minutos_de(intervalos),
        "_intervalos": intervalos,
        "mensagens": mensagens,
        "pedido_inicial": (pedido or "")[:400],
        "relatorio_final": (relatorio or "")[:1500],
    }


def minutos_de(intervalos):
    return int(sum((b - a for a, b in intervalos), timedelta(0)).total_seconds() // 60)


def uniao(intervalos):
    juntos = []
    for a, b in sorted(intervalos):
        if juntos and a <= juntos[-1][1]:
            juntos[-1][1] = max(juntos[-1][1], b)
        else:
            juntos.append([a, b])
    return juntos


def repos_nas_pastas(pastas):
    achados = set()
    for pasta in pastas:
        for raiz, dirs, _ in os.walk(pasta):
            profundidade = raiz[len(pasta):].count(os.sep)
            if ".git" in dirs or os.path.isfile(os.path.join(raiz, ".git")):
                if "/.claude/worktrees/" not in raiz:
                    achados.add(raiz)
                dirs[:] = []
                continue
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "node_modules"]
            if profundidade >= 3:
                dirs[:] = []
    return achados


def identidade_git(repo):
    nomes = set()
    for chave in ("user.name", "user.email"):
        for args in (["git", "config", "--global", chave], ["git", "-C", repo, "config", chave]):
            try:
                saida = subprocess.run(args, capture_output=True, text=True, timeout=10)
                if saida.returncode == 0 and saida.stdout.strip():
                    nomes.add(saida.stdout.strip())
            except Exception:
                pass
    return nomes


def commits_do_repo(repo, desde, ate):
    quem = identidade_git(repo)
    if not quem:
        return []
    try:
        saida = subprocess.run(
            ["git", "-C", repo, "log", "--all", "--since=" + desde.isoformat(),
             "--until=" + ate.isoformat(), "--format=%H%x09%h%x09%aI%x09%an%x09%ae%x09%s"],
            capture_output=True, text=True, timeout=30,
        )
    except Exception:
        return []
    commits = []
    for linha in saida.stdout.splitlines():
        partes = linha.split("\t", 5)
        if len(partes) < 6:
            continue
        completo, curto, data, nome, email, assunto = partes
        if nome not in quem and email not in quem:
            continue
        commits.append({"chave": "commit:" + completo, "repo": repo, "hash": curto,
                        "data": data, "assunto": assunto})
    return commits


def coletar(args):
    estado = ler_estado()
    fim = ler_ts(args.ate) if args.ate else agora()
    if args.desde:
        inicio = ler_ts(args.desde)
    elif estado.get("ultima_varredura"):
        inicio = ler_ts(estado["ultima_varredura"])
    else:
        inicio = fim.replace(hour=0, minute=0, second=0, microsecond=0)
    aviso = None
    if fim - inicio > JANELA_MAX:
        aviso = "Janela maior que 3 dias: limitada aos últimos 3 dias. Confirme com o usuário se quer ir mais atrás (use --desde)."
        inicio = fim - JANELA_MAX

    registradas = estado.get("registradas", {})
    sessoes = []
    limite_mtime = inicio.timestamp()
    for caminho in glob.glob(os.path.join(CLAUDE_DIR, "projects", "*", "*.jsonl")):
        try:
            if os.path.getmtime(caminho) < limite_mtime:
                continue
            sessao = ler_sessao(caminho, inicio, fim)
        except Exception:
            continue
        if sessao:
            sessao["ja_registrado"] = registradas.get(sessao["chave"])
            sessoes.append(sessao)
    sessoes.sort(key=lambda s: s["inicio"])
    soma = sum(s["minutos_ativos"] for s in sessoes)
    real = minutos_de(uniao([i for s in sessoes for i in s["_intervalos"]]))
    for s in sessoes:
        del s["_intervalos"]
        s["minutos_proporcionais"] = round(real * s["minutos_ativos"] / soma) if soma else 0

    repos = {s["repo"] for s in sessoes if s.get("repo")}
    repos |= repos_nas_pastas(pastas_do_perfil())
    commits = []
    vistos = set()
    for repo in sorted(repos):
        for c in commits_do_repo(repo, inicio, fim):
            if c["chave"] in vistos:
                continue
            vistos.add(c["chave"])
            c["ja_registrado"] = registradas.get(c["chave"])
            commits.append(c)
    commits.sort(key=lambda c: c["data"])

    saida = {
        "desde": inicio.isoformat(timespec="minutes"),
        "ate": fim.isoformat(timespec="minutes"),
        "aviso": aviso,
        "minutos_reais_no_claude": real,
        "minutos_somados_dos_chats": soma,
        "sessoes": sessoes,
        "commits": commits,
        "repos_olhados": sorted(repos),
    }
    json.dump(saida, sys.stdout, ensure_ascii=False, indent=1)
    print()


def marcar(args):
    estado = ler_estado()
    registradas = estado.setdefault("registradas", {})
    for chave in args.chaves:
        registradas[chave] = {"task": args.task, "lista": args.lista,
                              "em": agora().isoformat(timespec="minutes")}
    gravar_estado(estado)
    print("marcadas %d chaves para %r" % (len(args.chaves), args.task))


def concluir(args):
    estado = ler_estado()
    estado["ultima_varredura"] = ler_ts(args.ate).isoformat(timespec="seconds")
    corte = (agora() - timedelta(days=30)).isoformat()
    estado["registradas"] = {k: v for k, v in estado.get("registradas", {}).items()
                             if (v or {}).get("em", corte) >= corte}
    gravar_estado(estado)
    print("ultima_varredura =", estado["ultima_varredura"])


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("coletar")
    c.add_argument("--desde")
    c.add_argument("--ate")
    c.set_defaults(func=coletar)
    m = sub.add_parser("marcar")
    m.add_argument("--task", required=True)
    m.add_argument("--lista")
    m.add_argument("chaves", nargs="+")
    m.set_defaults(func=marcar)
    f = sub.add_parser("concluir")
    f.add_argument("--ate", required=True)
    f.set_defaults(func=concluir)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
