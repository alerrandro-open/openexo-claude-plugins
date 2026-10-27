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

- Extensão **Claude in Chrome** conectada, com o usuário já logado no Orbit.
  Se o Chrome não estiver conectado ou pedir login, pare e avise. Nunca digite senha.
- Carregue as ferramentas numa chamada só:
  `ToolSearch select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__tabs_create_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__find,mcp__claude-in-chrome__read_page,mcp__claude-in-chrome__javascript_tool,mcp__claude-in-chrome__browser_batch,mcp__claude-in-chrome__get_page_text,mcp__claude-in-chrome__form_input`
- Abra uma aba própria (`tabs_create_mcp`). Não mexa nas abas do usuário.

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

  ## Listas

  | Projeto (repo) | Lista no Orbit | Etiqueta |
  |---|---|---|

  ## Notas
  ```

- Agente em segundo plano: não invente o responsável. Pare e avise a sessão principal.

O responsável é o "Nome no Orbit" do perfil. Outra pessoa (entrega feita em
dupla, registro para um colega) só quando o usuário pedir.

"Confirmar antes de criar" ausente conta como `sim`.

## 2. Lista e etiqueta do projeto

Procure o projeto (repo) na tabela "Listas" do perfil. O time recebe essa
tabela preenchida junto com o prompt de instalação; a skill não traz listas
nem nomes de clientes porque o repositório é público.

Projeto fora da tabela: procure a lista na barra lateral do Orbit (as de
clientes ficam no espaço OpenExO › Projetos Growth), confirme com o usuário o
link e a etiqueta e grave a linha na tabela do perfil. Agente em segundo plano
não adivinha: pare e avise a sessão principal.

Use as etiquetas exatamente como estão na linha do projeto. Algumas linhas
pedem mais de uma (etiqueta do projeto + etiqueta do cliente).

## 3. Padrão de cada task

| Campo | Valor |
|---|---|
| Título | `Área \| O que foi entregue` (ex.: `Monitoramento \| Central de avisos com horário por tipo`) |
| Status | final `Closed - Encerrada` (entregue) ou `Doing - Em Andamento` (em andamento) |
| Responsáveis | "Nome no Orbit" do perfil (outra pessoa só a pedido do usuário) |
| Prioridade | "Prioridade padrão" do perfil (sem perfil: `Alta`) |
| Etiquetas | as da linha do projeto no perfil, exatamente com esse nome |
| Sprint | a sprint atual (aparece em /sprints; só ela aceita tarefa nova) |
| Horas estimadas | obrigatório; "Horas estimadas padrão" do perfil (ex.: `1h`) |
| Datas | Início e Vencimento = dia da entrega |
| Descrição | o que mudou em 2-5 linhas, em português, e a lista de commits (`hash mensagem`) |

Commits: `git log --oneline` no repo, só os daquela entrega.

## 4. Fluxo

Antes de mexer no formulário, leia `references/interface.md` (na pasta desta
skill): a interface do Orbit tem várias armadilhas com a aba em segundo plano.

1. **Evite duplicar.** Leia a lista (incluindo as encerradas, que ficam
   escondidas por padrão) e veja se já existe task com o mesmo assunto. Se
   existir, não crie outra: acrescente os commits na descrição e clique em
   **Concluir**. Se ela estiver em `Doing - Em Andamento` e a entrega terminou,
   faça também os passos 4 e 5 nela.
2. **Confirme o plano** (quando o perfil tiver "Confirmar antes de criar: sim").
   Mostre ao usuário, para cada task, título, lista, etiquetas, sprint, horas,
   status final e se é nova ou atualização, e espere o ok antes de gravar.
   Agente em segundo plano não pergunta: devolve esse plano à sessão principal,
   que confirma com o usuário e faz o registro.
3. **Crie em andamento.** O Orbit não deixa criar já encerrada. Clique em
   **Adicionar tarefa**, confira que o diálogo começa com "Nova tarefa" e
   preencha título, Status `Doing - Em Andamento`, Responsáveis, Prioridade,
   Etiquetas, Sprint, Horas estimadas, Datas e Descrição. Leia o texto do
   diálogo para conferir e clique em **Criar tarefa**.
4. **Registre as horas.** Espere o cabeçalho virar "Detalhes da tarefa". Clique
   em **Iniciar** (Rastrear tempo), confira "Tempo nesta tarefa" (pessoa, duração,
   data do registro = dia real da entrega) e **Salvar** ("Tempo salvo").
   Confira que o campo "Rastrear tempo" mostra as horas (ex.: `1h`), e não "Iniciar".
5. **Encerre.** Mude o Status para `Closed - Encerrada` e clique em
   **Concluir** ("Alterações concluídas"). Entrega ainda em andamento: pule este passo.
6. **Confira.** Encerradas somem da Lista e do Quadro: reabra cada task pela aba
   **Atividade** e confira status, horas, etiquetas e sprint.

Entrega de dia fora da sprint atual: vai para a sprint atual, com as datas e o
registro de horas no dia real.

## Regras

- Uma task por entrega/funcionalidade, não uma por commit.
- Não mude tasks de outras pessoas sem pedido do usuário.
- Não apague tasks sem ok explícito do usuário (a lixeira leva as horas registradas junto).
- Agente em segundo plano pode ter o clique de gravação bloqueado pelo sistema
  de permissões (sem prompt ao usuário). Se acontecer, pare, deixe o formulário
  como está e avise a sessão principal, que faz o registro com aprovação do usuário.
- No fim, responda com a lista do que foi criado/atualizado (`título -> status`).
- Aprendeu algo novo sobre a interface? Anote em "Notas" no seu perfil e avise
  quem mantém a skill, para entrar na próxima versão.
