#!/usr/bin/env python3
"""Registro de atividade do computador para a varredura do Orbit (opcional).

A cada INTERVALO segundos grava qual programa e qual janela estão em primeiro
plano e se a pessoa está parada. Não tira print, não lê o teclado nem o
conteúdo das janelas. Os registros ficam só neste computador, em
~/.claude/orbit-atividade/AAAA-MM-DD.jsonl, são apagados depois de 35 dias e
só são lidos pela skill orbit:dia, que mostra o resumo no plano antes de
qualquer registro no Orbit.

  atividade.py amostra                  mostra o que seria gravado agora
  atividade.py rodar [--intervalo 30]   fica gravando (é o que o início automático chama)
  atividade.py pausar MINUTOS           para de gravar por um tempo (0 retoma)
  atividade.py status                   diz se está gravando, se está pausado e o que já foi gravado
  atividade.py resumo [--desde ISO] [--ate ISO]
  atividade.py instalar                 liga o início automático (Windows e macOS)
  atividade.py desinstalar [--apagar-registros]

Windows: só biblioteca padrão (ctypes). macOS: o nome do programa vem do
lsappinfo; o título da janela pede permissão de Acessibilidade (sem ela, grava
só o programa).
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta

CLAUDE_DIR = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
PASTA = os.path.join(CLAUDE_DIR, "orbit-atividade")
ARQ_PAUSA = os.path.join(PASTA, "pausa")
ARQ_VIVO = os.path.join(PASTA, "vivo")
ARQ_PID = os.path.join(PASTA, "pid")
INTERVALO_PADRAO = 30
OCIOSO_APOS = 300  # segundos sem mexer no teclado ou mouse
GUARDAR_DIAS = 35
TITULO_MAX = 160
NOME_LAUNCHD = "br.com.openexo.orbit-atividade"


def agora():
    return datetime.now().astimezone()


def ler_ts(texto):
    try:
        return datetime.fromisoformat(texto.replace("Z", "+00:00")).astimezone()
    except Exception:
        return None


# ------------------------------------------------------------------ Windows

def _amostra_windows():
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    # Tipos explícitos: sem eles o ctypes corta handles de 64 bits.
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    kernel32.GetTickCount.restype = wintypes.DWORD
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                                    ctypes.POINTER(wintypes.DWORD)]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]

    info = LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(LASTINPUTINFO)
    ocioso_s = 0
    if user32.GetLastInputInfo(ctypes.byref(info)):
        ocioso_s = ((kernel32.GetTickCount() - info.dwTime) & 0xFFFFFFFF) / 1000.0

    janela = user32.GetForegroundWindow()
    titulo, app = "", ""
    if janela:
        tamanho = user32.GetWindowTextLengthW(janela)
        buf = ctypes.create_unicode_buffer(tamanho + 1)
        user32.GetWindowTextW(janela, buf, tamanho + 1)
        titulo = buf.value
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(janela, ctypes.byref(pid))
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        processo = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
        if processo:
            try:
                caminho = ctypes.create_unicode_buffer(1024)
                tam = wintypes.DWORD(1024)
                if kernel32.QueryFullProcessImageNameW(processo, 0, caminho, ctypes.byref(tam)):
                    app = os.path.basename(caminho.value)
            finally:
                kernel32.CloseHandle(processo)
    return app, titulo, ocioso_s


# ------------------------------------------------------------------ macOS

def _amostra_mac():
    app, titulo, ocioso_s = "", "", 0
    try:
        frente = subprocess.run(["lsappinfo", "front"], capture_output=True, text=True, timeout=5).stdout.strip()
        if frente:
            r = subprocess.run(["lsappinfo", "info", "-only", "name", frente],
                               capture_output=True, text=True, timeout=5).stdout
            # Saída: "Nome do App" ASN:0x0-...: (in front)  ou  "LSDisplayName"="Nome"
            m = re.search(r'"(?:LSDisplayName|name)"\s*=\s*"([^"]*)"', r) or re.match(r'\s*"([^"]+)"\s+ASN:', r)
            app = m.group(1) if m else ""
    except Exception:
        pass
    try:
        # Precisa de Acessibilidade; sem ela fica só o nome do programa.
        linhas = ['tell application "System Events"',
                  'set p to first application process whose frontmost is true',
                  'if (count of windows of p) > 0 then return name of front window of p',
                  'end tell']
        comando = ["osascript"]
        for linha in linhas:
            comando += ["-e", linha]
        r = subprocess.run(comando, capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            titulo = r.stdout.strip()
    except Exception:
        pass
    try:
        r = subprocess.run(["ioreg", "-c", "IOHIDSystem", "-d", "4"], capture_output=True, text=True, timeout=5).stdout
        m = re.search(r'"HIDIdleTime"\s*=\s*(\d+)', r)
        if m:
            ocioso_s = int(m.group(1)) / 1e9
    except Exception:
        pass
    return app, titulo, ocioso_s


def amostrar():
    if sys.platform == "win32":
        return _amostra_windows()
    if sys.platform == "darwin":
        return _amostra_mac()
    return None


# ------------------------------------------------------------------ gravação

def pausado_ate():
    try:
        with open(ARQ_PAUSA, encoding="utf-8") as f:
            ate = ler_ts(f.read().strip())
        if ate and ate > agora():
            return ate
    except Exception:
        pass
    return None


def limpar_antigos():
    corte = (agora() - timedelta(days=GUARDAR_DIAS)).strftime("%Y-%m-%d")
    try:
        for nome in os.listdir(PASTA):
            if re.match(r"^\d{4}-\d{2}-\d{2}\.jsonl$", nome) and nome[:10] < corte:
                os.remove(os.path.join(PASTA, nome))
    except Exception:
        pass


def outro_rodando(intervalo):
    try:
        return time.time() - os.path.getmtime(ARQ_VIVO) < max(3 * intervalo, 90)
    except OSError:
        return False


def registro(app, titulo, ocioso_s, intervalo):
    linha = {"ts": agora().isoformat(timespec="seconds"), "s": intervalo}
    if ocioso_s >= OCIOSO_APOS:
        linha["ocioso"] = True
    else:
        linha["app"] = app or ""
        linha["janela"] = (titulo or "")[:TITULO_MAX]
    return linha


def gravar(linha):
    os.makedirs(PASTA, exist_ok=True)
    caminho = os.path.join(PASTA, linha["ts"][:10] + ".jsonl")
    with open(caminho, "a", encoding="utf-8") as f:
        f.write(json.dumps(linha, ensure_ascii=False) + "\n")


def cmd_rodar(args):
    if amostrar() is None:
        print("Sistema não suportado: só Windows e macOS.")
        sys.exit(2)
    os.makedirs(PASTA, exist_ok=True)
    if outro_rodando(args.intervalo):
        print("Já há um registro rodando.")
        return
    with open(ARQ_PID, "w") as f:
        f.write(str(os.getpid()))
    limpar_antigos()
    ultimo_dia = None
    while True:
        with open(ARQ_VIVO, "w") as f:
            f.write(agora().isoformat(timespec="seconds"))
        if not pausado_ate():
            try:
                app, titulo, ocioso_s = amostrar()
                gravar(registro(app, titulo, ocioso_s, args.intervalo))
            except Exception:
                pass
        dia = agora().date()
        if dia != ultimo_dia:
            limpar_antigos()
            ultimo_dia = dia
        time.sleep(args.intervalo)


def cmd_amostra(args):
    r = amostrar()
    if r is None:
        print(json.dumps({"ok": False, "erro": "Sistema não suportado: só Windows e macOS."}, ensure_ascii=False))
        sys.exit(2)
    app, titulo, ocioso_s = r
    print(json.dumps({"ok": True, "app": app, "janela": titulo[:TITULO_MAX], "ocioso_segundos": round(ocioso_s),
                      "seria_gravado": registro(app, titulo, ocioso_s, INTERVALO_PADRAO)}, ensure_ascii=False, indent=1))


def cmd_pausar(args):
    os.makedirs(PASTA, exist_ok=True)
    if args.minutos <= 0:
        try:
            os.remove(ARQ_PAUSA)
        except OSError:
            pass
        print("Registro retomado.")
        return
    ate = agora() + timedelta(minutes=args.minutos)
    with open(ARQ_PAUSA, "w", encoding="utf-8") as f:
        f.write(ate.isoformat(timespec="seconds"))
    print("Registro pausado até %s." % ate.strftime("%d/%m %H:%M"))


def cmd_status(args):
    vivo = None
    try:
        vivo = datetime.fromtimestamp(os.path.getmtime(ARQ_VIVO)).astimezone()
    except OSError:
        pass
    dias = sorted(n[:10] for n in os.listdir(PASTA) if n.endswith(".jsonl")) if os.path.isdir(PASTA) else []
    pausa = pausado_ate()
    print(json.dumps({
        "gravando": bool(vivo and (agora() - vivo).total_seconds() < 120),
        "ultimo_sinal": vivo.isoformat(timespec="seconds") if vivo else None,
        "pausado_ate": pausa.isoformat(timespec="minutes") if pausa else None,
        "dias_gravados": len(dias), "primeiro_dia": dias[0] if dias else None, "pasta": PASTA,
        "inicio_automatico": inicio_automatico_ligado(),
    }, ensure_ascii=False, indent=1))


# ------------------------------------------------------------------ resumo

_SUFIXOS = re.compile(
    r"\s+[-–—]\s+(Google Chrome|Microsoft​? Edge|Mozilla Firefox|Brave|Opera|Safari|"
    r"Visual Studio Code|Cursor|Microsoft Excel|Excel|Microsoft Word|Word|PowerPoint|Outlook|"
    r"Microsoft Teams|Teams|WhatsApp|Explorador de Arquivos|File Explorer)\s*$", re.I)


def normalizar_janela(titulo):
    t = re.sub(r"^\(\d+\+?\)\s*", "", titulo or "")   # contador de não lidas: "(3) Inbox"
    t = re.sub(r"\s+e mais \d+ guias?$", "", t)
    t = re.sub(r"\s+and \d+ more pages?$", "", t)
    t = _SUFIXOS.sub("", t)
    return t.strip() or "(sem título)"


def ler_registros(desde, ate):
    if not os.path.isdir(PASTA):
        return []
    linhas = []
    dia = desde.date()
    while dia <= ate.date():
        caminho = os.path.join(PASTA, dia.isoformat() + ".jsonl")
        if os.path.isfile(caminho):
            with open(caminho, encoding="utf-8", errors="replace") as f:
                for bruta in f:
                    try:
                        linha = json.loads(bruta)
                    except Exception:
                        continue
                    ts = ler_ts(linha.get("ts", ""))
                    if ts and desde <= ts <= ate:
                        linha["_ts"] = ts
                        linhas.append(linha)
        dia += timedelta(days=1)
    return linhas


def resumo(desde, ate, limite_janelas=40):
    """Minutos ativos por programa, por janela e por hora. None se não houver registro."""
    linhas = ler_registros(desde, ate)
    if not linhas:
        return None
    por_app, por_janela, por_hora = {}, {}, {}
    ativos_s = 0
    primeiro = ultimo = None
    for l in linhas:
        if l.get("ocioso"):
            continue
        s = float(l.get("s") or INTERVALO_PADRAO)
        ativos_s += s
        app = l.get("app") or "(desconhecido)"
        chave = (app, normalizar_janela(l.get("janela", "")))
        por_app[app] = por_app.get(app, 0) + s
        por_janela[chave] = por_janela.get(chave, 0) + s
        hora = l["_ts"].strftime("%Y-%m-%d %H")
        por_hora[hora] = por_hora.get(hora, 0) + s
        primeiro = primeiro or l["_ts"]
        ultimo = l["_ts"]
    if not ativos_s:
        return {"minutos_ativos": 0, "por_app": [], "por_janela": [], "por_hora": []}
    minutos = lambda seg: round(seg / 60)
    return {
        "minutos_ativos": minutos(ativos_s),
        "primeira_atividade": primeiro.isoformat(timespec="minutes"),
        "ultima_atividade": ultimo.isoformat(timespec="minutes"),
        "por_app": [{"app": a, "minutos": minutos(s)}
                    for a, s in sorted(por_app.items(), key=lambda x: -x[1]) if minutos(s) > 0],
        "por_janela": [{"app": a, "janela": j, "minutos": minutos(s)}
                       for (a, j), s in sorted(por_janela.items(), key=lambda x: -x[1])[:limite_janelas]
                       if minutos(s) > 0],
        "por_hora": [{"hora": h, "minutos": minutos(s)} for h, s in sorted(por_hora.items())],
    }


def cmd_resumo(args):
    fim = ler_ts(args.ate) if args.ate else agora()
    inicio = ler_ts(args.desde) if args.desde else fim.replace(hour=0, minute=0, second=0, microsecond=0)
    print(json.dumps(resumo(inicio, fim), ensure_ascii=False, indent=1))


# ------------------------------------------------------------------ início automático

def _copia_estavel():
    """Copia este script para a pasta de registros: o caminho do plugin muda a
    cada versão, e o início automático precisa de um caminho fixo."""
    os.makedirs(PASTA, exist_ok=True)
    destino = os.path.join(PASTA, "atividade.py")
    if os.path.abspath(__file__) != os.path.abspath(destino):
        shutil.copyfile(os.path.abspath(__file__), destino)
    return destino


def _inicio_windows():
    return os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu",
                        "Programs", "Startup", "orbit-atividade.cmd")


def _plist_mac():
    return os.path.expanduser("~/Library/LaunchAgents/%s.plist" % NOME_LAUNCHD)


def inicio_automatico_ligado():
    if sys.platform == "win32":
        return os.path.isfile(_inicio_windows())
    if sys.platform == "darwin":
        return os.path.isfile(_plist_mac())
    return False


def _pythonw():
    candidato = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return candidato if os.path.isfile(candidato) else sys.executable


def cmd_instalar(args):
    script = _copia_estavel()
    if sys.platform == "win32":
        pyw = _pythonw()
        caminho = _inicio_windows()
        # newline="" evita \r\r\n; chcp 65001 deixa o cmd ler caminhos com acento (C:\Users\João).
        with open(caminho, "w", encoding="utf-8", newline="") as f:
            f.write('@echo off\r\nchcp 65001 >nul\r\nstart "" "%s" "%s" rodar\r\n' % (pyw, script))
        DETACHED_PROCESS, CREATE_NEW_PROCESS_GROUP = 0x00000008, 0x00000200
        subprocess.Popen([pyw, script, "rodar"], creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
                         close_fds=True)
        print("Início automático ligado (%s) e registro iniciado." % caminho)
    elif sys.platform == "darwin":
        plist = _plist_mac()
        os.makedirs(os.path.dirname(plist), exist_ok=True)
        with open(plist, "w", encoding="utf-8") as f:
            f.write("""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>%s</string>
  <key>ProgramArguments</key><array><string>/usr/bin/python3</string><string>%s</string><string>rodar</string></array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
