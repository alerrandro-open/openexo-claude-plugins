# Plugins OpenExO para o Claude Code

Marketplace do time OpenExO. Hoje tem um plugin, `orbit`, com duas skills:

| Skill | O que faz |
|---|---|
| `orbit:orbit` | Registra uma entrega no Orbit (orbit.openexo.com.br): cria ou atualiza a task na lista do projeto, com etiqueta, sprint, horas e commits, pela API do Orbit (o Claude in Chrome fica de reserva). |
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

## Token da API

Desde a versão 1.3.0 o registro é feito pela API do Orbit, com um token pessoal:

1. No Orbit, abra Configurações > Perfil · Tokens de API e crie um token (ele aparece uma vez só).
2. Guarde o token no cofre do sistema. O comando pede o token: cole e tecle Enter.
   - **macOS**, no Terminal (Keychain):

     ```bash
     security add-generic-password -U -a "$USER" -s orbit-api-token -w
     ```

   - **Windows**, no PowerShell ou no Prompt de Comando (Gerenciador de Credenciais):

     ```bash
     cmdkey /generic:orbit-api-token /user:orbit /pass
     ```

Em outros sistemas, use a variável de ambiente `ORBIT_API_TOKEN`.

**Windows:** os scripts do plugin usam Python 3, que não vem instalado. Instale uma vez (`winget install Python.Python.3.12`, ou pelo python.org marcando "Add python.exe to PATH") e abra uma sessão nova do Claude. O token é uma credencial: não cole no chat nem em arquivos. Para conferir, peça numa sessão "confere meu token do Orbit" (a skill roda `orbit_api.py token`).

Sem token, a skill registra pelo navegador: é preciso ter a extensão **Claude in Chrome** conectada e estar logado no Orbit.

## Perfil

Cada pessoa tem o próprio perfil em `~/.claude/orbit-perfil.md`: nome como aparece no Orbit, prioridade e horas padrão, se quer confirmar antes de criar e a tabela de listas dos projetos (repo → lista do Orbit → etiquetas). Esse arquivo não é apagado nas atualizações.

As listas não ficam neste repositório, que é público: o time recebe a tabela junto com o prompt de instalação. Sem perfil, a skill pergunta o nome no primeiro uso e cria o arquivo; projeto sem lista no perfil, ela pergunta o link e a etiqueta e grava.

## Varredura do dia

A skill `orbit:dia` foi feita para rodar como tarefa agendada do app Claude (por exemplo, 12h e 18h em dias úteis) com um prompt que comece por `[varredura-orbit]`, a marca que tira a própria varredura da contagem. Ela:

- lê os históricos locais do Claude e o git das "Pastas de projetos" do perfil (script `plugins/orbit/skills/dia/scripts/coletar_dia.py`, só leitura);
- consulta GitHub, Agenda, Gmail (só assunto, destinatário e horário), Drive, n8n, Lovable e Supabase quando os conectores estiverem ligados;
- calcula as horas pelo tempo real de interação, sem contar duas vezes os chats em paralelo;
- simula o registro na API (sem gravar), mostra o plano e **só registra depois do ok**; o que já foi registrado fica em `~/.claude/orbit-varredura.json` e não se repete.

Para rodar, o app precisa estar aberto (o Chrome com o Claude in Chrome, só se não houver token). Se o app estiver fechado no horário, a tarefa roda quando ele abrir.

### O que fica fora do Orbit

Nem toda sessão é trabalho para registrar. Para deixar algo de fora:

- **Uma sessão:** comece uma mensagem com `[sem-orbit]`, a qualquer momento da sessão. A varredura tira a sessão inteira, e os commits feitos no mesmo repo durante ela também ficam de fora.
- **Um projeto inteiro:** acrescente o nome do repositório ou da pasta na linha `- Ignorar:` do seu perfil (`~/.claude/orbit-perfil.md`), separado por vírgula. Por exemplo: `- Ignorar: projeto-pessoal, outro-repo`. Essas sessões e commits nem entram no plano.
- **Um item do plano:** responda "tira o 3". Ele fica marcado como ignorado e não volta.

No fim do plano, a varredura mostra numa linha o que ficou de fora e por quê, para você conferir.

## Registro de atividade (opcional)

Para a varredura enxergar o trabalho que não passa pelo Claude nem pelo git (planilhas, Gerenciador de Anúncios, Clinic, Manager), cada pessoa pode ligar um registro de atividade no próprio computador:

- A cada 30 segundos ele grava **qual programa e qual janela estão em primeiro plano** e se a pessoa está parada há mais de 5 minutos.
- **Não tira print, não lê o teclado nem o conteúdo das janelas.**
- Os registros ficam só no computador, em `~/.claude/orbit-atividade/`, e são apagados depois de 35 dias.
- A varredura mostra o resumo (minutos por programa e por janela) no plano. Nada vai para o Orbit sem o ok da pessoa, e os títulos de janela não são copiados para as tasks.

Comandos, a partir da pasta do plugin (`skills/dia/scripts/atividade.py`) ou pedindo numa sessão do Claude:

| Comando | O que faz |
|---|---|
| `python3 atividade.py amostra` | Mostra o que seria gravado agora, sem gravar |
| `python3 atividade.py instalar` | Liga: começa a gravar e passa a iniciar sozinho no login (Windows: pasta Inicializar; macOS: LaunchAgent) |
| `python3 atividade.py pausar 60` | Para de gravar por 60 minutos (`pausar 0` retoma) |
| `python3 atividade.py status` | Diz se está gravando, se está pausado e desde quando há registros |
| `python3 atividade.py desinstalar` | Desliga (acrescente `--apagar-registros` para apagar o que foi gravado) |

No Windows use `python` (ou `py`) no lugar de `python3`. No macOS, o título da janela só aparece com a permissão de Acessibilidade; sem ela, fica só o nome do programa.

**Antes de ligar numa equipe:** avise por escrito o que é registrado, para quê e quem vê. No Windows o sistema não mostra nenhum aviso de que o registro está ligado. Para prestadores PJ, confira antes com o jurídico.

## Atualizar

```bash
claude plugin marketplace update openexo
claude plugin update orbit@openexo
```

Reinicie a sessão do Claude para carregar a versão nova.

## Manutenção

- A skill fica em `plugins/orbit/skills/orbit/`: `SKILL.md` (fluxo e padrões), `scripts/orbit_api.py` (cliente da API, só biblioteca padrão do Python) e `references/interface.md` (receitas da interface do Orbit, para o registro pelo navegador).
- A cada mudança, suba o `version` em `plugins/orbit/.claude-plugin/plugin.json`. Sem isso a atualização não chega para quem já instalou.
- O repositório é público: nada de nomes de clientes, links de listas ou dados de pessoas aqui. Isso vai no perfil de cada um.
- Descobriu algo novo na interface do Orbit: abra um PR em `references/interface.md` ou anote em "Notas" no seu perfil e avise quem mantém o plugin.
- Antes de publicar: `claude plugin validate .` e `claude plugin validate plugins/orbit`.
