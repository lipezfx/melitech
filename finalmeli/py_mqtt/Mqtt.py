import serial
import paho.mqtt.client as mqtt
import time
import re

# --- Configurações da Serial ---
SERIAL_PORT = 'COM8'
BAUD_RATE = 115200

# --- Configurações do MQTT ---
MQTT_SERVER = "localhost"
MQTT_PORT = 1883

# Tópicos MQTT
TOPIC_DHT_TEMPERATURE = "dht/temperatura"
TOPIC_HUMIDITY = "dht/umidade"
TOPIC_SECOND_TEMPERATURE = "b20/temperatura"  # Tópico para o DS18B20

# Padrão Regex para extrair números (float ou int)
VALUE_PATTERN = re.compile(r"[-+]?\d*\.?\d+")


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Conectado ao broker MQTT!")
    else:
        print(f"Falha na conexão, código de retorno: {rc}")


def extract_value(line):
    """
    Extrai o último valor numérico da string.
    Isso evita pegar o '22' do texto 'DHT22' em vez da temperatura real.
    """
    matches = VALUE_PATTERN.findall(line)
    if matches:
        return matches[-1]  # pega o último número da linha
    return None


# --- Configuração e Conexão MQTT ---
client = mqtt.Client()
client.on_connect = on_connect

try:
    client.connect(MQTT_SERVER, MQTT_PORT, 60)
except Exception as e:
    print(f"Não foi possível conectar ao broker MQTT: {e}")
    exit()

client.loop_start()

# --- Configuração e Conexão Serial ---
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=5)
    print(f"Conectado à porta serial {SERIAL_PORT}")
except serial.SerialException as e:
    print(f"Erro ao conectar à porta serial: {e}")
    client.loop_stop()
    exit()

# Loop principal para ler a serial e publicar no MQTT
print("Iniciando loop de leitura e publicação...")
try:
    while True:
        if ser.in_waiting > 0:
            # Leitura, decodificação e limpeza da linha
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            print(f"Dados recebidos do Arduino: {line}")

            # Extrai o valor correto (último número encontrado)
            value_str = extract_value(line)

            if value_str:
                # --- Lógica de Publicação ---
                if "(DS18B20):" in line:
                    topic = TOPIC_SECOND_TEMPERATURE
                    client.publish(topic, value_str)
                    print(f"[OK] Publicado: {topic} -> {value_str}")

                elif "(DHT22):" in line:
                    topic = TOPIC_DHT_TEMPERATURE
                    client.publish(topic, value_str)
                    print(f"[OK] Publicado: {topic} -> {value_str}")

                elif "Umidade:" in line:
                    topic = TOPIC_HUMIDITY
                    client.publish(topic, value_str)
                    print(f"[OK] Publicado: {topic} -> {value_str}")

                else:
                    # Linhas irrelevantes (ex: separadores "---")
                    pass

        time.sleep(0.1)

except serial.SerialException as e:
    print(f"Erro de comunicação serial: {e}")
except KeyboardInterrupt:
    print("\nEncerrado pelo usuário.")
except Exception as e:
    print(f"Ocorreu um erro inesperado: {e}")

finally:
    # Limpeza final
    print("Desconectando e encerrando...")
    if 'ser' in locals() and ser.is_open:
        ser.close()
    client.loop_stop()
    client.disconnect()
