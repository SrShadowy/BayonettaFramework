# 🎮 BayonettaTrainerV2 — Guia de Instalação e Execução

Um trainer moderno para o jogo **Bayonetta**, projetado com uma arquitetura separada entre **Backend (C++ DLL)** e **Frontend (Python/PySide6 UI)** que se comunicam através de conexões de Socket TCP locais.

---

## 🛠️ Como Instalar (Passo a Passo)

### 1. Extrair os Arquivos do Trainer
Após baixar o arquivo `.zip` da release do trainer, você deve extrair o conteúdo diretamente na **pasta raiz do jogo** (onde fica localizado o executável `Bayonetta.exe`).

Os arquivos que devem ser colocados na pasta raiz do jogo são:
* `dinput8.dll` (o backend em C++ que intercepta e injeta a lógica no jogo)
* `trainer.ini` (arquivo de configurações gerais, hotkeys e porta de rede)
* `address.ini` (mapeamento de patterns de memória e AOBs)
* `scripts/` (pasta contendo todos os scripts `.lua` com as funcionalidades dos mods)

> [!IMPORTANT]
> A DLL deve se chamar exatamente `dinput8.dll` e estar na mesma pasta que o `Bayonetta.exe` para que o jogo a carregue automaticamente na inicialização.

---

### 2. Instalar a Dependência do MSVC++ (Obrigatório)
Como o backend do trainer foi desenvolvido em C++, é necessário que o seu sistema operacional Windows possua as bibliotecas runtime atualizadas do Microsoft Visual C++.

* Baixe e instale o instalador oficial do: **[Microsoft Visual C++ Redistributable 2015-2022](https://aka.ms/vs/17/release/vc_redist.x86.exe)**
* *Nota:* Como o Bayonetta é um jogo 32-bits (x86), certifique-se de instalar a versão **x86** (`vc_redist.x86.exe`), embora instalar a versão x64 também seja recomendado para o sistema.

---

### 3. Executar a Interface (Frontend)
A interface gráfica é o que permite a você ativar e desativar os mods visualmente, além de ver logs em tempo real.

Basta executar o arquivo `BayonettaTrainer.exe` fornecido na pasta para abrir a interface diretamente.

> [!NOTE]
> Prefere criar sua própria interface? O protocolo da UI é aberto (JSON delimitado por linha via TCP local) — veja a página **Protocolo da UI / AutoUI**.

---

## 💻 Customização Avançada & Scripts
Se você deseja entender o que cada configuração no `trainer.ini` faz ou quer aprender a criar seus próprios mods em Lua, consulte o **[Guia de Configuração e Scripts (PT)](file:///run/media/shadowy/8240450440450081/Users/Shadowy/Documents/GitHub/BayonettaTreinerV2/DOCS.pt.md)**.


