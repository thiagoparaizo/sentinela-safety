-- =====================================================
-- BANCO DE DADOS - SENTINELA
-- =====================================================

-- Tabela de Trabalhadores
CREATE TABLE trabalhadores (
    id_trabalhador INTEGER PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    matricula VARCHAR(20) UNIQUE NOT NULL,
    setor VARCHAR(50),
    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de Dispositivos Wearable
CREATE TABLE dispositivos (
    id_dispositivo INTEGER PRIMARY KEY,
    serial_number VARCHAR(50) UNIQUE NOT NULL,
    modelo VARCHAR(50),
    status VARCHAR(20) CHECK (status IN ('ativo', 'inativo', 'manutencao')),
    data_instalacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de Leituras dos Sensores
CREATE TABLE leituras_sensores (
    id_leitura INTEGER PRIMARY KEY,
    id_trabalhador INTEGER,
    id_dispositivo INTEGER,
    timestamp_ms BIGINT NOT NULL,
    aceleracao_x DECIMAL(10,3),
    aceleracao_y DECIMAL(10,3),
    aceleracao_z DECIMAL(10,3),
    magnitude DECIMAL(10,3),
    status_movimento VARCHAR(20) CHECK (status_movimento IN ('NORMAL', 'MOVIMENTO', 'QUEDA_LIVRE', 'QUEDA_DETECTADA')),
    queda_detectada BOOLEAN DEFAULT FALSE,
    data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_trabalhador) REFERENCES trabalhadores(id_trabalhador),
    FOREIGN KEY (id_dispositivo) REFERENCES dispositivos(id_dispositivo)
);

-- Tabela de Eventos de Queda
CREATE TABLE eventos_queda (
    id_evento INTEGER PRIMARY KEY,
    id_leitura INTEGER,
    id_trabalhador INTEGER,
    timestamp_queda BIGINT NOT NULL,
    magnitude_impacto DECIMAL(10,3),
    localizacao VARCHAR(100),
    gravidade VARCHAR(20) CHECK (gravidade IN ('leve', 'moderada', 'grave')),
    status_atendimento VARCHAR(30) CHECK (status_atendimento IN ('pendente', 'em_atendimento', 'finalizado')),
    tempo_resposta_segundos INTEGER,
    data_evento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_leitura) REFERENCES leituras_sensores(id_leitura),
    FOREIGN KEY (id_trabalhador) REFERENCES trabalhadores(id_trabalhador)
);

-- Tabela de Alertas
CREATE TABLE alertas (
    id_alerta INTEGER PRIMARY KEY,
    id_evento INTEGER,
    tipo_alerta VARCHAR(30) CHECK (tipo_alerta IN ('queda', 'queda_livre', 'impacto_alto')),
    nivel_prioridade VARCHAR(20) CHECK (nivel_prioridade IN ('baixa', 'media', 'alta', 'critica')),
    mensagem TEXT,
    enviado BOOLEAN DEFAULT FALSE,
    data_alerta TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_evento) REFERENCES eventos_queda(id_evento)
);

-- Índices para otimização de consultas
CREATE INDEX idx_leituras_timestamp ON leituras_sensores(timestamp_ms);
CREATE INDEX idx_leituras_trabalhador ON leituras_sensores(id_trabalhador);
CREATE INDEX idx_leituras_queda ON leituras_sensores(queda_detectada);
CREATE INDEX idx_eventos_timestamp ON eventos_queda(timestamp_queda);
CREATE INDEX idx_alertas_prioridade ON alertas(nivel_prioridade);

-- =====================================================
-- SCRIPT DE CARGA DE DADOS DE EXEMPLO
-- =====================================================

-- Inserir trabalhadores de exemplo
INSERT INTO trabalhadores (id_trabalhador, nome, matricula, setor) VALUES
(1, 'João Silva', 'TRB001', 'Produção'),
(2, 'Maria Santos', 'TRB002', 'Manutenção'),
(3, 'Pedro Costa', 'TRB003', 'Logística');

-- Inserir dispositivos
INSERT INTO dispositivos (id_dispositivo, serial_number, modelo, status) VALUES
(1, 'ESP32-WRB-001', 'ESP32-WROOM', 'ativo'),
(2, 'ESP32-WRB-002', 'ESP32-WROOM', 'ativo'),
(3, 'ESP32-WRB-003', 'ESP32-WROOM', 'manutencao');

-- Consultas úteis para análise
-- 1. Total de quedas por trabalhador
CREATE VIEW vw_quedas_por_trabalhador AS
SELECT 
    t.nome,
    t.matricula,
    t.setor,
    COUNT(e.id_evento) as total_quedas,
    AVG(e.magnitude_impacto) as magnitude_media,
    MAX(e.magnitude_impacto) as magnitude_maxima
FROM trabalhadores t
LEFT JOIN eventos_queda e ON t.id_trabalhador = e.id_trabalhador
GROUP BY t.id_trabalhador, t.nome, t.matricula, t.setor;

-- 2. Leituras com status crítico
CREATE VIEW vw_leituras_criticas AS
SELECT 
    l.id_leitura,
    t.nome as trabalhador,
    l.magnitude,
    l.status_movimento,
    l.timestamp_ms,
    l.data_registro
FROM leituras_sensores l
JOIN trabalhadores t ON l.id_trabalhador = t.id_trabalhador
WHERE l.queda_detectada = TRUE OR l.magnitude > 2.0
ORDER BY l.timestamp_ms DESC;

-- 3. Alertas pendentes de alta prioridade
CREATE VIEW vw_alertas_pendentes AS
SELECT 
    a.id_alerta,
    a.tipo_alerta,
    a.nivel_prioridade,
    a.mensagem,
    t.nome as trabalhador,
    e.magnitude_impacto,
    a.data_alerta
FROM alertas a
JOIN eventos_queda e ON a.id_evento = e.id_evento
JOIN trabalhadores t ON e.id_trabalhador = t.id_trabalhador
WHERE a.enviado = FALSE AND a.nivel_prioridade IN ('alta', 'critica')
ORDER BY a.data_alerta DESC;