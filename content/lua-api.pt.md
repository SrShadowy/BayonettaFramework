# Guia de Criação de Scripts em Lua (Bayonetta Trainer V2)

Este documento serve como referência para criar e modificar scripts Lua para o Bayonetta Trainer V2. O sistema de script permite interagir com a memória do jogo de forma segura e fácil através de uma API em C++ exportada para Lua.

## Índice

1. [Estrutura Básica de um Script](#1-estrutura-básica-de-um-script)
2. [Modelo enxuto: hooks `on_enable`/`on_disable`](#2-modelo-enxuto-on_enable--on_disable)
3. [Manifesto do Script (auto-descrição)](#3-manifesto-do-script-auto-descrição)
4. [Referência da API por tópico](#4-referência-da-api-por-tópico)
   — [Estado e argumentos](#41-estado-da-feature-e-argumentos-da-ui) · [Logs, watch e erros](#42-logs-observação-e-erros) · [Memória: patch](#43-memória--patch-de-bytes) · [leitura/escrita](#44-memória--leitura-e-escrita-direta) · [ponteiros](#45-memória--cadeia-de-ponteiros) · [freeze](#46-memória--congelamento-freeze) · [alocação](#47-memória--alocação-code-caves) · [Input: turbo](#48-input--turbo--autofire) · [spin do analógico](#49-input--spin-do-analógico) · [giro do mouse](#410-input--giro-do-mouse) · [tokens aceitos](#411-tokens-de-input-aceitos-e-observações)
5. [Helpers do prelude (`_lib.lua`)](#5-helpers-do-prelude-_liblua)
6. [Dicas Importantes](#6-dicas-importantes)

---

## 1. Estrutura Básica de um Script

Os scripts ficam localizados na pasta `scripts/` e devem possuir a extensão `.lua`. **A pasta `scripts/` é a fonte de verdade**: todo `.lua` colocado nela é descoberto automaticamente pelo backend — não é preciso registrá-lo em nenhum `.ini`. O nome do arquivo (sem a extensão) é o nome da feature. A seção `[Features]` do `trainer.ini` serve apenas para definir o estado inicial (ligado/desligado) e é opcional.

Um script típico de ativação/desativação (toggle) no estilo "corpo" tem o seguinte formato:

```lua
local on = get_state("NomeDaFeature") == 0
set_state("NomeDaFeature", on and 1 or 0)

if on then
    -- Código para ativar o mod (ex: injetar bytes, nop, etc)
    log_info("Feature ON")
else
    -- Código para desativar o mod (ex: restaurar memória)
    log_info("Feature OFF")
end
```

## 2. Modelo enxuto: `on_enable()` / `on_disable()`

Em vez do estilo acima (corpo que reexecuta e ramifica no `get_state`), um script pode só declarar dois hooks: a **engine gerencia o estado da feature e chama o hook certo**. Um mod toggle vira ~5 linhas:

```lua
function manifest() return { label = "Infinite Jump", category = "PLAYER", control = "toggle" } end

function on_enable()  write_memory("func_InfJump", 0, { 0xEB }) end
function on_disable() restore_memory("func_InfJump") end
```

Como funciona:

* Se o script define `on_enable` e/ou `on_disable`, a engine inverte o estado a cada execução e chama o hook correspondente. Você **não** chama `get_state`/`set_state`.
* A global **`FEATURE_NAME`** é injetada pela engine a cada execução com o nome do script — use-a em vez de hardcodar a string (renomear o arquivo não quebra mais nada).
* Compatível para trás: scripts no estilo corpo (sem hooks) continuam funcionando exatamente como antes.

## 3. Manifesto do Script (auto-descrição)

Um script pode expor uma função `manifest()`. O backend a chama numa passada isolada durante a descoberta e usa o resultado para montar a UI automaticamente — controle certo, categoria, hotkey e campos de input, sem editar `.ini` nem código Python.

```lua
function manifest()
    return {
        label    = "God Mode",   -- texto exibido na UI
        category = "PLAYER",     -- agrupamento na UI
        control  = "toggle",     -- toggle | value | freeze | action | turbo | spin
        hotkey   = "ALT+G",      -- opcional; vira o atalho default ([Hotkeys] do trainer.ini sobrescreve)
        description = "Ignora dano recebido",  -- tooltip na UI
        args = {                 -- campos de input renderizados na UI
            { name = "value", type = "float", min = 0, max = 9999, step = 10, default = 100 }
        }
    }
end
```

Regras e observações:

* Todos os campos são opcionais. Sem `manifest()`, o script aparece como `toggle` na categoria `GENERAL` com o nome do arquivo como label.
* Mapeamento `control → widget` na UI: `toggle` → botão ON/OFF, `value` → campos + SET, `freeze` → campos + FREEZE, `action` → botão simples, `turbo` → campos + botão TURBO, `spin` → campos + botão SPIN.
* `args[].type` aceita `int`, `float`, `bool` e `string`; `min`/`max`/`step`/`default` configuram o widget. O transporte é **tipado de ponta a ponta**: o backend converte cada argumento conforme o `type` do manifesto e `get_arg(name)` devolve o valor no tipo certo (int/float/bool/string). Um `1.5` chega até a memória sem perda.

### Assinaturas AOB no próprio script (pacote autocontido)

O manifesto pode declarar suas próprias assinaturas em `signatures`, resolvidas para o `AddressRegistry` logo após a descoberta. Assim um mod vira uma unidade autossuficiente — não precisa editar o `address.ini` global.

```lua
function manifest()
    return {
        label = "Meu Mod",
        signatures = {
            -- forma curta: só o padrão AOB (mesma sintaxe do address.ini)
            func_MinhaFeature = "89 8F A0 00 00 00",
            -- forma longa: padrão + offset de dereference após o match
            addr_Base = { pattern = "A1 ? ? ? ? 8B", offset = 1 }
        }
    }
end
```

Regras:

* A sintaxe do `pattern` é idêntica à do `address.ini` (bytes hex + `?` wildcards). `offset` é opcional (default `0` = usa o endereço do match).
* **O `address.ini` tem precedência.** Se o nome do símbolo já existir no `address.ini` (ou em outro script já carregado), a assinatura do script é **ignorada** e logada — evita que um script de terceiro sequestre um símbolo compartilhado. Portanto, dê nomes únicos aos símbolos do seu script.
* Assinaturas que não batem falham "soft" (só log, sem popup) — o mod simplesmente não funciona, mas o trainer não trava.
* Combine com `alloc_memory` para pacotes que criam a própria memória (ex.: code caves) sem depender de nada externo.
* A sonda de manifesto roda num ambiente restrito: apenas as libs `base`, `string`, `table`, `math` e `utf8` (sem `os`, `io`, `dofile`, `loadfile`), e todas as funções de memória são no-ops. O **corpo inteiro** do script é executado nessa sonda, portanto mantenha o topo do arquivo livre de efeitos colaterais — apenas defina `manifest()` e a lógica do mod.
* O manifesto é cacheado na descoberta; use o comando `reload` (ou reinicie) após editar.

---

## 4. Referência da API por tópico

Funções globais expostas pelo motor (`LuaEngine`), agrupadas por assunto. Os parâmetros `symbol` sempre se referem às chaves definidas no `address.ini` (ou registradas por `signatures`/`alloc_memory`).

### 4.1 Estado da feature e argumentos da UI

* `get_state(key)` — Retorna o estado atual (inteiro) de uma chave (ex: `1` para ativado, `0` para desativado).
* `set_state(key, value)` — Define o estado de uma chave para o valor especificado.
* `get_arg(name)` — Obtém o valor de um argumento passado pelo backend, **no tipo declarado** no manifesto (int/float/bool/string). Devolve `0` para argumento ausente (ex.: acionamento via hotkey).

### 4.2 Logs, observação e erros

* `log_info(msg)` — Imprime uma mensagem informativa no console/log do trainer.
* `log_fail(msg)` — Imprime uma mensagem de erro no console/log do trainer.

**Nota sobre o índice.** Além dos tópicos 4.1–4.11 há a seção **4.12 (Arquivos e segurança do runtime)** ao final da referência.
* `watch_value(name, value)` — Publica um valor vivo para a UI (ex.: HP atual, valor congelado). Empurra a mensagem `watch_update` para o cliente conectado com `{feature, name, value}`, amarrada automaticamente ao script em execução. Aceita number, string, bool ou nil (convertido para texto).
  *Exemplo:* `watch_value("hp", read_int("addr_HP", 0))`
* `report_error(message, line?, details?)` — Reporta um erro estruturado à UI (mensagem `script_error` com `{feature, message, line, details}`), em vez de só logar em arquivo. Útil para dar feedback imediato a quem escreve o script.
  *Exemplo:* `report_error("Ponteiro base nulo", 12, "addr_Base não resolvido")`

### 4.3 Memória — patch de bytes

* `write_memory(symbol, offset, {byte1, byte2, ...})`
  Escreve um array de bytes no endereço resolvido pelo `symbol` somado ao `offset`. Faz backup automático dos bytes originais na primeira vez que é chamado.
  *Exemplo:* `write_memory("func_DmgCombat", 0, { 0xEB })`

* `nop_memory(symbol, offset, count)`
  Preenche `count` bytes com a instrução `NOP` (`0x90`) no endereço especificado. Faz backup automático dos bytes originais.
  *Exemplo:* `nop_memory("func_FireDemage", 0, 2)`

* `restore_memory(symbol)`
  Restaura os bytes originais de um `symbol` modificado por `write_memory`/`nop_memory`. Restaura **todas** as regiões que aquele símbolo modificou numa única chamada.

### 4.4 Memória — leitura e escrita direta

* `read_int(symbol, offset)` / `read_float(symbol, offset)` — Lê um valor inteiro ou float do endereço resolvido.
* `write_int(symbol, offset, value)` / `write_float(symbol, offset, value)` — Escreve um valor inteiro ou float diretamente na memória.

### 4.5 Memória — cadeia de ponteiros

* `write_on_pointer_int(symbol, {offset1, offset2, ...}, value)` — Resolve uma cadeia de ponteiros a partir do `symbol` e escreve o inteiro `value` no destino final.
* `write_on_pointer_float(symbol, {offset1, offset2, ...}, value)` — Idem para **float**. Aceita valores fracionários (ex: `1.5`).

**Regra da cadeia de ponteiros (importante).** A resolução de offsets é a **mesma** para `write_on_pointer_*` e `frozen_memory`, no estilo do Cheat Engine:

* `{}` (tabela vazia) → usa o **próprio endereço do símbolo**, sem dereference.
* `{o1, o2, ..., on}` → resolve `[ ... [[símbolo] + o1] ... + o(n-1) ] + on`. Lê o ponteiro no símbolo, soma cada offset dereferenciando a cada passo, e o **último** offset é apenas somado (não dereferenciado).

Se algum ponteiro da cadeia for inválido, a operação é abortada com um `[FAIL]` no log — **sem derrubar o jogo**.

### 4.6 Memória — congelamento (freeze)

Útil para valores que o jogo atualiza constantemente (ex: vida, mana). O trainer cria uma thread em background que reescreve os bytes continuamente.

* `frozen_memory(symbol, {offsets}, {byte1, byte2, ...})`
  Congela os bytes especificados no endereço final (mesma regra de cadeia da seção 4.5). Sem offsets, passe `{}`. Chamar novamente sobre um símbolo já congelado **atualiza** o valor congelado.
  *Exemplo:* `frozen_memory("addr_WitcherPower", {}, {0x00, 0x00, 0x80, 0x3F})`

* `unfrozen_memory(symbol)` — Para de congelar a memória do `symbol` especificado.

### 4.7 Memória — alocação (code caves)

* `alloc_memory(symbol, size)` → endereço (inteiro)
  Aloca `size` bytes de memória **executável** (RWX, ideal para code caves) o mais próximo possível do módulo do jogo, zera o bloco e **registra o endereço sob `symbol`** — a partir daí `symbol` é usado como qualquer símbolo de AOB (`write_memory`, `frozen_memory`, etc.). Chamar de novo com o mesmo `symbol` reaproveita o bloco existente. Retorna `0` em caso de falha.
  *Exemplo:* `local cave = alloc_memory("cave_MyHook", 64)`

* `free_memory(symbol)`
  Libera um bloco criado por `alloc_memory` e remove o `symbol` do registro. **Não é obrigatório chamar:** a engine libera automaticamente todas as alocações no shutdown/reload, mas liberar manualmente é boa prática ao desligar uma feature.

### 4.8 Input — turbo / autofire

Repetição automática de botões — teclado, mouse e controle (XInput) — com suporte a combos de vários alvos ao mesmo tempo e gatilho configurável. Só existe **um** turbo ativo por vez (o último `turbo_start` vale) e a injeção só acontece com o jogo em primeiro plano. O script de referência, com todos os campos expostos na UI, é o `scripts/Turbo.lua`.

* `turbo_start(config)` → `true`/`false`
  Ativa o turbo. `config` é uma tabela com campos **todos opcionais** — campo ausente/vazio/`<= 0` reaproveita o valor da última configuração usada (é assim que a hotkey religa o turbo sem enviar args):

```lua
turbo_start({
    target   = "W+SPACE+E+LMB+RMB", -- um ou vários alvos separados por + (ou ,)
    trigger  = "MOUSE4",            -- tecla que o jogador SEGURA para disparar (vazio = primeiro alvo)
    press_ms = 30,                  -- tempo SEGURANDO os botões, em ms (mín. 10, máx. 2000)
    gap_ms   = 30,                  -- tempo SOLTO entre apertos, em ms (mín. 10, máx. 2000)
    mode     = "hold",              -- "hold" (repete enquanto segura o gatilho) | "auto" (contínuo até desligar)
})
```

  Forma posicional também aceita: `turbo_start(targets, interval_ms, mode, trigger)` — o `interval_ms` (ciclo completo) vira `press_ms`/`gap_ms` metade a metade. Na tabela, `interval_ms` também funciona como atalho para quem não precisa de tempos assimétricos.

* `turbo_stop()` — Desativa o turbo e solta qualquer tecla sintética pendente.

### 4.9 Input — spin do analógico

* `stick_spin_start(opções)` → `true`/`false`
  Gira um analógico do controle em círculo enquanto um combo estiver segurado (requer o mesmo hook de XInput do turbo). O gatilho aceita controle (`PAD_*`), **teclado e mouse**, misturados — teclado/mouse são lidos via `GetAsyncKeyState` (estado físico global). Campo vazio/0 reaproveita a última config usada (útil para hotkey).

```lua
stick_spin_start({
    stick     = "LS",             -- "LS" (esquerdo) | "RS" (direito)
    direction = "left",           -- "left" (anti-horário) | "right" (horário)
    period_ms = 400,              -- ms por volta completa (100–5000)
    trigger   = "PAD_R3+PAD_A",   -- combo segurado junto (tb.: "MOUSE4", "SHIFT+RMB")
    consume   = true,             -- o jogo não vê os botões PAD_* do gatilho enquanto gira
})
```

  Forma posicional: `stick_spin_start(stick, direction, period_ms, trigger)`.

* `stick_spin_stop()` — Desliga o giro; o stick volta ao controle físico.

### 4.10 Input — giro do mouse

* `mouse_spin_start(opções)` → `true`/`false`
  Move o **mouse** em círculos (deltas relativos via `SendInput`, como girar o mouse na mesa) enquanto o gatilho estiver segurado. Não depende do hook de XInput. Gatilho aceita controle/teclado/mouse; campo vazio/0 reaproveita a última config.

```lua
mouse_spin_start({
    direction = "left",    -- "left" (anti-horário) | "right" (horário)
    period_ms = 400,       -- ms por volta completa (100–5000)
    radius    = 120,       -- raio do círculo em pixels (10–2000)
    trigger   = "MOUSE4",  -- combo segurado (tb.: "SHIFT+RMB", "PAD_R3")
})
```

  Forma posicional: `mouse_spin_start(direction, period_ms, radius, trigger)`.

* `mouse_spin_stop()` — Desliga o giro do mouse.

### 4.11 Tokens de input aceitos e observações

**Alvos e gatilhos aceitos** (maiúsculas/minúsculas e espaços internos são ignorados — `"mouse 4"` = `MOUSE4`):

| Tipo | Tokens |
|---|---|
| Teclado | `A`–`Z`, `0`–`9`, `F1`–`F24`, `SPACE`, `ENTER`, `TAB`, `SHIFT`, `CTRL`, `ALT`, `UP`/`DOWN`/`LEFT`/`RIGHT`, `BACKSPACE`, `DELETE`, `INSERT`, `HOME`, `END`, `PGUP`, `PGDN`, `NUM0`–`NUM9`, `PLUS`, `MINUS`, `COMMA`, `PERIOD` |
| Mouse | `LMB`, `RMB`, `MMB`, `MOUSE4`, `MOUSE5` (botões laterais) |
| Controle (XInput) | `PAD_A`, `PAD_B`, `PAD_X`, `PAD_Y`, `PAD_LB`, `PAD_RB`, `PAD_LT`, `PAD_RT`, `PAD_UP`/`PAD_DOWN`/`PAD_LEFT`/`PAD_RIGHT`, `PAD_START`, `PAD_BACK`, `PAD_L3`, `PAD_R3` |

Observações:

* O jogo lê input a ~16 ms por frame; se uma ação não registrar, aumente o `press_ms` (ou o `period_ms`, nos spins).
* Gatilho e alvos são independentes e podem misturar dispositivos: segurar `PAD_RB` e spammar teclas do teclado funciona, assim como segurar `MOUSE5` e pulsar botões do controle. Em combos mistos, teclado e controle pulsam em fase.
* Para jogos que leem input via DirectInput (como a Bayonetta), o turbo injeta teclado e mouse no buffer de estado do jogo usando scancodes DIK, o que costuma funcionar melhor do que a via tradicional de `SendInput`.
* No modo `hold`, o gatilho físico é detectado a partir do estado real do jogo quando possível, e os eventos sintéticos gerados pelo próprio turbo são ignorados na detecção (sem loop de feedback).
* Alvos/gatilhos de controle exigem que o jogo importe `XInputGetState` (o hook de IAT é instalado sob demanda). Se a importação não existir, `turbo_start` retorna `false` com `[FAIL]` no log — sem travar nada.
* `control = "turbo"` / `control = "spin"` no manifesto renderizam os campos de config + botão TURBO/SPIN na UI automaticamente.

**Exemplo — preset fixo.** Copie para um arquivo novo (ex.: `TurboEsquiva.lua`) e ele vira um botão próprio na UI, com hotkey própria, sem precisar de campos:

```lua
function manifest()
    return {
        label = "Esquiva Turbo",
        category = "INPUT",
        control = "toggle",   -- preset fixo não precisa de campos na UI
        hotkey = "ALT+E",
        description = "Segure MOUSE5 para spammar esquiva (SHIFT) a 25/s",
    }
end

function on_enable()
    confirm_enable(turbo_start({ target = "SHIFT", trigger = "MOUSE5",
                                 press_ms = 20, gap_ms = 20, mode = "hold" }))
end

function on_disable()
    turbo_stop()
end
```

### 4.12 Arquivos e segurança do runtime

Os scripts rodam **dentro do processo do jogo com acesso total à memória** (`write_memory` pode reescrever qualquer byte). Por isso, a filosofia de segurança é: só instale scripts de fontes em que você confia — nenhuma sandbox protege contra um script que já pode reescrever o código do jogo.

Ainda assim, o runtime é **endurecido** na inicialização: removem-se apenas as funções que nenhum mod precisa e que causam estrago fora do escopo de modding. Ficam **indisponíveis**: `os.execute`, `io.popen` (shell/processos), `os.remove`, `os.rename` (apagar/mover arquivos), `os.exit` (encerrar o jogo) e `package.loadlib` + `package.cpath` (carregar DLL nativa arbitrária).

A **E/S de arquivos continua disponível** — `io.open`, `io.read`, `io.write`, `os.time`, `os.date`, `os.getenv` etc. — então um script pode ler um arquivo do jogo ou salvar um arquivo de configuração/preset normalmente.

* `scripts_path(rel?)` — retorna o caminho absoluto da pasta `scripts/` do trainer, com `rel` opcional anexado. Use isto para localizar arquivos: `io.open` resolve caminhos relativos contra o CWD do **jogo** (imprevisível), então `io.open(scripts_path("config/x.cfg"), "r")` é determinístico. A pasta `scripts/config/` é criada automaticamente.

Para o caso comum, prefira os helpers do prelude `read_file` / `write_file` / `config_save` / `config_load` (seção 5.7), que já resolvem o caminho e tratam erros sem lançar exceção.

---

## 5. Helpers do prelude (`_lib.lua`)

O arquivo `scripts/_lib.lua` é carregado uma vez pela engine e expõe helpers globais a todos os scripts (é ignorado pela descoberta, não vira feature). Os tópicos abaixo espelham as regiões do próprio arquivo.

### 5.1 Logs

* `info(msg)` / `fail(msg)` — logs já prefixados com `[FEATURE_NAME]`. Sempre logam.
* `DEBUG` (global, default `false`) e `debug_info(msg)` — logs de funcionamento esperado (ON/OFF, confirmações) só aparecem com `DEBUG = true`. Erros (`fail`) sempre aparecem.

### 5.2 Estado / ciclo de vida

* `toggle(on_fn, off_fn)` — lê o estado de `FEATURE_NAME`, inverte e chama a função certa (estilo corpo, alternativa aos hooks). Retorna `true` se ligou.
* `is_enabled()` — estado atual da feature como boolean.
* `confirm_enable(ok, on_msg?, fail_msg?)` — padrão do `on_enable()`: loga o resultado (sucesso via `debug_info`) e reverte o toggle na UI em falha. Retorna `ok`.

### 5.3 Argumentos da UI

* `require_arg(name, default)` — lê um argumento com fallback quando ausente/zero.
* `arg_string(name, default?)` / `arg_int(name, default?)` — `get_arg` com guarda de tipo; `""`/`0` quando ausente (nos turbos/spins, isso significa "reaproveitar a última config").

### 5.4 Memória

* `bytes_from_int(n)` / `bytes_from_float(f)` — convertem um número em tabela de bytes little-endian (sem o boilerplate de `string.pack`).
* `write_float_value(symbol, offsets?, value)` / `write_int_value(symbol, offsets?, value)` — escrita via cadeia de ponteiros; `offsets` é opcional.
* `freeze_float(symbol, value)` / `freeze_int(symbol, value)` / `unfreeze(symbol)` — congelamento sem montar bytes na mão.
* `assert_symbol(symbol)` — valida (read guarded) que um símbolo resolveu; reporta erro estruturado e retorna `false` se inválido.

### 5.5 Input: turbo (teclado / mouse / controle)

Atalhos sobre `turbo_start`; todos retornam true/false. Ciclo default: 60 ms.

* `mash(targets, ms?)` — turbo clássico: segurar o próprio botão o repete. Ex.: `mash("PAD_A")`.
* `turbo_combo(targets, trigger, ms?)` — segurar o gatilho masheia o combo. Ex.: `turbo_combo("PAD_X+PAD_Y+PAD_A+PAD_B", "PAD_DOWN")`.
* `on_hold(trigger, targets, ms?)` — o mesmo, na ordem falada ("ao segurar X, masheia Y").
* `turbo_auto(targets, ms?)` — pressiona sozinho até `turbo_stop()`.
* `turbo_from_args()` — lê os args padrão da UI (`control = "turbo"`: target, trigger, press_ms, gap_ms, hold) e chama `turbo_start`. Funciona para teclado, mouse e controle.

### 5.6 Input: spins (analógico e mouse)

Atalhos sobre `stick_spin_start`/`mouse_spin_start`; todos retornam true/false. Defaults: stick esquerdo, 400 ms/volta, `consume=true`; mouse com raio 120 px.

* `spin_left(trigger, period_ms?, stick?)` / `spin_right(...)` — gira o analógico enquanto o combo estiver segurado. Ex.: `spin_left("PAD_R3+PAD_A")`.
* `spin_from_args()` — lê os args padrão da UI (`control = "spin"`: trigger, stick, direction, period_ms, consume) e chama `stick_spin_start`.
* `mouse_spin_left(trigger, period_ms?, radius?)` / `mouse_spin_right(...)` — move o MOUSE em círculos (como girar o mouse na mesa). Ex.: `mouse_spin_left("MOUSE4")`.

### 5.7 Arquivos e configuração

Helpers seguros sobre `io` (retornam nil/false em vez de lançar erro) e resolvem caminhos de forma determinística — ver seção 4.12.

* `scripts_path(rel?)` — caminho absoluto da pasta `scripts/` do trainer, com `rel` opcional anexado.
* `read_file(path)` / `write_file(path, text)` — lê/escreve um arquivo (caminho relativo é resolvido contra `scripts/`; absoluto é usado como está). `read_file` devolve `nil` se não abrir; `write_file` devolve `true`/`false`.
* `config_save(name, tbl)` / `config_load(name)` — persiste uma tabela plana (string/number/bool) em `scripts/config/<name>.cfg` e a lê de volta com os tipos convertidos. Sem arquivo, `config_load` devolve `{}`.

---

## 6. Dicas Importantes

- Use sempre o `address.ini` para mapear os padrões de bytes ou ponteiros do jogo em vez de hardcodar endereços (o ASLR muda os endereços base).
- O backend cuida de mudar as permissões de página de memória (`VirtualProtect`) automaticamente.
- Chame `restore_memory` ou `unfrozen_memory` ao desativar uma funcionalidade para evitar crashes no jogo.
- `restore_memory(symbol)` restaura **todas** as regiões que aquele símbolo modificou (ex: `write_memory` no offset 0 + `nop_memory` no offset 6 são desfeitos numa única chamada).
- Acessos a endereços inválidos são tolerados: geram `[FAIL]` no log em vez de crash. Porém tenha bom senso, é comun em caso de ponteiro invalidos causar crash in-game. Use `assert_symbol` para validar símbolos antes de ler/escrever.
