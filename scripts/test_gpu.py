import torch
import sys

def test_gpu_environment():
    print("=== Teste de Ambiente PyTorch & CUDA ===")
    print(f"Python Version:  {sys.version.split()[0]}")
    print(f"PyTorch Version: {torch.__version__}")
    print(f"CUDA Available:  {torch.cuda.is_available()}")

    if not torch.cuda.is_available():
        print("\n❌ ERRO: O PyTorch não conseguiu acessar a GPU. Verifique a instalação do driver e do CUDA.")
        return

    device = torch.device("cuda:0")
    props = torch.cuda.get_device_properties(device)

    print(f"\n=== Informações da GPU ===")
    print(f"Nome da GPU:        {props.name}")
    print(f"Compute Capability: {props.major}.{props.minor}")
    print(f"VRAM Total:         {props.total_memory / (1024**3):.2f} GB")
    print(f"BFloat16 Suportado: {torch.cuda.is_bf16_supported()}")

    print("\n=== Teste do Flash-Attention ===")
    try:
        import flash_attn
        print(f"✅ Flash-Attention detectado! Versão: {flash_attn.__version__}")
    except ImportError:
        print("⚠️ Flash-Attention não encontrado no ambiente ou falhou ao importar.")

    print("\n=== Teste de Computação Básico (bfloat16) ===")
    try:
        # Criando tensores diretamente na VRAM da GPU para testar os Tensor Cores
        print("Alocando tensores 4096x4096 e multiplicando...")
        a = torch.randn(4096, 4096, device=device, dtype=torch.bfloat16)
        b = torch.randn(4096, 4096, device=device, dtype=torch.bfloat16)
        c = torch.matmul(a, b)
        print("✅ Cálculo na GPU concluído com sucesso!")
        
        # Limpando a VRAM após o teste
        del a, b, c
        torch.cuda.empty_cache()
    except Exception as e:
        print(f"❌ Erro ao executar cálculo na GPU: {e}")

if __name__ == "__main__":
    test_gpu_environment()