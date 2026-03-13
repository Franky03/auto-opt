# auto-opt

Configuração para rodar o modelo Qwen 3.5 27B localmente na GPU via Ollama.

## Pré-requisitos

- GPU NVIDIA com pelo menos 16GB de VRAM (testado com RTX 5090)
- [Driver NVIDIA](https://www.nvidia.com/drivers) instalado
- Python 3.10+

## Passo a passo

### 1. Instalar o Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Verifique se está rodando:

```bash
ollama --version
```

### 2. Clonar o repositório

```bash
git clone <url-do-repositorio>
cd auto-opt
```

### 3. Baixar o modelo GGUF

```bash
wget -O Qwen3.5-27B.Q4_K_M.gguf "https://huggingface.co/Jackrong/Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-GGUF/resolve/main/Qwen3.5-27B.Q4_K_M.gguf?download=true"
```

> O arquivo tem ~15GB. Certifique-se de ter espaço em disco suficiente.

### 4. Criar o modelo no Ollama

```bash
ollama create qwen-reasoning -f Modelfile
```

### 5. Instalar dependências Python

```bash
pip install requests
```

### 6. Rodar

```bash
python model_qwen.py
```

## Uso via terminal

Você também pode conversar direto pelo terminal:

```bash
ollama run qwen-reasoning
```

## Estrutura do projeto

```
auto-opt/
├── Modelfile           # Configuração do modelo para o Ollama
├── model_qwen.py       # Script Python para consultar o modelo via API
├── scripts/
│   └── test_gpu.py     # Teste de ambiente GPU/CUDA
└── README.md
```

## Testando a GPU

Para verificar se sua GPU e CUDA estão funcionando:

```bash
pip install torch
python scripts/test_gpu.py
```
