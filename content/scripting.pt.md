# 📖 Guia de Configuração e Criação de Scripts — Bayonetta Trainer V2

Este guia foi elaborado para usuários e desenvolvedores que baixaram a versão compilada do trainer (a partir das *Releases* do GitHub) e desejam customizar atalhos, ajustar configurações ou programar novos mods usando scripts Lua.

---

## ⚙️ Entendendo o `trainer.ini`

O arquivo `trainer.ini` fica na mesma pasta que o executável do jogo e controla todo o comportamento inicial do backend do trainer. Você pode editá-lo com qualquer editor de texto (como o Bloco de Notas).

### 1. Seção `[Network]` (Configurações de Rede)
O frontend (interface gráfica) se conecta ao jogo via conexões de rede locais.
* **`Port=27015`**: A porta de rede que o servidor interno do trainer usará para ouvir os comandos da interface. Só mude se essa porta já estiver sendo usada por outro programa.
* **`AllowRemoteUI=0`**:
  * `0` (Recomendado): Apenas o seu próprio computador pode se conectar ao trainer (seguro).
  * `1`: Permite conexões de outros aparelhos na mesma rede local (útil se você quiser rodar a interface em outro computador ou no celular).
* **`AuthToken=`**: Permite definir uma senha de autenticação. Se você definir uma senha aqui (ex: `AuthToken=MinhaSenha123`), qualquer interface que tente se conectar precisará enviar essa senha nos pacotes para que os comandos funcionem.

> **Dica para desenvolvedores de UI:** o protocolo é JSON delimitado por `\n`. Envie `{"type":"help"}` para receber a lista completa de comandos disponíveis (nome, parâmetros e descrição) direto do backend. Veja `UI/AutoUI/README.md` para a referência do protocolo.

### 2. Seção `[beep]` (Efeitos Sonoros)
Configura o som do sinal sonoro (beep) emitido ao ativar ou desativar mods.
* **`alert=1`**: Ativa (`1`) ou desativa (`0`) o som.
* **`frequencyON=800`** / **`durationON=150`**: Frequência (em Hz) e duração (em milissegundos) do beep emitido ao **ativar** um mod.
* **`frequencyOFF=600`** / **`durationOFF=150`**: Frequência e duração do beep emitido ao **desativar** um mod.

### 3. Seção `[Features]` (Estado Inicial)
Define o estado padrão de cada mod quando o jogo inicia. **Esta seção é opcional**: os scripts da pasta `scripts/` são descobertos automaticamente — um mod que não estiver listado aqui simplesmente inicia desativado.
* O nome da variável deve ser **exatamente igual** ao nome do arquivo do script contido na pasta `scripts/` (sem o `.lua`).
* **`0`**: Desativado ao iniciar.
* **`1`**: Ativado ao iniciar.

```ini
[Features]
GodMode=0
InfiniteJump=0
```

### 4. Seção `[Hotkeys]` (Atalhos de Teclado)
Mapeia teclas do teclado para alternar (ativar/desativar) as features.
* Você pode usar teclas simples (como `F1`, `G`, `NUMPAD5`) ou combinações usando modificadores (`CTRL+F1`, `ALT+A`, `SHIFT+F`).

```ini
[Hotkeys]
GodMode=ALT+G
InfiniteJump=CTRL+F6
```

---

## 🛠️ Como Criar Novos Scripts (Passo a Passo)

A grande vantagem do Bayonetta Trainer V2 é que você não precisa recompilar o código C++ para adicionar mods. Toda a lógica é feita em scripts **Lua**, que são interpretados dinamicamente.

### Passo 1: Encontrar o Padrão de Bytes (AOB)
Em vez de usar endereços de memória fixos (que mudam sempre que o jogo inicia), o trainer usa busca por padrões de bytes (AOB - Array of Bytes). Use a ferramenta de engenharia reversa que preferir — **Cheat Engine** (anexado ao processo), **IDA**, **Ghidra**, **x64dbg**, etc. Para o trainer não importa de onde o padrão veio; só importam os bytes.
1. Encontre a instrução em código de máquina (Assembly) responsável pelo mod que você quer fazer (ex: a instrução que diminui a vida) — por scan de memória ao vivo (Cheat Engine) ou análise estática do binário do jogo (IDA/Ghidra).
2. Copie o padrão de bytes hexadecimal da instrução (ex: `89 8F A0 00 00 00`).
3. Se alguns bytes mudarem dependendo da versão do jogo, você pode substituí-los por `?` (wildcards).

### Passo 2: Registrar o Endereço em `address.ini`
Abra o arquivo `address.ini` e adicione o padrão de bytes sob uma nova tag (identificador único).

```ini
[func_DanoJogador]
89 8F A0 00 00 00
```
*Dica:* Se você tiver diferentes padrões para diferentes versões do jogo, você pode colocá-los um embaixo do outro no mesmo bloco para servirem de backup (fallback).

### Passo 3: Criar o Script Lua
Na pasta `scripts/`, crie um arquivo com o nome do seu mod (ex: `MeuMod.lua`).

