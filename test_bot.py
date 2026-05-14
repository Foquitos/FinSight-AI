import os
import logging
# Configuramos un log básico para ver qué hace LlamaIndex por detrás
# logging.basicConfig(level=logging.INFO)

# Importamos tu clase finsight
from app.services.Rag_llm.llm import finsight
from app.services.database.database import sqlite_engine
def probar_chatbot():
    print("Iniciando FinSight (Esto puede tardar un poco la primera vez mientras lee y vectoriza los .md)...")
    
    # Instanciamos el bot. 
    # Pasamos sql_engine=sqlite_engine para usar la base de datos SQLite en esta prueba.
    bot = finsight(sql_engine=sqlite_engine, read_only=False)
    
    print("\n✅ ¡Bot inicializado correctamente!\n")
    
    # Definimos una pregunta basada en los documentos que subiste
    # (Ejemplo basado en 01_credit_card_fraud_indicators.md o 05_pci_dss_compliance.md)
    pregunta = "What are the common indicators of credit card fraud? Please list them."
    print(f"👤 Pregunta: {pregunta}\n")
    
    # Ejecutamos el método query
    # Los parámetros user_id, effective_campana, y task_id son requeridos por tu método 
    # para el logging, así que le pasamos datos de prueba (dummies).
    resultado = bot.query(
        query_text=pregunta,
        user_id=1,
        task_id="task_001"
    )
    
    print("🤖 Respuesta de FinSight:")
    print("-" * 50)
    print(resultado['response'])
    print("-" * 50)
    
    print("\n📚 Fuentes utilizadas (Reranker Top N):")
    for nodo in resultado['source_nodes']:
        print(f"- Archivo: {nodo['filename']} (Relevancia: {nodo['score']:.4f})")

if __name__ == "__main__":
    # Ejecutar desde la terminal usando: python test_bot.py
    probar_chatbot()