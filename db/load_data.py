#!/usr/bin/env python3
"""
CARGA DE DADOS NO BANCO
"""

import sqlite3
import pandas as pd
from datetime import datetime


def conectar_banco_sqlite(db_path='sentinela.db'):
    return sqlite3.connect(db_path)

def criar_banco_sqlite(db_path='sentinela.db'):
    """Cria o banco SQLite e estrutura inicial"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Executar schema SQL
    with open('db/schema.sql', 'r') as f:
        schema = f.read()
        # Executar cada comando separadamente
        for statement in schema.split(';'):
            if statement.strip():
                try:
                    cursor.execute(statement)
                except sqlite3.OperationalError as e:
                    if 'already exists' not in str(e):
                        print(f"Erro: {e}")
    
    conn.commit()
    return conn

def carregar_dados_csv(conn, csv_path='data/sample_data.csv'):
    """Carrega dados do CSV para o banco"""
    
    # Ler CSV
    df = pd.read_csv(csv_path)
    print(f"Lendo {len(df)} registros do CSV...")
    
    cursor = conn.cursor()
    
    # Inserir trabalhador e dispositivo padrão se não existirem
    cursor.execute("""
        INSERT OR IGNORE INTO trabalhadores (id_trabalhador, nome, matricula, setor) 
        VALUES (1, 'João Silva', 'TRB001', 'Produção')
    """)
    
    cursor.execute("""
        INSERT OR IGNORE INTO dispositivos (id_dispositivo, serial_number, modelo, status) 
        VALUES (1, 'ESP32-WRB-001', 'ESP32-WROOM', 'ativo')
    """)
    
    # Inserir leituras
    id_leitura = 1
    eventos_queda = []
    
    for idx, row in df.iterrows():
        queda_detectada = 1 if row['Queda'] == 1 else 0
        
        cursor.execute("""
            INSERT INTO leituras_sensores 
            (id_leitura, id_trabalhador, id_dispositivo, timestamp_ms, 
             aceleracao_x, aceleracao_y, aceleracao_z, magnitude, 
             status_movimento, queda_detectada)
            VALUES (?, 1, 1, ?, ?, ?, ?, ?, ?, ?)
        """, (id_leitura, row['Timestamp(ms)'], row['Ax(g)'], row['Ay(g)'], 
              row['Az(g)'], row['Magnitude(g)'], row['Status'], queda_detectada))
        
        # Se foi queda, criar evento
        if queda_detectada:
            eventos_queda.append({
                'id_leitura': id_leitura,
                'timestamp': row['Timestamp(ms)'],
                'magnitude': row['Magnitude(g)']
            })
        
        id_leitura += 1
    
    # Inserir eventos de queda
    id_evento = 1
    for evento in eventos_queda:
        # Determinar gravidade baseado na magnitude
        if evento['magnitude'] >= 3.0:
            gravidade = 'grave'
        elif evento['magnitude'] >= 2.0:
            gravidade = 'moderada'
        else:
            gravidade = 'leve'
        
        cursor.execute("""
            INSERT INTO eventos_queda 
            (id_evento, id_leitura, id_trabalhador, timestamp_queda, 
             magnitude_impacto, gravidade, status_atendimento, tempo_resposta_segundos)
            VALUES (?, ?, 1, ?, ?, ?, 'pendente', ?)
        """, (id_evento, evento['id_leitura'], evento['timestamp'], 
              evento['magnitude'], gravidade, 250))
        
        # Criar alerta para quedas graves
        if gravidade in ['grave', 'moderada']:
            nivel = 'critica' if gravidade == 'grave' else 'alta'
            cursor.execute("""
                INSERT INTO alertas 
                (id_alerta, id_evento, tipo_alerta, nivel_prioridade, mensagem, enviado)
                VALUES (?, ?, 'queda', ?, ?, FALSE)
            """, (id_evento, id_evento, nivel, 
                  f'ALERTA: Queda detectada com magnitude {evento["magnitude"]:.2f}g'))
        
        id_evento += 1
    
    conn.commit()
    print(f"✅ Carregados {id_leitura-1} leituras e {len(eventos_queda)} eventos de queda")

def consultas_analise(conn):
    """Executa consultas para análise"""
    
    queries = {
        'Total de Leituras': "SELECT COUNT(*) FROM leituras_sensores",
        'Total de Quedas': "SELECT COUNT(*) FROM eventos_queda",
        'Alertas Críticos': "SELECT COUNT(*) FROM alertas WHERE nivel_prioridade = 'critica'",
        'Magnitude Média nas Quedas': "SELECT AVG(magnitude_impacto) FROM eventos_queda",
        'Magnitude Máxima': "SELECT MAX(magnitude_impacto) FROM eventos_queda"
    }
    
    print("\n" + "="*50)
    print("ESTATÍSTICAS DO BANCO DE DADOS")
    print("="*50)
    
    for nome, query in queries.items():
        resultado = pd.read_sql_query(query, conn).iloc[0, 0]
        print(f"{nome}: {resultado}")
    
    # Distribuição de status
    df_status = pd.read_sql_query("""
        SELECT status_movimento, COUNT(*) as total 
        FROM leituras_sensores 
        GROUP BY status_movimento
    """, conn)
    
    print("\nDistribuição de Status:")
    print(df_status.to_string(index=False))
    
    # Quedas por gravidade
    df_gravidade = pd.read_sql_query("""
        SELECT gravidade, COUNT(*) as total 
        FROM eventos_queda 
        GROUP BY gravidade
    """, conn)
    
    print("\nQuedas por Gravidade:")
    print(df_gravidade.to_string(index=False))

if __name__ == "__main__":
    print("🔧 Iniciando carga de dados no banco...")
    
    # Conectar ao banco
    conn = conectar_banco_sqlite()
    
    # Criar banco
    ##conn = criar_banco_sqlite()
    
    # Carregar dados
    carregar_dados_csv(conn)
    
    # Análises
    consultas_analise(conn)
    
    conn.close()
    print("\n✅ Processo concluído!")