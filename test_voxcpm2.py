from voxcpm import VoxCPM
import soundfile as sf

def test_voxcpm2():
    print("Iniciando o teste do VoxCPM2...")
    
    try:
        # Carrega o modelo
        print("Carregando o modelo openbmb/VoxCPM2...")
        model = VoxCPM.from_pretrained("openbmb/VoxCPM2", load_denoiser=False, device="cpu")
        
        # O texto que o modelo vai falar
        texto = "(A friendly man, clear and natural voice) Olá! Este é um teste gerado com o modelo VoxCPM2. Estou testando a geração de voz usando Python."
        print(f"Gerando áudio para o texto: '{texto}'")
        
        # Gera o áudio
        wav = model.generate(text=texto)
        
        # Salva o arquivo de saída
        output_file = "teste_voxcpm2.wav"
        
        # A API pode fornecer o sample_rate em model.tts_model.sample_rate ou ser padrão 48000
        sample_rate = getattr(model, "tts_model", model).sample_rate if hasattr(model, "tts_model") else 48000
        
        sf.write(output_file, wav, sample_rate)
        
        print(f"Sucesso! Áudio salvo como: {output_file}")
        
    except ImportError as e:
        print(f"Erro de importação. Verifique se o módulo 'voxcpm' e 'soundfile' estão instalados: {e}")
        print("Instale com: pip install voxcpm soundfile")
    except Exception as e:
        print(f"Ocorreu um erro durante a execução: {e}")

if __name__ == "__main__":
    test_voxcpm2()
