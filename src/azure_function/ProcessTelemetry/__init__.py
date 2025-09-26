import logging
import json
import os
import uuid
import azure.functions as func
from azure.iot.hub import IoTHubRegistryManager

# --- Configurações da Lógica de Negócio ---
TEMPERATURE_THRESHOLD = 24.0

# --- Leitura das Connection Strings (das configurações da função) ---
# Para envio de comandos C2D, usamos a connection string de serviço do IoT Hub.
# O gatilho usa a mesma chave, mas o SDK para enviar comandos precisa dela explicitamente.
IOTHUB_SERVICE_CONNECTION_STRING = os.environ.get("IOTHUB_CONNECTION_STRING")

def main(event: func.EventHubEvent, outputDocument: func.Out[func.Document]):
    """
    Esta função é acionada sempre que uma nova mensagem de telemetria chega ao Hub IoT.
    - Processa a mensagem.
    - Salva os dados no Cosmos DB através de um Output Binding.
    - Aplica uma regra de negócio (verificar temperatura).
    - Envia um comando de volta ao dispositivo (C2D) se necessário.
    """
    try:
        # 1. Decodificar a mensagem recebida do Hub IoT
        body = event.get_body().decode('utf-8')
        telemetry_data = json.loads(body)
        logging.info(f'Python EventHub trigger processou uma mensagem: {telemetry_data}')

        device_id = telemetry_data.get("deviceId")
        temperature = telemetry_data.get("temperature")

        if not device_id or temperature is None:
            logging.error(f"Mensagem inválida recebida: {telemetry_data}")
            return

        # 2. Adicionar um ID único e preparar para salvar no Cosmos DB
        # O Output Binding 'outputDocument' cuidará da persistência dos dados.
        telemetry_data['id'] = str(uuid.uuid4())
        outputDocument.set(func.Document.from_dict(telemetry_data))
        logging.info(f"Dados para o dispositivo '{device_id}' enviados para o Cosmos DB.")

        # 3. Aplicar a lógica de negócio (Regra de Temperatura)
        if temperature > TEMPERATURE_THRESHOLD:
            logging.warning(f"ALERTA: Temperatura ({temperature}°C) acima do limite para o dispositivo '{device_id}'!")
            
            # 4. Enviar um comando de volta para o dispositivo (Cloud-to-Device)
            command_message = "LIGAR_AC"
            
            # Usamos o SDK de gerenciamento do Hub IoT para enviar comandos
            registry_manager = IoTHubRegistryManager.from_connection_string(IOTHUB_SERVICE_CONNECTION_STRING)
            
            logging.info(f"Enviando comando '{command_message}' para o dispositivo '{device_id}'.")
            registry_manager.send_c2d_message(device_id, command_message)
            
    except json.JSONDecodeError:
        logging.error(f"Erro ao decodificar JSON: {event.get_body().decode('utf-8')}")
    except Exception as e:
        logging.error(f"Erro inesperado ao processar a mensagem: {e}")