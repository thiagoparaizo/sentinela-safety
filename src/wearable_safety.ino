/*
 * SISTEMA WEARABLE PARA DETECÇÃO DE QUEDAS EM AMBIENTES INDUSTRIAIS
 * 
 * Projeto: Challenge Reply - Fase 4 
 * Objetivo: Monitoramento de segurança do trabalhador
 * Hardware: ESP32 + MPU6050 + LED + Buzzer
 * 
 * Desenvolvido para simulação no Wokwi
 * Data: Junho 2025
 */

#include <Wire.h>
#include <Arduino.h>


// Configurações do MPU6050
const int MPU_addr = 0x68;  // Endereço I2C do MPU6050

// Pinos de saída
const int LED_ALERTA = 2;
const int BUZZER = 4;

// Variáveis para dados do sensor
int16_t AcX, AcY, AcZ, Tmp, GyX, GyY, GyZ;
float ax_g, ay_g, az_g;
float accel_magnitude;

// Parâmetros do algoritmo de detecção de queda
const float THRESHOLD_FREEFALL = 0.5;     // Limiar de queda livre (g)
const float THRESHOLD_IMPACT = 1.8;       // Limiar de impacto (g) - REDUZIDO para Wokwi
const unsigned long MIN_FREEFALL_TIME = 100;  // Tempo mínimo de queda livre (ms)
const unsigned long MAX_FREEFALL_TIME = 2000; // Tempo máximo para reset (ms)

// Estado do sistema de detecção
bool in_freefall = false;
unsigned long freefall_start_time = 0;
int fall_count = 0;

// Buffer para armazenamento de dados
struct SensorReading {
  unsigned long timestamp;
  float ax, ay, az;
  float magnitude;
  bool fall_detected;
};

const int BUFFER_SIZE = 50;
SensorReading data_buffer[BUFFER_SIZE];
int buffer_index = 0;

void setup() {
  // Inicializar comunicação serial
  Serial.begin(115200);
  while (!Serial) delay(10);
  
  // Inicializar I2C
  Wire.begin();
  Wire.beginTransmission(MPU_addr);
  Wire.write(0x6B);  // PWR_MGMT_1 register
  Wire.write(0);     // Acordar o MPU6050
  Wire.endTransmission(true);
  
  // Configurar pinos de saída
  pinMode(LED_ALERTA, OUTPUT);
  pinMode(BUZZER, OUTPUT);
  
  // Teste inicial dos componentes
  testComponents();
  
  // Cabeçalho para dados CSV
  Serial.println("=== SISTEMA WEARABLE DE SEGURANÇA INDUSTRIAL ===");
  Serial.println("Inicializando monitoramento de quedas...");
  Serial.println();
  Serial.println("Timestamp(ms),Ax(g),Ay(g),Az(g),Magnitude(g),Queda,Status");
  
  delay(1000);
}

void loop() {
  // Ler dados do MPU6050
  readMPU6050();
  
  // Converter para unidades g (gravidade)
  ax_g = AcX / 16384.0;
  ay_g = AcY / 16384.0;
  az_g = AcZ / 16384.0;
  
  // Calcular magnitude do vetor aceleração
  accel_magnitude = sqrt(ax_g*ax_g + ay_g*ay_g + az_g*az_g);
  
  // Executar algoritmo de detecção de queda
  bool fall_detected = detectFall();
  
  // Armazenar dados no buffer
  storeSensorData(millis(), ax_g, ay_g, az_g, accel_magnitude, fall_detected);
  
  // Enviar dados formatados para o Monitor Serial
  printSensorData(fall_detected);
  
  // Acionar alerta se queda detectada
  if (fall_detected) {
    triggerEmergencyAlert();
    fall_count++;
  }
  
  // Delay para controlar taxa de amostragem (20Hz)
  delay(50);
}

void readMPU6050() {
  Wire.beginTransmission(MPU_addr);
  Wire.write(0x3B);  // Começar no registro ACCEL_XOUT_H
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_addr, 14, true);  // Solicitar 14 bytes
  
  AcX = Wire.read() << 8 | Wire.read();  // 0x3B (ACCEL_XOUT_H) & 0x3C (ACCEL_XOUT_L)
  AcY = Wire.read() << 8 | Wire.read();  // 0x3D (ACCEL_YOUT_H) & 0x3E (ACCEL_YOUT_L)
  AcZ = Wire.read() << 8 | Wire.read();  // 0x3F (ACCEL_ZOUT_H) & 0x40 (ACCEL_ZOUT_L)
  Tmp = Wire.read() << 8 | Wire.read();  // 0x41 (TEMP_OUT_H) & 0x42 (TEMP_OUT_L)
  GyX = Wire.read() << 8 | Wire.read();  // 0x43 (GYRO_XOUT_H) & 0x44 (GYRO_XOUT_L)
  GyY = Wire.read() << 8 | Wire.read();  // 0x45 (GYRO_YOUT_H) & 0x46 (GYRO_YOUT_L)
  GyZ = Wire.read() << 8 | Wire.read();  // 0x47 (GYRO_ZOUT_H) & 0x48 (GYRO_ZOUT_L)
}

