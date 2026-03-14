import requests

def ask_qwen(prompt):
    url = "http://localhost:11434/api/generate"
    data = {
        "model": "qwen-reasoning",
        "prompt": prompt,
        "stream": False
    }
    
    response = requests.post(url, json=data)
    return response.json()['response']

print("🚀 Enviando pergunta para a RTX 5090 via Ollama...")
resposta = ask_qwen("Como estruturar um ambiente Python para PMSP-ML com Deep Reinforcement Learning?")
print(f"\nResposta:\n{resposta}")