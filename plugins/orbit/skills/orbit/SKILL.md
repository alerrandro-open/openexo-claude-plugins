---
name: orbit
description: Registra entregas no Orbit (orbit.openexo.com.br), o gestor de tarefas da OpenExO. Use ao fechar um bloco de trabalho (commit/push) ou quando pedirem para criar ou atualizar tasks no Orbit.
---

# Registrar entregas no Orbit

Skill do time OpenExO. Quem usa tem o próprio perfil (nome no Orbit, padrões e
listas dos projetos) em `~/.claude/orbit-perfil.md`, fora da pasta da skill,
para não se perder quando a skill for atualizada.

Para registrar o dia inteiro de uma vez (chats, commits, agenda, e-mails...),
use a skill `dia` deste plugin, que monta o plano e usa esta skill para gravar.

## Pré-requisitos

O registro é feito pela **API do Orbit**, com o token pessoal de quem está
usando. O navegador (Claude in Chrome) fica só como reserva (seção 6).

`${CLAUDE_SKILL_DIR}` é a pasta desta skill; se aparecer vazio, use a
pasta-base informada quando a skill foi carregada. Confira o token:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/orbit_api.py" token
```

- `"ok": true`: siga pela API.
- Sem token ou 401: peça ao usuário para criar um token no Orbit
  (Configurações > Perfil · Tokens de API) e guardá-lo no cofre do sistema,
  rodando ele mesmo. O comando pede o token: é só colar e teclar Enter.
  - macOS (Terminal):

    ```bash
    security add-generic-password -U -a "$USER" -s orbit-api-token -w
    ```

  - Windows (PowerShell ou Prompt de Comando), no Gerenciador de Credenciais:

    ```bash
    cmdkey /generic:orbit-api-token /user:orbit /pass
    ```

  - Outros sistemas: variável de ambiente `ORBIT_API_TOKEN`.

  Enquanto não houver token, use o navegador.
- Windows sem Python: o script precisa do Python 3. Peça para a pessoa
  instalar (`winget install Python.Python.3.12`) e abrir uma sessão nova.

O token é uma credencial: nunca peça no chat, não grave em arquivo, não
imprima e não passe na linha de comando. O script lê sozinho do Keychain, do
Gerenciador de Credenciais ou da variável.

## 1. Perfil de quem está usando

Leia `~/.claude/orbit-perfil.md`. Se não existir:

- Sessão principal: pergunte ao usuário o nome exatamente como aparece no
  Orbit (campo Responsáveis) e crie o arquivo com este modelo:

  ```markdown
  # Perfil Orbit

  - Nome no Orbit: Fulano de Tal
  - Prioridade padrão: Alta
  - Horas estimadas padrão: 1h
  - Confirmar antes de criar: sim
  - Pastas de projetos: ~/Documents/Projetos
  - Ignorar:

  ## Listas

  | Projeto (repo) | Lista no Orbit | Etiqueta |
  |---|---|---|

  ## Notas
  ```

- Agente em segundo plano: não invente o responsável. Pare e avise a sessão principal.

O responsável é quem é dono do token (`"me"`). Outra pessoa (entrega feita em
dupla, registro para um colega) só quando o usuário pedir.

"Confirmar antes de criar" ausente conta como `sim`.

**O que não vai para o Orbit:**
- **"Ignorar":** nomes de repositório ou pasta (ou caminhos), separados por
  vírgula, que nunca vão para o Orbit. Por exemplo, projetos pessoais ou de
  outra empresa.
- **Uma sessão só:** comece uma mensagem com `[sem-orbit]`, em qualquer
  momento da sessão. A varredura tira a sessão inteira.
- **Numa sessão em que a pessoa escreveu `[sem-orbit]`:** esta skill não registra nada,
  mesmo depois de commit, a menos que a pessoa peça.

## 2. Lista e etiqueta do projeto

Procure o projeto (repo) na tabela "Listas" do perfil. O time recebe essa
tabela preenchida junto com o prompt de instalação; a skill não traz listas
nem nomes de clientes porque o repositório é público.

Projeto fora da tabela: procure com `orbit_api.py listas --busca <nome>` (as de
clientes ficam no espaço OpenExO › Projetos Growth), confirme com o usuário o
link e a etiqueta e grave a linha na tabela do perfil. Agente em segundo plano
não adivinha: pare e avise a sessão principal.

Use as etiquetas exatamente como estão na linha do projeto. Algumas linhas
pedem mais de uma (etiqueta do projeto + etiqueta do cliente). Os nomes
válidos da lista saem em `orbit_api.py meta <lista>` (`tags`).

## 3. Padrão de cada task

| Campo | Valor | Na API |
|---|---|---|
| Título | `Área \| O que foi entregue` (ex.: `Monitoramento \| Central de avisos com horário por tipo`) | `title` |
| Status | final `Closed - Encerrada` (entregue) ou `Doing - Em Andamento` (em andamento) | `final_status`: `"closed"`, `"doing"` ou o nome (o script troca o atalho pelo nome do status da lista: `doing` vira `Doing - Em Andamento`, e não o primeiro status do tipo, como `Waiting - Impedido`) |
| Responsáveis | quem é dono do token | `assignees: ["me"]` (outra pessoa: id em `meta` → `members`) |
| Prioridade | "Prioridade padrão" do perfil (sem perfil: `Alta`) | `priority`; só na criação, a API não muda depois |
| Etiquetas | as da linha do projeto no perfil, exatamente com esse nome | `tags` |
| Sprint | a sprint atual (só ela aceita tarefa nova) | `sprint: "current"` |
| Horas estimadas | obrigatório; "Horas estimadas padrão" do perfil (ex.: `1h`) | `estimate`: `"30m"`, `"1h"`, `"1h 30m"` |
| Datas | Início e Vencimento = dia da entrega | `start_date`, `due_date` (`AAAA-MM-DD`) |
| Descrição | o que mudou em 2-5 linhas, em português, e a lista de commits (`hash mensagem`) | `description` + `description_mode: "append"` |
| Horas | dia e hora reais do trabalho | `time_entries: [{date, start, duration, person: "me", note}]` |
| Chave | identifica a entrega (abaixo) | `external_key` |

Commits: `git log --oneline` no repo, só os daquela entrega.

**Chave (`external_key`):** `orbit:<pessoa>:<AAAA-MM-DD>:<assunto>`, com a
pessoa e o assunto em minúsculas, sem acentos e com hífens (ex.:
`orbit:fulano-de-tal:2026-11-13:central-de-avisos`). A mesma chave na mesma
lista atualiza a task em vez de criar outra. Guarde a chave: é ela que
permite atualizar depois.

**Horas:** `start` é a hora real em que o trabalho começou, e início +
duração não pode passar de agora (fuso de São Paulo). Encerrar exige horas:
mande os `time_entries` na mesma entrega.

## 4. Fluxo pela API

Scripts: `python3 "${CLAUDE_SKILL_DIR}/scripts/orbit_api.py" <comando>`.
`LISTA` e `TAREFA` aceitam o id ou o link do Orbit.

1. **Evite duplicar.** `tarefas --lista LISTA --busca "<assunto>" --encerradas`
   (acrescente `--minhas` e `--desde AAAA-MM-DD` para estreitar). Se a task já
   existir, não crie outra:
   - com `external_keys`: mande a entrega de novo com a mesma chave, com só o
     que é novo na descrição e só as horas novas em `time_entries`;
   - sem `external_keys` (criada pela tela): `atualizar TAREFA --descricao "..."`
     (acrescenta), `horas TAREFA --data AAAA-MM-DD --inicio HH:MM --duracao "1h"`
     e, se terminou, `atualizar TAREFA --status closed --lista LISTA`. Título, estimativa,
     datas e prioridade não mudam pela API.
2. **Monte o arquivo de entregas** (JSON, no scratchpad), um item por task:

   ```json
   {"items": [{
     "external_key": "orbit:fulano-de-tal:2026-11-13:central-de-avisos",
     "list_id": "<link ou id da lista>",
     "title": "Monitoramento | Central de avisos com horário por tipo",
     "description": "O que mudou em 2-5 linhas.\n\nCommits:\nabc1234 mensagem",
     "description_mode": "append",
     "assignees": ["me"],
     "priority": "Alta",
     "tags": ["<etiqueta do perfil>"],
     "sprint": "current",
     "estimate": "1h",
     "start_date": "2026-11-13",
     "due_date": "2026-11-13",
     "time_entries": [{"date": "2026-11-13", "start": "09:00", "duration": "1h", "person": "me", "note": ""}],
     "final_status": "closed"
   }]}
   ```

3. **Simule:** `entregar ARQUIVO --simular`. Nada é gravado. Cada item volta
   com `acao` (`created`, `updated` ou `unchanged`) ou com `erro`. Corrija os
   erros (seção 5) e simule de novo.
4. **Confirme o plano** (quando o perfil tiver "Confirmar antes de criar: sim").
   Mostre ao usuário, para cada task, título, lista, etiquetas, horas, status
   final e a ação da simulação, e espere o ok antes de gravar. Agente em
   segundo plano não pergunta: devolve o plano à sessão principal, que
   confirma com o usuário e faz o registro.
5. **Grave:** `entregar ARQUIVO`. O script manda lotes de até 50 e devolve
   `task_id` e `url` de cada item. Um item com erro não impede os outros.
   Repetir a mesma chamada é seguro: o que já foi gravado volta `unchanged`,
   sem duplicar task nem horas.
6. **Confira:** todos com `ok: true` e `horas_total` esperado. Para rever,
   `tarefas --lista LISTA --minhas --encerradas --desde <dia>`.

Entrega de dia fora da sprint atual: vai para a sprint atual, com as datas e o
registro de horas no dia real.

## 5. Erros da API

| Código | O que fazer |
|---|---|
| 401 / `UNAUTHORIZED` | Token ausente, vencido ou revogado: veja Pré-requisitos. |
| `FORBIDDEN_LIST` | Sem acesso à lista: confirme o link com o usuário. |
| `UNKNOWN_TAG` | Use o nome exato de `meta` → `tags`. Não crie etiqueta. |
| `UNKNOWN_STATUS` | Use `closed`, `doing` ou um nome de `meta` → `statuses`. |
| `ESTIMATE_REQUIRED` | Preencha `estimate`. |
| `CLOSE_REQUIRES_TIME` | Mande `time_entries` na mesma entrega ou deixe em `doing`. |
| `FUTURE_TIME` | Início + duração passou de agora: ajuste o início. |
| `SPRINT_NOT_ALLOWED` | Use `"current"`, com datas e horas no dia real. |
| `ASSIGNEE_NOT_MEMBER` | Responsável fora da lista: use um id de `meta` → `members`. |
| `VALIDATION_ERROR` | A mensagem diz o campo (ex.: "Campo desconhecido", "Título obrigatório"). |
| `RATE_LIMITED`, 5xx | O script repete sozinho. Se continuar, pare e tente mais tarde ou use o navegador. |

## 6. Pelo navegador (reserva)

Só quando não houver token ou a API estiver fora do ar.

- Extensão **Claude in Chrome** conectada, com o usuário já logado no Orbit.
  Se o Chrome não estiver conectado ou pedir login, pare e avise. Nunca digite senha.
- Carregue as ferramentas numa chamada só:
  `ToolSearch select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__tabs_create_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__find,mcp__claude-in-chrome__read_page,mcp__claude-in-chrome__javascript_tool,mcp__claude-in-chrome__browser_batch,mcp__claude-in-chrome__get_page_text,mcp__claude-in-chrome__form_input`
- Abra uma aba própria (`tabs_create_mcp`). Não mexa nas abas do usuário.
- Antes de mexer no formulário, leia `references/interface.md` (na pasta desta
  skill): a interface do Orbit tem várias armadilhas com a aba em segundo plano.

1. **Evite duplicar** e **confirme o plano** como nos passos 1 e 4 da seção 4
   (na tela, mostre as encerradas, que ficam escondidas por padrão). Task
   existente: acrescente os commits na descrição e clique em **Concluir**.
2. **Crie em andamento.** A tela não deixa criar já encerrada. Clique em
   **Adicionar tarefa**, confira que o diálogo começa com "Nova tarefa" e
   preencha título, Status `Doing - Em Andamento`, Responsáveis ("Nome no
   Orbit" do perfil), Prioridade, Etiquetas, Sprint, Horas estimadas, Datas e
   Descrição. Leia o texto do diálogo para conferir e clique em **Criar tarefa**.
3. **Registre as horas.** Espere o cabeçalho virar "Detalhes da tarefa". Clique
   em **Iniciar** (Rastrear tempo), confira "Tempo nesta tarefa" (pessoa, duração,
   data do registro = dia real da entrega) e **Salvar** ("Tempo salvo").
   Confira que o campo "Rastrear tempo" mostra as horas (ex.: `1h`), e não "Iniciar".
4. **Encerre.** Mude o Status para `Closed - Encerrada` e clique em
   **Concluir** ("Alterações concluídas"). Entrega ainda em andamento: pule este passo.
5. **Confira.** Encerradas somem da Lista e do Quadro: reabra cada task pela aba
   **Atividade** e confira status, horas, etiquetas e sprint.

## Regras

- Uma task por entrega/funcionalidade, não uma por commit.
- Não mude tasks de outras pessoas sem pedido do usuário.
- Não apague tasks sem ok explícito do usuário (a lixeira leva as horas
  registradas junto). A API não apaga.
- Agente em segundo plano pode ter a gravação bloqueada pelo sistema de
  permissões (sem prompt ao usuário). Se acontecer, pare e avise a sessão
  principal, que faz o registro com aprovação do usuário.
- No fim, responda com a lista do que foi criado/atualizado (`título -> status`).
- Aprendeu algo novo sobre a API ou a interface? Anote em "Notas" no seu perfil
  e avise quem mantém a skill, para entrar na próxima versão.
