# [Auto Trainer UI](https://github.com/SrShadowy/BayonettaFramework/tree/main/AutoUI) (manifest-driven)

UI standalone em Python (tkinter, sem dependências externas) que monta a interface **sozinha** a partir dos manifestos dos scripts. Nenhum mod é hardcoded aqui: adicionar um `.lua` na pasta `scripts/` do backend faz um controle novo aparecer na tela.

## Uso

```
python auto_trainer_ui.py [--host 127.0.0.1] [--port 27015] [--token SENHA]
```

Requer Python 3.8+ com tkinter (no Windows já vem; em Linux, pacote `tk`).

## Como a interface é montada

1. Ao conectar, envia `{"type":"hello"}` (recebe `welcome` + snapshot `state`) e `{"type":"describe"}`.
2. A resposta `{"type":"manifest","scripts":[...]}` traz um objeto por script:


| Campo          | Descrição                                                                           |
| -------------- | ------------------------------------------------------------------------------------- |
| `name`         | nome da feature (= nome do arquivo`.lua`)                                             |
| `has_manifest` | se o script definiu`manifest()`                                                       |
| `label`        | texto exibido (fallback:`name`)                                                       |
| `category`     | grupo na UI (fallback:`GENERAL`)                                                      |
| `control`      | `toggle` \| `value` \| `freeze` \| `turbo` \| `spin` \| `action` (fallback: `toggle`) |
| `hotkey`       | atalho default, se declarado                                                          |
| `description`  | tooltip                                                                               |
| `args[]`       | `{name, type, min?, max?, step?, default?}` — define os campos de input              |

3. Mapeamento `control → widget`:


| `control` | Widget                                             |
| --------- | -------------------------------------------------- |
| `toggle`  | botão ON/OFF                                      |
| `value`   | campos + botão SET                                |
| `freeze`  | campos + botão FREEZE (com estado ativo)          |
| `turbo`   | campos de config + botão TURBO (com estado ativo) |
| `spin`    | campos de config + botão SPIN (com estado ativo)  |
| `action`  | botão RUN                                         |

`args[].type`: `int`/`float` → spinbox, `bool` → checkbox, `string` → campo de texto. Se `value`/`freeze` vier sem `args`, a UI assume um arg `value` int (compatibilidade com backends antigos).

## Mensagens do protocolo (TCP, JSON delimitado por `\n`)

Enviadas pela UI:

```json
{"type":"hello"}
{"type":"describe"}
{"type":"help"}
{"type":"command","feature":"GodMode"}
{"type":"command","feature":"SetHoly","args":{"value":100000}}
{"type":"state","feature":"GodMode"}
{"type":"check"}
{"type":"reload"}
```

`{"type":"help"}` responde `{"type":"help","commands":[{name,params,description}...]}` com a lista completa de comandos do protocolo — útil para explorar o backend com um simples `nc`/`telnet`.

Se `AuthToken` estiver definido no `trainer.ini`, todo envio inclui `"token":"..."`.

Recebidas do backend:


| Mensagem                              | Tratamento na AutoUI                                                                                                        |
| ------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| `welcome`                             | loga jogo + versão do protocolo                                                                                            |
| `manifest`                            | (re)monta os controles                                                                                                      |
| `state`                               | snapshot com estados + manifestos; sincroniza os botões                                                                    |
| `ack {feature,state}`                 | atualiza o estado do controle                                                                                               |
| `error {message}`                     | loga no console                                                                                                             |
| `watch_update {feature,name,value}`   | valores vivos publicados por`watch_value()` — exibidos no console                                                          |
| `script_error {feature,message,line}` | erros estruturados de script — exibidos no console                                                                         |
| `state_changed {feature,state}`       | push quando um mod muda fora da UI (ex.: hotkey) — exibido no console; envie`hello`/`check` para ressincronizar os botões |

Mensagens desconhecidas são logadas em JSON cru — o protocolo pode ganhar tipos novos sem quebrar a UI.

## Argumentos tipados

Argumentos são tipados de ponta a ponta (`int`/`float`/`bool`/`string`): a UI envia cada valor no tipo declarado no manifesto e o backend converte conforme `args[].type`. Floats chegam à memória sem arredondamento.
