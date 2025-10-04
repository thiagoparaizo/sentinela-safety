#!/usr/bin/env python3
"""
MODELO DE MACHINE LEARNING - SENTINELA SAFETY - DETECÇÃO DE QUEDAS
Sprint 3/4 - Challenge Reply
"""

import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.preprocessing import StandardScaler
import joblib

class FallDetectionML:
    def __init__(self, db_path='sentinela.db'):
        self.db_path = db_path
        self.model = None
        self.scaler = StandardScaler()
        
    def carregar_dados(self):
        """Carrega dados do banco SQLite"""
        conn = sqlite3.connect(self.db_path)
        
        query = """
        SELECT 
            aceleracao_x, aceleracao_y, aceleracao_z, 
            magnitude, queda_detectada
        FROM leituras_sensores
        WHERE aceleracao_x IS NOT NULL
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        print(f"📊 Dados carregados: {len(df)} registros")
        print(f"   - Quedas: {df['queda_detectada'].sum()}")
        print(f"   - Normal: {len(df) - df['queda_detectada'].sum()}")
        
        return df
    
    def criar_features(self, df):
        """Cria features adicionais para o modelo"""
        
        # Features derivadas
        df['accel_diff'] = df['magnitude'].diff().fillna(0)
        df['accel_std'] = df['magnitude'].rolling(window=5, min_periods=1).std().fillna(0)
        df['accel_max'] = df['magnitude'].rolling(window=5, min_periods=1).max().fillna(0)
        df['accel_min'] = df['magnitude'].rolling(window=5, min_periods=1).min().fillna(0)
        
        # Features angulares
        df['angle_xy'] = np.arctan2(df['aceleracao_y'], df['aceleracao_x'])
        df['angle_xz'] = np.arctan2(df['aceleracao_z'], df['aceleracao_x'])
        
        return df
    
    def treinar_modelo(self):
        """Treina o modelo Random Forest"""
        
        # Carregar dados
        df = self.carregar_dados()
        df = self.criar_features(df)
        
        # Preparar features e target
        feature_cols = ['aceleracao_x', 'aceleracao_y', 'aceleracao_z', 
                       'magnitude', 'accel_diff', 'accel_std', 
                       'accel_max', 'accel_min', 'angle_xy', 'angle_xz']
        
        X = df[feature_cols]
        y = df['queda_detectada']
        
        # Split treino/teste
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.3, random_state=42, stratify=y
        )
        
        # Normalizar features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Treinar Random Forest
        print("\n🤖 Treinando modelo Random Forest...")
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            random_state=42,
            class_weight='balanced'
        )
        
        self.model.fit(X_train_scaled, y_train)
        
        # Predições
        y_pred = self.model.predict(X_test_scaled)
        
        # Métricas
        accuracy = accuracy_score(y_test, y_pred)
        print(f"\n✅ Modelo treinado!")
        print(f"   Acurácia: {accuracy:.2%}")
        
        # Report detalhado
        print("\n📈 Classification Report:")
        print(classification_report(y_test, y_pred, 
                                    target_names=['Normal', 'Queda']))
        
        # Salvar modelo
        joblib.dump(self.model, 'ml/fall_detection_model.pkl')
        joblib.dump(self.scaler, 'ml/scaler.pkl')
        print("\n💾 Modelo salvo em: ml/fall_detection_model.pkl")
        
        return X_test_scaled, y_test, y_pred, feature_cols
    
    def visualizar_resultados(self, X_test, y_test, y_pred, feature_cols):
        """Gera visualizações dos resultados"""
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        
        # 1. Matriz de Confusão
        cm = confusion_matrix(y_test, y_pred)
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                   xticklabels=['Normal', 'Queda'],
                   yticklabels=['Normal', 'Queda'], ax=axes[0, 0])
        axes[0, 0].set_title('Matriz de Confusão', fontsize=14, fontweight='bold')
        axes[0, 0].set_ylabel('Real')
        axes[0, 0].set_xlabel('Predito')
        
        # 2. Feature Importance
        importances = self.model.feature_importances_
        indices = np.argsort(importances)[::-1][:10]
        
        axes[0, 1].barh(range(len(indices)), importances[indices])
        axes[0, 1].set_yticks(range(len(indices)))
        axes[0, 1].set_yticklabels([feature_cols[i] for i in indices])
        axes[0, 1].set_title('Top 10 Features Importantes', fontsize=14, fontweight='bold')
        axes[0, 1].set_xlabel('Importância')
        
        # 3. Distribuição de Predições
        pred_df = pd.DataFrame({
            'Real': y_test.values,
            'Predito': y_pred
        })
        
        pred_counts = pred_df.groupby(['Real', 'Predito']).size().unstack(fill_value=0)
        pred_counts.plot(kind='bar', ax=axes[1, 0], color=['#2ecc71', '#e74c3c'])
        axes[1, 0].set_title('Distribuição: Real vs Predito', fontsize=14, fontweight='bold')
        axes[1, 0].set_xlabel('Classe Real')
        axes[1, 0].set_ylabel('Quantidade')
        axes[1, 0].legend(['Normal', 'Queda'])
        axes[1, 0].set_xticklabels(['Normal', 'Queda'], rotation=0)
        
        # 4. Métricas Resumidas
        accuracy = accuracy_score(y_test, y_pred)
        tn, fp, fn, tp = cm.ravel()
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        metrics_text = f"""
MÉTRICAS DO MODELO

