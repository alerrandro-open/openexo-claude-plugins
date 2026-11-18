---
name: dia
description: Varre tudo o que a pessoa fez desde a última varredura (chats do Claude, commits, PRs, agenda, e-mails enviados, Drive, n8n, Lovable, Supabase), monta o plano de tasks do Orbit e registra depois do ok. Use na tarefa agendada (12h e 18h) ou quando pedirem para registrar o dia no Orbit.
---

# Varredura do dia no Orbit

Junta o trabalho da pessoa desde a última varredura e registra no Orbit. O
registro em si segue a skill `orbit` deste plugin (perfil, listas, padrão de
task, chave da entrega e a API): leia `../orbit/SKILL.md` antes de montar o
plano. O cliente da API é `../orbit/scripts/orbit_api.py`, chamado aqui de
`orbit_api.py`. Confira o token logo no início (`orbit_api.py token`). Sem
token, avise no plano e registre pelo navegador, seguindo a seção 6 da skill
`orbit` e `../orbit/references/interface.md`.

**Sempre mostre o plano e espere o ok**, mesmo que o perfil diga "Confirmar
antes de criar: não". Até o ok, tudo é só leitura.

## 1. Coletar

### Chats do Claude e commits (script)

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/coletar_dia.py" coletar
```

(`${CLAUDE_SKILL_DIR}` é a pasta desta skill; se aparecer vazio, use a pasta-base informada quando a skill foi carregada.) O script lê os históricos
locais do Claude e o git e devolve JSON com:

- `desde`/`ate`: a janela (da última varredura até agora; na primeira vez,
  desde 00:00 de hoje; no máximo 3 dias, com `aviso` quando cortar);
- `sessoes`: um item por chat com atividade na janela (título, repo, branch,
  pedido inicial, relatório final, `minutos_ativos`, `minutos_proporcionais`,
  `ja_registrado`);
- `commits`: commits da pessoa em todos os repos (inclusive os feitos fora
  do Claude), com `ja_registrado`;
- `minutos_reais_no_claude`: tempo real de interação no dia, sem contar duas
  vezes os chats em paralelo.

Sessões da própria varredura (marca `[varredura-orbit]`) já vêm excluídas.

### Outras fontes (conectores)

Use as que estiverem disponíveis; sem o conector, pule e diga no plano.
Carregue as ferramentas com `ToolSearch` pelas palavras-chave indicadas. Os
nomes mudam de pessoa para pessoa.

| Fonte | Como | O que aproveitar |
|---|---|---|
| GitHub | `gh search prs --author=@me --updated=">=AAAA-MM-DD" --json repository,number,title,state,url,updatedAt` e o mesmo com `--reviewed-by=@me` | PRs abertos, mergeados e revisados |
| Google Agenda | ToolSearch "calendar list events": eventos da janela (horário local, sem offset) | reuniões em que a pessoa não recusou; pule dia inteiro e ausências |
| Gmail | ToolSearch "gmail search threads": `in:sent after:AAAA/MM/DD before:AAAA/MM/DD`, `view` METADATA_ONLY ou MINIMAL | só assunto, destinatário e horário; nunca abra o corpo |
| Google Drive | ToolSearch "drive recent files": `orderBy: lastModifiedByMe`, `excludeContentSnippets: true` | pare no primeiro arquivo com `modifiedTime` anterior à janela; só nome e horário |
| n8n | ToolSearch "n8n search workflows" | workflows alterados ou publicados na janela |
| Lovable | ToolSearch "lovable list projects" e "list edits" | edições/publicações na janela |
| Supabase | ToolSearch "supabase list migrations" nos projetos do perfil | migrations com versão (AAAAMMDDHHMMSS) dentro da janela |

n8n, Lovable e Supabase servem para achar trabalho que nenhum chat ou commit
explica; o que já aparece num chat entra só como detalhe da entrega.

Itens que não vêm do script também ficam no estado. Leia
`~/.claude/orbit-varredura.json` (`registradas`) e trate como já registrado
quem tiver a chave lá: `agenda:<id do evento>`, `email:<id da conversa>`,
`drive:<id do arquivo>`, `pr:<repo>#<número>`, `n8n:<id>`, `lovable:<id>`,
`supabase:<projeto>:<versão>`.

## 2. Montar as entregas

Tudo o que aconteceu na janela entra em alguma task:

- **Uma task por entrega**, não por chat. Junte chats do mesmo assunto, os
  que nasceram um do outro (o pedido inicial ou o relatório costuma citar) e
  os do mesmo PR. Commits, PRs, migrations e publicações vão para a entrega
  do assunto.
- **Reunião** vira `Reunião | <assunto>` (ou entra na entrega do assunto),
  com a duração do evento como horas.
- **E-mails e documentos** entram na entrega do assunto. Sem assunto
  correspondente: `Comunicação | E-mails do dia` ou `Documento | <nome>`.
- **Chats curtos** (perguntas, conferências rápidas) que não formam entrega:
  uma task por lista, `Atendimento | Análises e dúvidas do dia (DD/MM)`.
