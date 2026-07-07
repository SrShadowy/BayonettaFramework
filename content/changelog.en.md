# Changelog — Bayonetta Trainer V2

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

## [0.4.5] — 2026-07-07 — Release de lançamento 🎉

Primeira release pública, consolidando o ciclo de testes. Esta versão fecha os riscos de concorrência/ciclo de vida encontrados na revisão técnica, acelera a resolução de assinaturas AOB e conclui a refatoração interna do backend — sem nenhuma mudança de comportamento para scripts ou para a UI.

### Corrigido
- **Race condition no `AddressRegistry` (podia crashar o jogo).** A thread de freeze lia o mapa de símbolos a cada tick enquanto `alloc_memory`/`free_memory`/reload o modificavam sem sincronização — comportamento indefinido. Agora protegido por `std::shared_mutex` (leituras compartilhadas na freeze thread, escrita exclusiva nos mutadores).
- **Deadlock potencial no unload da DLL.** `DLL_PROCESS_DETACH` fazia `join()` de threads segurando o loader lock do Windows. Quando o processo está terminando (`lpReserved != nullptr`) o teardown pesado é pulado — as threads já foram encerradas pelo SO e não há nada a restaurar; o caminho de `FreeLibrary` explícito preserva o teardown completo.
- **Ordem de iteração das tabelas Lua.** Offsets de cadeia de ponteiros e bytes (`write_memory`, `write_on_pointer_*`, `frozen_memory`) eram lidos com `lua_next`, que não garante ordem — e a ordem é semanticamente crítica. Agora a iteração é indexada (`luaL_len` + `lua_geti`, 1..n).
- **`AddressResolver` endurecido.** O retorno de `GetModuleInformation` passou a ser checado (antes, em falha, o scan varria uma struct não inicializada) e o dereference pós-match usa leitura guardada — um offset inválido no ini gera log em vez de crash.

### Alterado
- **Scanner AOB ~10x mais rápido.** Reescrito para localizar a maior sequência de bytes fixos do padrão (âncora) e buscá-la com `memchr` vetorizado (âncoras curtas) ou Boyer-Moore-Horspool (âncoras longas). Validado contra a implementação original em 3000+ casos com resultados idênticos.
- **Versão do protocolo** (`welcome`) atualizada para `0.4.5`.

### Interno
- **Refatoração da god class `LuaEngine`** (~1650 → ~1160 linhas), extraindo três unidades coesas: `MemoryOps` (leitura/escrita guardada SEH/`VirtualQuery`, `ScopedMemoryProtect`, alocação near-module, cadeia de ponteiros), `FreezeManager` (subsistema de freeze encapsulado — fim dos globais soltos; logging movido para fora da região crítica) e `ManifestLoader` (tipos do manifesto + sonda sandboxed; os 27 stubs no-op da sonda agora vêm de uma tabela única sincronizada com os bindings reais). API pública inalterada — nenhum consumidor precisou mudar.
- `NOMINMAX` definido no projeto (as macros `min`/`max` do `windows.h` conflitavam com o rapidjson).

### Adicionado
- **Endurecimento do runtime Lua + E/S de arquivos.** Na inicialização, `HardenRuntime()` remove só as funções perigosas e sem uso em modding (`os.execute`/`io.popen`, `os.remove`/`os.rename`, `os.exit`, `package.loadlib`/`cpath`); a leitura/escrita de arquivos (`io.open`/`read`/`write`, `os.time`/`date`/`getenv`) continua disponível para configs, presets e leitura de arquivos do jogo. Nova função `scripts_path(rel)` resolve caminhos contra a pasta do trainer (não o CWD do jogo), e o prelude ganhou `read_file`/`write_file`/`config_save`/`config_load` (pasta `scripts/config/` criada automaticamente). Não é sandbox total — de propósito: como os scripts têm `write_memory` liberado, tapar `os`/`io` por completo seria teatro de segurança e quebraria usos legítimos.
- **Giro de MOUSE (`mouse_spin_start`/`mouse_spin_stop`).** Move o mouse em círculos com deltas relativos via `SendInput` — indistinguível de girar o mouse fisicamente na mesa — enquanto um combo (controle/teclado/mouse) estiver segurado. Configurável: direção, `period_ms` por volta e `radius` em pixels. Roda em thread própria (~125 Hz), não depende do hook de XInput e só injeta com o jogo em foco. Helpers `mouse_spin_left`/`mouse_spin_right` no prelude e preset `scripts/MouseSpinLeft.lua` (ALT+M: segurar MOUSE4 gira anti-horário).
- **Gatilho do spin aceita teclado e mouse**, misturados com botões do controle (ex.: `MOUSE4`, `SHIFT+RMB`, `PAD_R3+PAD_A`) — teclado/mouse lidos via `GetAsyncKeyState`. Campo vazio/0 no `stick_spin_start` reaproveita a última config usada (útil para hotkey), como no turbo.
- **Novo controle de UI `"spin"`** (nas duas interfaces): botão SPIN com estado ativo e campos editáveis em tempo real.
- **Novo script configurável** `scripts/StickSpin.lua` (ALT+R): trigger, stick, direction, period_ms e consume na UI — o análogo do `Turbo.lua` para o giro de analógico.
- **Helper** `spin_from_args()` no prelude — lê os args padrão do controle "spin" e chama `stick_spin_start`.
- **Spin de analógico (giro automático do stick).** Novo recurso no `TurboSystem`: enquanto um combo de botões `PAD_*` estiver segurado, o stick escolhido (LS/RS) gira em círculo completo, com direção (esquerda/anti-horário ou direita/horário) e velocidade (`period_ms` por volta) configuráveis. Opção `consume` esconde do jogo os botões do gatilho enquanto gira (evita, por exemplo, pular com A ao ativar o giro). Aplicado no mesmo hook de `XInputGetState` do turbo, com fase pelo relógio global (giro suave, independente do framerate).
- **Novas funções Lua** `stick_spin_start(opções)` e `stick_spin_stop()`, com forma tabela e posicional. Documentadas nas `LUA_API*.md`.
- **Helpers de input no prelude (`_lib.lua`)** para reduzir boilerplate:
  - `mash(targets, ms)` — turbo clássico (segurar o próprio botão o repete);
  - `turbo_combo(targets, trigger, ms)` — segurar o gatilho masheia o combo;
  - `turbo_auto(targets, ms)` — pressiona sozinho até `turbo_stop()`;
  - `spin_left(trigger, period_ms, stick)` / `spin_right(...)` — giro de analógico com defaults (stick esquerdo, 400 ms/volta, `consume=true`);
  - `on_hold(trigger, targets, ms)` — `turbo_combo` na ordem falada ("ao segurar X, masheia Y");
  - `turbo_from_args()` — lê os args padrão do controle "turbo" da UI e chama `turbo_start`;
  - `arg_string(name, default)` / `arg_int(name, default)` — `get_arg` com guarda de tipo;
  - `confirm_enable(ok, on_msg, fail_msg)` — padrão do `on_enable()`: loga e reverte o toggle na UI em falha;
  - flag global `DEBUG` (default `false`) + `debug_info(msg)` — logs de funcionamento esperado (ON/OFF, sucesso do `confirm_enable`) só aparecem com `DEBUG = true`; erros sempre logam.
