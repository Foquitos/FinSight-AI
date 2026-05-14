import os
import logging
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

# 1. Definir la ruta absoluta a la carpeta actual (app/services/database/)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. Definir el nombre del archivo de la base de datos
DB_PATH = os.path.join(BASE_DIR, "database.db")

# 3. Crear la URL de conexión de SQLite
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# 4. Crear el Engine
# 'check_same_thread': False es CRÍTICO para SQLite en entornos web (como FastAPI/Flask con Gunicorn)
# ya que permite que múltiples hilos interactúen con la base de datos.
sqlite_engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)

def init_sqlite_db():
    """Crea la tabla de logs si no existe en el archivo SQLite."""
    try:
        with sqlite_engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS query_chatbots_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    query TEXT,
                    response TEXT,
                    context TEXT,
                    task_id TEXT,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    embedding_tokens INTEGER,
                    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
                    active INTEGER DEFAULT 1
                )
            """))
        logger.info(f"Base de datos SQLite lista en: {DB_PATH}")
    except Exception as e:
        logger.error(f"Error inicializando la base de datos SQLite: {e}")

# Ejecutamos la inicialización automáticamente cuando este módulo es importado
init_sqlite_db()