#!/usr/bin/env python3
"""
PIPELINE DE INTEGRAÇÃO COMPLETO
Sprint 4 - Challenge Reply

Este script executa todo o fluxo integrado:
1. Cria o banco de dados
2. Carrega dados do ESP32/simulação
3. Treina o modelo ML
4. Gera relatórios e alertas
"""

import os
import sys
import subprocess
from pathlib import Path

class PipelineIntegrado:
    def __init__(self):
        self.base_path = Path.cwd()
        self.passos_concluidos = []
        
    def criar_estrutura_pastas(self):
        """Cria estrutura de pastas necessária"""
        print("📁 Criando estrutura de pastas...")
        
        pastas = ['db', 'ml', 'dashboard', 'logs']
        for pasta in pastas:
            Path(pasta).mkdir(exist_ok=True)
            print(f"   ✓ {pasta}/")
        
        self.passos_concluidos.append("Estrutura de pastas criada")
    
    def executar_sql_schema(self):
        """Executa script SQL de criação do banco"""
        print("\n🗄️ Criando estrutura do banco de dados...")
        
        import sqlite3
        
        # Ler schema SQL
        with open('db/schema.sql', 'r', encoding='utf-8') as f:
            schema = f.read()
        
        # Criar banco
        from db.load_data import criar_banco_sqlite, criar_banco_sqlite
        import mysql.connector
        conn = criar_banco_sqlite()
        cursor = conn.cursor()
        
        for statement in schema.split(';'):
            if statement.strip():
                try:
                    cursor.execute(statement)
                except mysql.connector.errors.DatabaseError as e:
                    if 'already exists' not in str(e):
                        print(f"   ⚠️ Aviso: {e}")
        
        conn.commit()
        conn.close()
        
        print("   ✓ Banco de dados criado: sentinela.db")
        self.passos_concluidos.append("Banco de dados criado")
    
    def carregar_dados(self):
        """Carrega dados do CSV para o banco"""
        print("\n📊 Carregando dados no banco...")
        
        try:
            # Importar e executar loader
            sys.path.insert(0, str(self.base_path))
            from db.load_data import carregar_dados_csv, conectar_banco_mysql, criar_banco_sqlite, consultas_analise
            
            conn = conectar_banco_mysql()
            #conn = criar_banco_sqlite('sentinela.db')
            carregar_dados_csv(conn, 'data/sample_data.csv')
            consultas_analise(conn)
            conn.close()
            
            print("   ✓ Dados carregados com sucesso")
            self.passos_concluidos.append("Dados carregados no banco")
            
        except Exception as e:
            print(f"   ❌ Erro: {e}")
            return False
        
        return True
    
    def treinar_modelo_ml(self):
        """Treina modelo de Machine Learning"""
        print("\n🤖 Treinando modelo de Machine Learning...")
        
        try:
            from ml.train_model import FallDetectionML
            
            ml = FallDetectionML()
            X_test, y_test, y_pred, features = ml.treinar_modelo()
            ml.visualizar_resultados(X_test, y_test, y_pred, features)
            
            print("   ✓ Modelo treinado e salvo")
            self.passos_concluidos.append("Modelo ML treinado")
            
        except Exception as e:
            print(f"   ❌ Erro: {e}")
            return False
        
        return True
    
    def gerar_relatorio_alertas(self):
        """Gera relatório de alertas"""
        print("\n📄 Gerando relatório de alertas...")
        
        import sqlite3
        import pandas as pd
        from datetime import datetime
        
        from db.load_data import conectar_banco_mysql
        conn = conectar_banco_mysql()
        
        # Buscar alertas críticos
        df_alertas = pd.read_sql_query("""
            SELECT a.*, e.magnitude_impacto, t.nome, t.setor
            FROM alertas a
            JOIN eventos_queda e ON a.id_evento = e.id_evento
            JOIN trabalhadores t ON e.id_trabalhador = t.id_trabalhador
            WHERE a.nivel_prioridade IN ('critica', 'alta')
            ORDER BY a.data_alerta DESC
        """, conn)
        
        conn.close()
        
        # Gerar relatório
        relatorio_path = f"logs/relatorio_alertas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(relatorio_path, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write("RELATÓRIO DE ALERTAS - SISTEMA WEARABLE DE SEGURANÇA\n")
            f.write("="*70 + "\n\n")
            f.write(f"Data de Geração: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n")
            
            f.write(f"TOTAL DE ALERTAS CRÍTICOS/ALTOS: {len(df_alertas)}\n\n")
            
            if len(df_alertas) > 0:
                f.write("DETALHAMENTO DOS ALERTAS:\n")
                f.write("-" * 70 + "\n\n")
                
                for idx, alerta in df_alertas.iterrows():
                    f.write(f"ALERTA #{alerta['id_alerta']}\n")
                    f.write(f"  Tipo: {alerta['tipo_alerta']}\n")
                    f.write(f"  Prioridade: {alerta['nivel_prioridade'].upper()}\n")
                    f.write(f"  Trabalhador: {alerta['nome']} ({alerta['setor']})\n")
                    f.write(f"  Magnitude: {alerta['magnitude_impacto']:.2f}g\n")
                    f.write(f"  Mensagem: {alerta['mensagem']}\n")
                    f.write(f"  Data/Hora: {alerta['data_alerta']}\n")
                    f.write(f"  Status: {'Enviado' if alerta['enviado'] else 'PENDENTE'}\n")
                    f.write("-" * 70 + "\n\n")
            else:
                f.write("✅ Nenhum alerta crítico ou alto no momento.\n")
            
            f.write("\n" + "="*70 + "\n")
            f.write("FIM DO RELATÓRIO\n")
            f.write("="*70 + "\n")
        
        print(f"   ✓ Relatório salvo: {relatorio_path}")
        self.passos_concluidos.append("Relatório de alertas gerado")
        
        return relatorio_path
    
    def verificar_dependencias(self):
        """Verifica se todas as dependências estão instaladas"""
        print("🔍 Verificando dependências...")
        
        dependencias = [
            'pandas', 'numpy', 'matplotlib', 'seaborn',
            'sklearn', 'joblib', 'streamlit', 'plotly'
        ]
        
        faltando = []
        for dep in dependencias:
            try:
                __import__(dep)
                print(f"   ✓ {dep}")
            except ImportError:
                faltando.append(dep)
                print(f"   ❌ {dep}")
        
        if faltando:
            print(f"\n⚠️ Instale as dependências faltantes:")
            print(f"   pip install {' '.join(faltando)}")
            return False
        
        print("   ✓ Todas as dependências OK")
        return True
    
    def iniciar_dashboard(self):
        """Inicia o dashboard Streamlit"""
        print("\n🚀 Iniciando dashboard Streamlit...")
        print("   → O dashboard será aberto no navegador")
        print("   → Pressione Ctrl+C para encerrar\n")
        
        try:
            subprocess.run(['streamlit', 'run', 'dashboard/app.py'])
        except KeyboardInterrupt:
            print("\n👋 Dashboard encerrado")
    
    def executar_pipeline_completo(self):
        """Executa pipeline completo"""
        print("="*70)
        print("🏭 PIPELINE INTEGRADO - SISTEMA WEARABLE DE SEGURANÇA")
        print("="*70)
        print()
        
        # 1. Verificar dependências
        if not self.verificar_dependencias():
            print("\n❌ Pipeline abortado: dependências faltando")
            return False
        
        # 2. Criar estrutura
        self.criar_estrutura_pastas()
        
        # 3. Criar banco
        #self.executar_sql_schema()
        
        # 4. Carregar dados
        if not self.carregar_dados():
            print("\n❌ Pipeline abortado: erro ao carregar dados")
            return False
        
        # 5. Treinar ML
        if not self.treinar_modelo_ml():
            print("\n❌ Pipeline abortado: erro no treinamento ML")
            return False
        
        # 6. Gerar relatório
        relatorio = self.gerar_relatorio_alertas()
        
        # 7. Resumo
        print("\n" + "="*70)
        print("✅ PIPELINE EXECUTADO COM SUCESSO!")
        print("="*70)
        print("\nPASSOS CONCLUÍDOS:")
        for i, passo in enumerate(self.passos_concluidos, 1):
            print(f"   {i}. {passo}")
        
        print("\nARQUIVOS GERADOS:")
        print("   📁 sentinela.db - Banco de dados")
        print("   🤖 ml/fall_detection_model.pkl - Modelo treinado")
        print("   📊 ml/model_results.png - Gráficos de análise")
        print(f"   📄 {relatorio} - Relatório de alertas")
        
        print("\n" + "="*70)
        print("🎯 PRÓXIMOS PASSOS:")
        print("="*70)
        print("   1. Revisar relatório de alertas em: logs/")
        print("   2. Visualizar gráficos ML em: ml/model_results.png")
        print("   3. Iniciar dashboard: streamlit run dashboard/app.py")
        print("   4. Ou executar: python pipeline.py --dashboard")
        print()
        
        return True

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Pipeline Integrado - Sistema Wearable')
    parser.add_argument('--dashboard', action='store_true', 
                       help='Iniciar dashboard após pipeline')
    parser.add_argument('--skip-ml', action='store_true',
                       help='Pular treinamento ML (usar modelo existente)')
    
    args = parser.parse_args()
    
    pipeline = PipelineIntegrado()
    
    if pipeline.executar_pipeline_completo():
        if args.dashboard:
            pipeline.iniciar_dashboard()
    else:
        print("\n❌ Pipeline falhou. Verifique os erros acima.")
        sys.exit(1)

if __name__ == "__main__":
    main()