#### Exemplo 1: Escrevendo bytes modificados (ex: NOP ou JMP)
Este modelo é ideal para desativar funções do jogo (como dano ou detecção de colisão):

```lua
-- Verifica o estado atual do mod. Se for 0 (desativado), define para 1.
local on = get_state("MeuMod") == 0
set_state("MeuMod", on and 1 or 0)

if on then
    -- Escreve o byte 0x90 (NOP) no endereço de "func_DanoJogador" para desativar a instrução
    nop_memory("func_DanoJogador", 0, 6)
    log_info("MeuMod ativado com sucesso!")
else
    -- Restaura automaticamente os bytes originais do jogo
    restore_memory("func_DanoJogador")
    log_info("MeuMod desativado!")
end
```

#### Exemplo 2: Congelando valores (ex: Vida Infinita ou Witch Time infinito)
Este modelo é ideal para travar um número em um valor específico:

```lua
local on = get_state("VidaInfinita") == 0
set_state("VidaInfinita", on and 1 or 0)

if on then
    -- Congela o valor de vida. O trainer reescreverá o valor continuamente.
    -- Parâmetros: (nome_da_tag, offsets_em_tabela, bytes_do_valor)
    -- Exemplo: Congelar vida como 9999 (0x0F, 0x27 em hexadecimal little-endian)
    frozen_memory("addr_VidaTotal", {}, {0x27, 0x0F, 0x00, 0x00})
    log_info("Vida infinita congelada!")
else
    -- Para de congelar o endereço
    unfrozen_memory("addr_VidaTotal")
    log_info("Vida infinita desligada!")
end
```

### Passo 4 (opcional): Descrever o Mod com `manifest()`
Basta salvar o arquivo na pasta `scripts/` — o trainer o descobre sozinho e ele já aparece na interface. Para que a UI mostre nome bonito, categoria, atalho e campos de valor automaticamente, adicione uma função `manifest()` no topo do script:

```lua
function manifest()
    return {
        label    = "Meu Mod",       -- nome exibido na UI
        category = "PLAYER",          -- grupo na UI
        control  = "toggle",          -- toggle | value | freeze | action
        hotkey   = "ALT+H",           -- atalho default (o [Hotkeys] do .ini sobrescreve)
        description = "O que ele faz",
        args = {                      -- só para control = value/freeze
            { name = "value", type = "int", min = 0, max = 9999, step = 1, default = 100 }
        }
    }
end
```

Consulte o `Backend/LUA_API.md` para a referência completa do manifesto.

### Passo 5 (opcional): Ajustes no `trainer.ini`
O `.ini` não é mais obrigatório para registrar mods — ele serve para sobrescrever defaults:

1. Em `[Features]`, adicione `MeuMod=1` se quiser que ele inicie **ativado**.
2. Em `[Hotkeys]`, adicione `MeuMod=ALT+H` para sobrescrever o atalho do manifesto.

Pronto! Ao iniciar o jogo, o mod aparece na interface e responde ao atalho definido.

---

## 📚 Referência da API Lua

Aqui estão as principais funções expostas pelo motor C++ para uso nos seus scripts:

### Estado e Logs
* `get_state("nome")`: Retorna o estado atual da feature (`0` para desligado, `1` para ligado).
* `set_state("nome", valor)`: Modifica o estado (`0` ou `1`).
* `log_info("mensagem")`: Imprime uma mensagem informativa no log.
* `log_fail("mensagem")`: Imprime uma mensagem de erro no log.

### Edição de Memória
* `write_memory("tag", offset, {bytes})`: Escreve uma lista de bytes a partir do endereço da tag + offset.
* `nop_memory("tag", offset, tamanho)`: Substitui os bytes do endereço por instruções NOP (`0x90`).
* `restore_memory("tag")`: Restaura os bytes para o estado original antes da modificação.
* `read_int("tag", offset)` / `read_float("tag", offset)`: Lê valores numéricos diretamente da memória.
* `write_int("tag", offset, valor)` / `write_float("tag", offset, valor)`: Grava valores numéricos no endereço.
* `write_on_pointer_int("tag", {offsets}, valor)` / `write_on_pointer_float("tag", {offsets}, valor)`: Resolve ponteiros e edita o valor final.
* `frozen_memory("tag", {offsets}, {bytes})`: Congela os bytes especificados no endereço do ponteiro.
* `unfrozen_memory("tag")`: Descongela o endereço.

### Input (turbo e giro de analógico)
* `turbo_start({...})` / `turbo_stop()`: Repete inputs automaticamente (teclado, mouse ou controle XInput). Ver `Backend/LUA_API.pt.md` para todas as opções.
* `stick_spin_start({...})` / `stick_spin_stop()`: Gira um analógico do controle em círculo enquanto um combo de botões estiver segurado.
* Atalhos do prelude (`_lib.lua`), recomendados para scripts simples:
  * `mash("PAD_A")` — segurar A repete A (turbo clássico);
  * `turbo_combo("PAD_X+PAD_Y+PAD_A+PAD_B", "PAD_DOWN")` — segurar o gatilho masheia o combo;
  * `turbo_auto("J", 80)` — pressiona sozinho até `turbo_stop()`;
  * `spin_l