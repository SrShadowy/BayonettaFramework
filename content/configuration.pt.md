# Documentação e Configuração do Projeto (Bayonetta Trainer V2)

Esta documentação fornece uma visão geral do funcionamento do backend do **Bayonetta Trainer V2**, explicando como configurar opções, adicionar atalhos e gerenciar as assinaturas de memória.

## Estrutura de Arquivos

- `/scripts` - Contém os scripts em `.lua` com a lógica individual de cada mod (GodMode, InfiniteJump, etc.).
- `dinput8.dll` - O backend do trainer, carregado automaticamente pelo jogo.
- `trainer.ini` - Arquivo de configuração principal (Features, Hotkeys, Configs).
- `address.ini` - Mapeamento de assinaturas (AOB) e ponteiros.

## Como Configurar (`trainer.ini`)

O arquivo `trainer.ini` gerencia o estado inicial, atalhos de teclado e configurações de rede.

### Seção `[Network]`
Define as configurações de socket e segurança para comunicação externa (ex: interface em Python, Web ou Electron).
- `Port=27015` - Porta utilizada pelo servidor interno do trainer.
- `AllowRemoteUI=0` - (Segurança) Define se o trainer deve aceitar conexões apenas do próprio computador (`0`) ou de qualquer dispositivo na rede local (`1`). Deixe em `0` se não for usar o celular.
- `AuthToken=` - (Segurança) Define uma senha (Token) de autenticação. Se estiver preenchida, qualquer interface externa precisará enviar esse token (ex: `{"token": "sua_senha"}`) em todos os pacotes JSON para que o comando seja aceito.

### Seção `[beep]`
Configurações de feedback sonoro quando um mod é ativado ou desativado.
- `alert=1` - Ativa/desativa o som (1 = ativado).
- `frequencyON`, `durationON` - Frequência e duração do beep de ativação.
- `frequencyOFF`, `durationOFF` - Frequência e duração do beep de desativação.

> **Linux/Proton:** o beep funciona sob Wine/Proton. O trainer detecta o Wine e, nesse caso, sintetiza o tom via `waveOut` (o `Beep()` do Windows não emite som no Wine), respeitando as mesmas frequências e durações. Nenhuma configuração extra é necessária.

### Seção `[Features]`
Define o estado inicial de cada mod (0 para desligado, 1 para ligado). **Seção opcional**: os scripts da pasta `scripts/` são descobertos automaticamente; um mod não listado aqui inicia desativado. O nome da variável deve corresponder ao nome do script `.lua` na pasta `scripts/` (ex: `GodMode=0` vai rodar `GodMode.lua` ao ser ativado).

```ini
[Features]
InfiniteJump=0
GodMode=0
HitKill=0
```

### Seção `[Hotkeys]`
Mapeia teclas de atalho para os scripts descobertos. O trainer interceptará essas teclas globalmente para dar "toggle" nos scripts. Um atalho definido aqui **sobrescreve** o `hotkey` declarado no `manifest()` do script (ver `LUA_API.md`).

```ini
[Hotkeys]
InfiniteJump=CTRL+F6
GodMode=ALT+G
```

## Configurando Endereços e Padrões (`address.ini`)

O arquivo `address.ini` é fundamental para a compatibilidade do trainer entre diferentes versões do jogo. Ele não trabalha com endereços fixos, mas sim com **Array of Bytes (AOB / Patterns)**.

Formato:
```ini
[nome_do_symbol]
XX XX ? ? XX XX XX, Y
```

- Onde `XX` são os bytes exatos em Hexadecimal e `?` são wildcards (bytes que mudam ou não importam).
- `Y` (opcional) indica um offset adicional após encontrar o padrão, ou qual ocorrência usar.
- Múltiplas linhas abaixo de uma chave funcionam como *fallbacks* ou para ler diferentes ponteiros em cadeia.

No Lua, este símbolo será referenciado pelo nome. Por exemplo, a chave `[func_DmgCombat]` no `.ini` será usada como `write_memory("func_DmgCombat", 0, {0xEB})` no script.

## Como Adicionar uma Nova Funcionalidade

1. **Encontre o Padrão de Bytes** - Use sua ferramenta de engenharia reversa preferida (Cheat Engine, IDA, Ghidra...) para achar a instrução no jogo.
2. **Adicione no `address.ini`** - Crie uma tag (ex: `[func_MinhaFeature]`) e cole o padrão de bytes encontrado com wildcards quando necessário.
3. **Crie o Script Lua** - Crie um arquivo `MinhaFeature.lua` na pasta `scripts/`. Programe a lógica usando a API (ver `LUA_API.md`). Pronto: o script é descoberto automaticamente e já aparece na UI.
4. **(Opcional) Adicione um `manifest()`** - Declare label, categoria, tipo de controle, hotkey e args no próprio script para a UI montar o controle certo (ver `LUA_API.md`).
5. **(Opcional) Sobrescreva no `trainer.ini`** - `MinhaFeature=1` em `[Features]` para iniciar ativado; `MinhaFeature=