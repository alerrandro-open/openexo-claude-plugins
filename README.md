# Plugins OpenExO para o Claude Code

Marketplace do time OpenExO. Hoje tem um plugin:

| Plugin | O que faz |
|---|---|
| `orbit` | Registra entregas no Orbit (orbit.openexo.com.br): cria ou atualiza a task na lista do projeto, com etiqueta, sprint, horas e commits, pelo Claude in Chrome. |

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