- **Novo preset** `scripts/StickSpinLeft.lua` (toggle, ALT+S): segurar **R3 + A** gira o stick esquerdo para a esquerda.

### Corrigido
- **Patches de bytes deixavam o jogo alterado no unload/reload.** Se um mod ligado (ex.: God Mode) estivesse ativo ao dar Shutdown ou RELOAD SCRIPTS, o código do jogo permanecia modificado, porque os backups só eram revertidos quando o script chamava `restore_memory`. Agora `LuaEngine::TeardownResources()` roda no Shutdown e no Reload e restaura **todas** as regiões patcheadas aos bytes originais, limpa os congelamentos, para o input (turbo/spins), libera as alocações e zera os estados — de forma determinística. Após um reload nada fica aplicado e a UI ressincroniza pelo snapshot.
- **Hook de XInput não encontrava `XInputGetState` na Bayonetta.** O jogo importa a função de `XINPUT1_3.dll` **por ordinal** (thunk `0x80000002`), não por nome, e o scan da IAT pulava imports por ordinal. Agora o hook reconhece o ordinal 2 (`XInputGetState` em todas as versões do XInput: 1_1–1_4 e 9_1_0) — corrige o turbo de controle (ex.: `TurboFaceButtons`).

### Alterado
- **LUA_API reorganizada por tópicos** (nas 3 línguas): índice navegável no topo; referência da API dividida em Estado/Argumentos, Logs/Watch/Erros, Memória (patch, leitura/escrita, ponteiros, freeze, alocação) e Input (turbo, spin do analógico, giro do mouse, tokens aceitos); helpers do prelude em seções que espelham as regiões do `_lib.lua`. Nenhuma função mudou — só a organização.
- **Terminologia**: "cheat" substituído por "mod" em toda a documentação (READMEs, DOCS, LUA_API, CONFIGURATION, ROADMAP) e no placeholder da UI; exemplos `MyCheat`/`MeuCheat` renomeados para `MyMod`/`MeuMod`. O nome próprio "Cheat Engine" (a ferramenta) foi mantido.
- **Interface toda em inglês**: labels/descriptions dos manifests de todos os scripts, mensagens de ON/erro dos scripts de input, rótulos dos campos (Repeat, Hold, Rev, Radius...), tooltips e placeholders da UI Qt traduzidos. Comentários de código continuam em pt-BR.
- **Categorias colapsáveis na UI (Qt)**: cada grupo (INPUT, PLAYER...) virou uma seção com cabeçalho clicável (▾ aberto / ▸ fechado); o estado fechado sobrevive a reconexões e reload de scripts.
- **UI (Qt) reformulada para telas estreitas + tema flat.** Linhas de feature com args agora são EMPILHADAS: cabeçalho (label + hotkey + botão) e campos em pares por linha com rótulos amigáveis (Segurar, Repetir, Volta, Raio...) — o layout dedicado do turbo foi substituído por esse genérico, que serve turbo/spin/value/freeze e cabe nos 320 px mínimos. Estilo: gradientes e glow removidos; superfícies sólidas escuras, bordas neutras discretas e o carmesim reservado para estado (ativo/foco/hover); dourado só em título e chips de hotkey.
- **Velocidade do giro na UI**: os presets `StickSpinLeft` e `MouseSpinLeft` viraram controle `"spin"` e expõem `period_ms` (e `radius`, no mouse) como campos editáveis em tempo real — menor = mais rápido (mín. 100 ms = 10 voltas/s), para dificuldades altas. Via hotkey, reusam os últimos valores.
- **Busca na IAT com fallbacks encadeados**: nome → ordinal 2 → comparação por ponteiro (resolve o endereço real via `GetProcAddress` por nome e, se falhar, por `MAKEINTRESOURCEA(2)`, e procura a entrada da IAT que aponta para ele — cobre inclusive descritores sem `OriginalFirstThunk`). O log indica qual método encontrou a entrada.
- `scripts/Turbo.lua`, `scripts/TurboFaceButtons.lua` e `scripts/StickSpinLeft.lua` simplificados para usar os novos helpers do prelude (`on_enable` de uma chamada só).