Acurácia Geral: {accuracy:.2%}

Classe: QUEDA
• Precisão: {precision:.2%}
• Recall: {recall:.2%}
• F1-Score: {f1:.2%}

Matriz de Confusão:
• Verdadeiros Negativos: {tn}
• Falsos Positivos: {fp}
• Falsos Negativos: {fn}
• Verdadeiros Positivos: {tp}

Total de Amostras Teste: {len(y_test)}
"""
        
        axes[1, 1].text(0.1, 0.5, metrics_text, transform=axes[1, 1].transAxes,
                       fontsize=11, verticalalignment='center',
                       bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8),
                       family='monospace')
        axes[1, 1].axis('off')
        axes[1, 1].set_title('Resumo de Métricas', fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig('ml/model_results.png', dpi=300, bbox_inches='tight')
        print("\n📊 Gráficos salvos em: ml/model_results.png")
        plt.show()
    
    def prever_nova_leitura(self, accel_x, accel_y, accel_z):
        """Faz predição para uma nova leitura"""
        
        magnitude = np.sqrt(accel_x**2 + accel_y**2 + accel_z**2)
        
        # Criar features (simplificado para uma única leitura)
        features = np.array([[
            accel_x, accel_y, accel_z, magnitude,
            0, 0, magnitude, magnitude,  # Features simplificadas
            np.arctan2(accel_y, accel_x),
            np.arctan2(accel_z, accel_x)
        ]])
        
        features_scaled = self.scaler.transform(features)
        pred = self.model.predict(features_scaled)[0]
        proba = self.model.predict_proba(features_scaled)[0]
        
        return {
            'queda': bool(pred),
            'probabilidade_queda': proba[1],
            'magnitude': magnitude
        }

if __name__ == "__main__":
    print("🚀 Iniciando treinamento do modelo ML...")
    
    # Criar e treinar modelo
    ml = FallDetectionML()
    X_test, y_test, y_pred, features = ml.treinar_modelo()
    
    # Visualizar resultados
    ml.visualizar_resultados(X_test, y_test, y_pred, features)
    
    # Teste de predição
    print("\n🧪 Teste de Predição:")
    resultado = ml.prever_nova_leitura(2.0, 0.3, 0.3)
    print(f"   Queda detectada: {resultado['queda']}")
    print(f"   Probabilidade: {resultado['probabilidade_queda']:.2%}")
    print(f"   Magnitude: {resultado['magnitude']:.2f}g")
    
    print("\n✅ Processo ML concluído!")