bool detectFall() {
  unsigned long current_time = millis();
  
  // Etapa 1: Detectar início de queda livre (baixa aceleração)
  if (accel_magnitude < THRESHOLD_FREEFALL && !in_freefall) {
    in_freefall = true;
    freefall_start_time = current_time;
    return false;
  }
  
  // Etapa 2: Detectar impacto após período de queda livre
  if (in_freefall && accel_magnitude > THRESHOLD_IMPACT) {
    unsigned long freefall_duration = current_time - freefall_start_time;
    
    // Verificar se duração da queda livre está dentro dos parâmetros
    if (freefall_duration >= MIN_FREEFALL_TIME) {
      in_freefall = false;
      return true;  // QUEDA CONFIRMADA!
    }
  }
  
  // Reset automático se queda livre durar muito tempo
  if (in_freefall && (current_time - freefall_start_time) > MAX_FREEFALL_TIME) {
    in_freefall = false;
  }
  
  return false;
}

void storeSensorData(unsigned long timestamp, float ax, float ay, float az, float magnitude, bool fall) {
  data_buffer[buffer_index] = {timestamp, ax, ay, az, magnitude, fall};
  buffer_index = (buffer_index + 1) % BUFFER_SIZE;
}

void printSensorData(bool fall_detected) {
  // Formato CSV para fácil análise
  Serial.print(millis());
  Serial.print(",");
  Serial.print(ax_g, 3);
  Serial.print(",");
  Serial.print(ay_g, 3);
  Serial.print(",");
  Serial.print(az_g, 3);
  Serial.print(",");
  Serial.print(accel_magnitude, 3);
  Serial.print(",");
  Serial.print(fall_detected ? "1" : "0");
  Serial.print(",");
  
  // Status descritivo
  if (fall_detected) {
    Serial.println("QUEDA_DETECTADA!");
  } else if (in_freefall) {
    Serial.println("QUEDA_LIVRE");
  } else if (accel_magnitude > 1.5) {
    Serial.println("MOVIMENTO");
  } else {
    Serial.println("NORMAL");
  }
}

void triggerEmergencyAlert() {
  // Mensagem de emergência destacada
  Serial.println();
  Serial.println("🚨🚨🚨 ALERTA DE EMERGÊNCIA 🚨🚨🚨");
  Serial.println("QUEDA DE TRABALHADOR DETECTADA!");
  Serial.print("Timestamp: ");
  Serial.println(millis());
  Serial.print("Magnitude do Impacto: ");
  Serial.print(accel_magnitude, 2);
  Serial.println("g");
  Serial.print("Total de Quedas Detectadas: ");
  Serial.println(fall_count + 1);
  Serial.println("Acionando protocolo de segurança...");
  Serial.println();
  
  // Sequência de alerta visual e sonoro
  for (int i = 0; i < 5; i++) {
    // Alerta intenso
    digitalWrite(LED_ALERTA, HIGH);
    digitalWrite(BUZZER, HIGH);
    delay(200);
    
    digitalWrite(LED_ALERTA, LOW);
    digitalWrite(BUZZER, LOW);
    delay(100);
    
    // Alerta rápido  
    digitalWrite(LED_ALERTA, HIGH);
    digitalWrite(BUZZER, HIGH);
    delay(100);
    
    digitalWrite(LED_ALERTA, LOW);
    digitalWrite(BUZZER, LOW);
    delay(100);
  }
  
  // Pausa antes de continuar monitoramento
  delay(1000);
}

void testComponents() {
  Serial.println("Testando componentes do sistema...");
  
  // Teste do LED
  Serial.print("LED de Alerta: ");
  digitalWrite(LED_ALERTA, HIGH);
  delay(500);
  digitalWrite(LED_ALERTA, LOW);
  Serial.println("OK");
  
  // Teste do Buzzer
  Serial.print("Buzzer: ");
  digitalWrite(BUZZER, HIGH);
  delay(200);
  digitalWrite(BUZZER, LOW);
  Serial.println("OK");
  
  // Teste da comunicação I2C com MPU6050
  Serial.print("MPU6050: ");
  Wire.beginTransmission(MPU_addr);
  byte error = Wire.endTransmission();
  
  if (error == 0) {
    Serial.println("OK");
  } else {
    Serial.println("ERRO - Sensor não encontrado!");
  }
  
  Serial.println("Sistema pronto para operação!");
  Serial.println();
}

void printStatistics() {
  // Função para imprimir estatísticas do sistema
  // (pode ser chamada periodicamente ou via comando serial)
  
  Serial.println("=== ESTATÍSTICAS DO SISTEMA ===");
  Serial.print("Tempo de Operação: ");
  Serial.print(millis() / 1000);
  Serial.println(" segundos");
  
  Serial.print("Total de Quedas Detectadas: ");
  Serial.println(fall_count);
  
  Serial.print("Taxa de Amostragem: ");
  Serial.println("20 Hz (50ms)");
  
  Serial.print("Threshold Queda Livre: ");
  Serial.print(THRESHOLD_FREEFALL);
  Serial.println("g");
  
  Serial.print("Threshold Impacto: ");
  Serial.print(THRESHOLD_IMPACT);
  Serial.println("g");
  
  Serial.println("===============================");
}