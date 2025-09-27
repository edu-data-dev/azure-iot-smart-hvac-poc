import time
import json
import random
import threading
from azure.iot.device import IoTHubDeviceClient, Message
from dotenv import load_dotenv
import os   

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# --- CONFIGURAÇÃO ---
# Configuração via variáveis de ambiente para segurança
CONNECTION_STRING = os.getenv("AZURE_IOT_CONNECTION_STRING", "")
DEVICE_ID = "sensor-sala101"
BUILDING_ID = "SP-EDF01"
ROOM_ID = "101"

# Validação de configuração
if not CONNECTION_STRING:
    print("❌ ERRO: Variável de ambiente AZURE_IOT_CONNECTION_STRING não configurada!")
    print("💡 Configure a variável de ambiente ou crie um arquivo .env")
    print("📋 Exemplo: export AZURE_IOT_CONNECTION_STRING='HostName=...'")
    exit(1)

# Simulação de temperatura
temperatura_atual = 22.5
fator_variacao = 0.5
ac_ligado = False

# --- FUNÇÕES ---

def command_listener(device_client):
    """Escuta por comandos C2D (Cloud-to-Device) em uma thread separada."""
    global ac_ligado
    while True:
        try:
            message = device_client.receive_message()  # Bloqueante
            if message:
                print(f"\n[COMANDO RECEBIDO]: {message.data.decode('utf-8')}")
                
                # Simples lógica para ligar/desligar o AC
                if "LIGAR" in message.data.decode('utf-8').upper():
                    ac_ligado = True
                    print("[AÇÃO]: Ar-condicionado LIGADO.")
                elif "DESLIGAR" in message.data.decode('utf-8').upper():
                    ac_ligado = False
                    print("[AÇÃO]: Ar-condicionado DESLIGADO.")
            time.sleep(1)
        except Exception as e:
            print(f"Erro no listener de comandos: {e}")
            time.sleep(5)


def run_telemetry_simulation():
    """Função principal que envia a telemetria."""
    global temperatura_atual
    global ac_ligado

    try:
        # Cria o cliente do dispositivo
        device_client = IoTHubDeviceClient.create_from_connection_string(CONNECTION_STRING)
        device_client.connect()
        print("Simulador de sensor conectado ao IoT Hub.")

        # Inicia a thread que escuta por comandos
        command_thread = threading.Thread(target=command_listener, args=(device_client,))
        command_thread.daemon = True
        command_thread.start()

        while True:
            # Lógica para simular a variação da temperatura
            if ac_ligado:
                # Se o AC está ligado, a temperatura tende a baixar
                temperatura_atual -= fator_variacao * random.random()
            else:
                # Se está desligado, a temperatura tende a subir
                temperatura_atual += fator_variacao * random.random()

            # Monta o payload da mensagem
            msg_payload = {
                "deviceId": DEVICE_ID,
                "buildingId": BUILDING_ID,
                "roomId": ROOM_ID,
                "temperature": round(temperatura_atual, 2)
            }
            
            message_json = json.dumps(msg_payload)
            message = Message(message_json)
            message.content_encoding = "utf-8"
            message.content_type = "application/json"

            # Envia a mensagem
            print(f"Enviando mensagem: {message_json}")
            device_client.send_message(message)
            
            time.sleep(10) # Envia a cada 10 segundos

    except KeyboardInterrupt:
        print("Simulador interrompido pelo usuário.")
    except Exception as e:
        print(f"Erro inesperado: {e}")
    finally:
        if 'device_client' in locals() and device_client.connected:
            device_client.disconnect()
            print("Dispositivo desconectado.")

if __name__ == '__main__':
    run_telemetry_simulation()