- **Já registrado** (`ja_registrado` ou chave no estado): não crie outra;
  planeje atualizar a task existente (acrescentar commits e o que mudou e
  lançar as horas novas). O estado traz o `id` e a `external_key` da task
  quando ela foi gravada pela API. Com `external_key`, a atualização é a mesma
  entrega com a mesma chave. Sem ela, use `atualizar` e `horas` (skill
  `orbit`, seção 4, passo 1).
- **Lista e etiquetas:** pela tabela "Listas" do perfil, a partir do repo.
  Repo ou assunto sem lista: junte numa pergunta só no plano (link da lista
  e etiqueta) e grave as respostas no perfil.
- **Status:** `Closed - Encerrada` quando o relatório diz que terminou (PR
  mergeado, publicado, respondido). `Doing - Em Andamento` quando ficou
  pendente (PR aberto, aguardando deploy, investigação sem conclusão); a
  próxima varredura atualiza.
- **Horas:** some os `minutos_proporcionais` dos chats da entrega (mais a
  duração das reuniões) e arredonde para 0,5h, mínimo 0,5h. Trabalho visto só
  por commit, sem chat: 0,5h, marcado "estimativa".
- **Datas:** o dia em que o trabalho aconteceu.
- **Início das horas:** a hora real em que começou (o `inicio` do primeiro
  chat da entrega ou o início da reunião). Início + duração não pode passar
  de agora; se passar, antecipe o início.
- **Chave:** cada entrega nova ganha uma `external_key` no padrão da skill
  `orbit` (`orbit:<pessoa>:<AAAA-MM-DD>:<assunto>`).
- **Descrição:** 2-5 linhas em português do que mudou, a partir do
  relatório final, e a lista de commits (`hash mensagem`) e PRs. Não copie a
  conversa, nem tokens, senhas, telefones, CPF ou dados de pacientes/clientes
  finais.

## 3. Simular, mostrar o plano e esperar o ok

Monte o arquivo de entregas (formato da skill `orbit`, seção 4) com as
entregas novas e as atualizações que têm `external_key`, e simule:

```bash
python3 "${CLAUDE_SKILL_DIR}/../orbit/scripts/orbit_api.py" entregar <arquivo> --simular
```

Nada é gravado. Corrija o que voltar com erro (etiqueta, status, horas no
futuro...) antes de mostrar o plano; o que depender do usuário vai como
pergunta. Atualizações de tasks sem `external_key` também podem ser
simuladas: `atualizar ... --simular` e `horas ... --simular`.

Mostre uma tabela, na ordem em que vai registrar:

| # | Task | Lista · etiquetas | Status | Horas | Simulação | Origem |
|---|---|---|---|---|---|---|

Na coluna Simulação, use o resultado: nova (`created`), atualiza
(`updated`), sem mudança (`unchanged`) ou o erro que sobrou. Na coluna
Origem, cite os chats (título), commits e PRs de cada task.
Depois da tabela, mostre:

- tempo real no Claude (`minutos_reais_no_claude`) e total de horas do plano;
- fontes puladas (sem conector) e listas que faltam no perfil;
- o pedido: "Responda **ok** para registrar, ou diga o que mudar (juntar,
  separar, tirar, horas, lista)."

Rodando agendada, ninguém está olhando: deixe o plano e espere a resposta
no próprio chat. Não registre nada sem o ok, nem por tempo esgotado.

Ajustes do usuário: refaça a tabela e peça o ok de novo. Itens que ele mandar
tirar: marque como ignorados (passo 4) para não voltarem.

## 4. Registrar e guardar o estado

Com o ok, grave o mesmo arquivo de uma vez (já com os ajustes pedidos):

```bash
python3 "${CLAUDE_SKILL_DIR}/../orbit/scripts/orbit_api.py" entregar <arquivo>
```

As atualizações sem `external_key` vão por `atualizar` e `horas`. Repetir a
gravação é seguro: o que já foi gravado volta `unchanged`. Sem token, siga o
navegador (skill `orbit`, seção 6). Logo depois, marque as chaves que cada
task cobriu, com o `task_id` e a `external_key` que a gravação devolveu:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/coletar_dia.py" marcar --task "Título da task" --lista "URL da lista" --id <task_id> --chave-externa <external_key> sessao:... commit:... agenda:...
```

Itens ignorados: `marcar --task "(ignorado)" <chaves>`.

No fim, com tudo registrado, feche a janela com o `ate` da coleta:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/coletar_dia.py" concluir --ate "<ate da coleta>"
```

Se parar no meio (API fora do ar, Chrome caiu, erro no Orbit), não rode
`concluir`: o que já foi marcado não se repete na próxima varredura e o resto
volta para o plano.

Responda com a lista `título -> status (horas)`, o que ficou pendente e as
listas novas gravadas no perfil.

## Regras

- Só leitura em chats, e-mail, agenda, Drive, n8n, Lovable e Supabase: não
  envie mensagens, não arquive chats, não altere nada fora do Orbit.
- Só o trabalho de quem está usando (histórico local e conta própria nos
  conectores).
- Não use histórico do navegador nem nada fora das fontes acima.
- Não apague tasks; não mude tasks de outras pessoas.
