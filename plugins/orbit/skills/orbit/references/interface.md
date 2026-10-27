# Interface do Orbit: o que funciona (testado em out/2026)

Quase todos os problemas vêm da aba do Chrome em segundo plano: animações não
terminam, cliques se perdem e o "Salvando..." trava. As receitas abaixo
contornam isso.

## Caminho que funcionou de ponta a ponta (27/10/2026)

1. `form_input` no título ("Nome da tarefa"), na descrição e em "Horas estimadas".
2. Cada seletor (Status, Prioridade, Responsáveis, Etiquetas, Sprint, Início,
   Vencimento): `find` para achar o botão, clique real por ref, `find` para a
   opção e clique por ref. Depois de cada escolha, desmonte os menus fantasma
   (receita abaixo). Responsáveis e Etiquetas fecham clicando de novo no botão.
3. Leia `document.querySelector('[role=dialog]').innerText` para conferir tudo
   antes de **Criar tarefa**.

## Abrir o diálogo "Nova tarefa"

- Botão **Adicionar tarefa** que não abre o diálogo: clique pelo JS no próprio botão:
  `[...document.querySelectorAll('button')].find(x=>x.innerText.trim()==='Adicionar tarefa' && x.getBoundingClientRect().top<80).click()`
- Antes de preencher, confirme que o diálogo aberto começa com "Nova tarefa".
  Se o detalhe anterior não fechou, o texto vai para a tarefa errada (fica em
  "Alterações pendentes"; recarregue sem Concluir para descartar).

## Preencher campos

- **Título e descrição**: use `form_input`, não digite. Se o diálogo ainda não
  pegou o foco, as teclas vão para os atalhos da lista e o título sai só com os acentos.
- **Status, Prioridade, Sprint** (Radix Select): pelo JS,
  `combo.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,button:0,pointerType:'mouse'}))`
  abre; na opção, `focus()` + keydown Enter escolhe. Eles fecham sozinhos ao escolher.
  Sprints passadas vêm com `aria-disabled` no seletor.
- **Responsáveis, Etiquetas e datas**: pointerdown + click no botão pelo JS e
  `click()` no item dentro do popover aberto (`data-state=open`). Para fechar
  responsáveis/etiquetas, clique de novo no mesmo botão.
- Alternativa confiável para popovers: clique real (`computer left_click` por
  ref) seguido de screenshot.
- Opções pelo texto com `find`: "option Closed - Encerrada", "option Alta", "tag OpenExO".
- **Horas estimadas**: `input[placeholder^="Ex.: 1d"]` (ex.: `1h`). Obrigatório.
- **Calendário**: dias têm aria-label como `segunda-feira, 19 de outubro de 2026`;
  hoje começa com "Today" (`Today, segunda-feira, ...`).
- Etiqueta marcada aparece no popover com `aria-pressed=true`.
- Nomes de pessoas aparecem como estão cadastrados no Orbit (nome e sobrenome).

## Menus "fantasma" (Radix)

Com a aba em segundo plano a animação de fechar dos seletores nunca termina:
o menu fechado continua na tela e come os cliques seguintes ("precisa de dois
cliques"). Depois de escolher cada opção, desmonte os fechados:

```js
for (const w of document.querySelectorAll('[data-radix-popper-content-wrapper]')) {
  const c = w.firstElementChild;
  if (c?.getAttribute('data-state') === 'closed')
    c.dispatchEvent(new AnimationEvent('animationend', { bubbles: true }));
}
```

- Feche menus abertos clicando no rótulo "Descrição". Não use Escape: fecha o diálogo.
- Popovers às vezes não abrem na 1ª tentativa: desmonte os fantasmas, repita e
  localize o aberto pelo texto (`ETAPAS DA LISTA`, `ETIQUETAS`, `Escolha uma data`,
  `Tempo nesta tarefa`).

## Salvar e registrar horas

- "Criar tarefa" pode ficar 10 s+ em "Salvando...". Espere o cabeçalho virar
  "Detalhes da tarefa" antes de clicar em **Iniciar** (o diálogo de criação
  também tem um Iniciar).
- "Salvando..." pode travar até alguém tirar um screenshot: `computer screenshot`
  ou `wait` "acorda" a aba.
- Não use `setTimeout` longo no JS: a aba fica estrangulada e o comando expira.
- O botão **Iniciar** do detalhe tem aria-label "Abrir rastreamento de tempo";
  clicar de novo nele fecha o painel.
- "Tempo nesta tarefa":
  - combobox "Pessoa que realizou a tarefa" (lançar as horas em nome de quem fez);
  - inputs aria-label "Duração" e "Hora de início" (setter nativo + evento input);
    vêm preenchidos com um período que termina no horário atual: confira a
    duração e a data antes de salvar;
  - botão aria-label "Data do registro" abre o calendário para trocar o dia
    (entrega de outro dia).
- O toast "Tempo salvo" de uma tarefa anterior pode ficar na tela e enganar a
  checagem: confira no próprio detalhe. Antes de encerrar, as horas aparecem
  em "Rastrear tempo" (ex.: `1h` no lugar de "Iniciar"); depois de encerrada,
  o campo vira "Horas registradas".

## Editar texto no detalhe

`el.focus()`, setter nativo de `value`, `new InputEvent('input', {bubbles:true})`
e `el.blur()`. Só então o rodapé mostra "Revise e confirme..." e o **Concluir**
grava. Sem o blur a edição se perde em silêncio.

## Fechar o detalhe

- O X (botão com texto/aria-label "Close") fecha sem recarregar.
- Se não fechar no X nem no Escape, recarregue a página.

## Ler a lista

- Conteúdo: a Lista não é tabela (não há `tr`). Leia
  `document.querySelector('main').innerText` linha a linha: cada grupo começa
  pelo cabeçalho (ex.: `CLOSED - ENCERRADA` e a contagem na linha seguinte) e
  cada task vem como nome, etiqueta, data, prioridade e sprint.
- Antes de clicar em "Criar tarefa", leia `document.querySelector('[role=dialog]').innerText`
  e, depois, confirme pela contagem da lista na barra lateral.
- A Lista esconde encerradas: o botão aria-label "Mostre rapidamente tarefas
  fechadas" (ícone de check ao lado de "Mais Períodos") mostra o grupo CLOSED.
- Encerradas somem da Lista e do Quadro: confira pela aba **Atividade**.
- Subtarefas não aparecem na Lista, só dentro da mãe. Subtarefa não se desvincula
  (mover fica desabilitado): para tirá-la, recrie como tarefa solta e mande a
  original para a lixeira, com ok do usuário antes (ela leva as horas junto).
