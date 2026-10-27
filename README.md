# Plugins OpenExO para o Claude Code

Marketplace do time OpenExO. Hoje tem um plugin, `orbit`, com duas skills:

| Skill | O que faz |
|---|---|
| `orbit:orbit` | Registra uma entrega no Orbit (orbit.openexo.com.br): cria ou atualiza a task na lista do projeto, com etiqueta, sprint, horas e commits, pelo Claude in Chrome. |
| `orbit:dia` | Varre o que você fez desde a última varredura (chats do Claude, commits, PRs, agenda, e-mails enviados, Drive, n8n, Lovable, Supabase), monta o plano de tasks e registra tudo depois do seu ok. |

## Instalar

No terminal:

```bash
claude plugin marketplace add alerrandro-open/openexo-claude-plugins
claude plugin install orbit@openexo
```

Ou dentro de uma sessão do `claude`: `/plugin marketplace add alerrandro-open/openexo-claude-plugins` e depois `/plugin install orbit@openexo`.

Só usa o app Claude (aba Code)? Peça numa sessão para rodar esses dois comandos. Se o comando `claude` não existir no terminal, o Claude pode usar o executável do Claude Code que vem dentro do app.

O plugin passa a valer na próxima sessão. Tinha a skill copiada à mão em `~/.claude/skills/orbit`? Apague essa pasta, senão as duas versões ficam carregadas.

Para usar, é preciso ter a extensão **Claude in Chrome** conectada e estar logado no Orbit.

## Perfil

Cada pessoa tem o próprio perfil em `~/.claude/orbit-perfil.md`: nome como aparece no Orbit, prioridade e horas padrão, se quer confirmar antes de criar e a tabela de listas dos projetos (repo → lista do Orbit → etiquetas). Esse arquivo não é apagado nas atualizações.

As listas não ficam neste repositório, que é público: o time recebe a tabela junto com o prompt de instalação. Sem perfil, a skill pergunta o nome no primeiro uso e cria o arquivo; projeto sem lista no perfil, ela pergunta o link e a etiqueta e grava.

## Varredura do dia

A skill `orbit:dia` foi feita para rodar como tarefa agendada do app Claude (por exemplo, 12h e 18h em dias úteis) com um prompt que comece por `[varredura-orbit]`, a marca que tira a própria varredura da contagem. Ela:

- lê os históricos locais do Claude e o git das "Pastas de projetos" do perfil (script `plugins/orbit/skills/dia/scripts/coletar_dia.py`, só leitura);
- consulta GitHub, Agenda, Gmail (só assunto, destinatário e horário), Drive, n8n, Lovable e Supabase quando os conectores estiverem ligados;
- calcula as horas pelo tempo real de interação, sem contar duas vezes os chats em paralelo;
- mostra o plano e **só registra depois do ok**; o que já foi registrado fica em `~/.claude/orbit-varredura.json` e não se repete.

Para rodar, o app e o Chrome (com o Claude in Chrome) precisam estar abertos. Se o app estiver fechado no horário, a tarefa roda quando ele abrir.

## Atualizar

```bash
claude plugin marketplace update openexo
claude plugin update orbit@openexo
```

Reinicie a sessão do Claude para carregar a versão nova.

## Manutenção

- A skill fica em `plugins/orbit/skills/orbit/`: `SKILL.md` (fluxo e padrões) e `references/interface.md` (receitas da interface do Orbit).
- A cada mudança, suba o `version` em `plugins/orbit/.claude-plugin/plugin.json`. Sem isso a atualização não chega para quem já instalou.
- O repositório é público: nada de nomes de clientes, links de listas ou dados de pessoas aqui. Isso vai no perfil de cada um.
- Descobriu algo novo na interface do Orbit: abra um PR em `references/interface.md` ou anote em "Notas" no seu perfil e avise quem mantém o plugin.
- Antes de publicar: `claude plugin validate .` e `claude plugin validate plugins/orbit`.