</dict></plist>
""" % (NOME_LAUNCHD, script))
        subprocess.run(["launchctl", "unload", plist], capture_output=True)
        subprocess.run(["launchctl", "load", "-w", plist], capture_output=True)
        print("Início automático ligado (%s) e registro iniciado." % plist)
    else:
        print("Sistema não suportado: só Windows e macOS.")
        sys.exit(2)


def cmd_desinstalar(args):
    if sys.platform == "win32":
        try:
            os.remove(_inicio_windows())
        except OSError:
            pass
        try:
            pid = open(ARQ_PID).read().strip()
            subprocess.run(["taskkill", "/PID", pid, "/F"], capture_output=True)
        except Exception:
            pass
    elif sys.platform == "darwin":
        plist = _plist_mac()
        subprocess.run(["launchctl", "unload", "-w", plist], capture_output=True)
        try:
            os.remove(plist)
        except OSError:
            pass
    for arq in (ARQ_VIVO, ARQ_PID, ARQ_PAUSA):
        try:
            os.remove(arq)
        except OSError:
            pass
    if args.apagar_registros and os.path.isdir(PASTA):
        shutil.rmtree(PASTA, ignore_errors=True)
        print("Início automático desligado e registros apagados.")
    else:
        print("Início automático desligado. Os registros continuam em %s." % PASTA)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("amostra").set_defaults(func=cmd_amostra)
    s = sub.add_parser("rodar")
    s.add_argument("--intervalo", type=int, default=INTERVALO_PADRAO)
    s.set_defaults(func=cmd_rodar)
    s = sub.add_parser("pausar")
    s.add_argument("minutos", type=int)
    s.set_defaults(func=cmd_pausar)
    sub.add_parser("status").set_defaults(func=cmd_status)
    s = sub.add_parser("resumo")
    s.add_argument("--desde")
    s.add_argument("--ate")
    s.set_defaults(func=cmd_resumo)
    sub.add_parser("instalar").set_defaults(func=cmd_instalar)
    s = sub.add_parser("desinstalar")
    s.add_argument("--apagar-registros", action="store_true")
    s.set_defaults(func=cmd_desinstalar)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
