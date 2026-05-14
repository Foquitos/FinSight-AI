import os
import re
import logging
import asyncio
import datetime
import tiktoken
import chromadb
import sqlalchemy
import json
import pandas as pd

from sqlalchemy import text
from datetime import datetime, timedelta
from typing import Dict, List, Optional, TypedDict, Tuple

from app.config import settings
from llama_index.llms.gemini import Gemini
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.schema import MetadataMode
from llama_index.core.chat_engine import ContextChatEngine
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core.retrievers import QueryFusionRetriever
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.postprocessor import SentenceTransformerRerank
from chromadb.errors import ChromaError
from llama_index.core.callbacks import CallbackManager, TokenCountingHandler

from app.services.Rag_llm.llm_config import DEFAULT_CHROMA_COLLECTION, DEFAULT_LLM_TEMP_REMOTE, DEFAULT_LOG_DIR, DEFAULT_REMOTE_LLM_MODEL, DEFAULT_REMOTE_EMBED_MODEL, DEFAULT_RERANKER_MODEL, DEFAULT_RERANKER_TOP_N, FINSIGHT_DOCS_FOLDER, FINSIGHT_EMBEDDING_STORAGE

from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext, Settings, ChatPromptTemplate, load_index_from_storage
from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter

# --- Configuration Constants ---

# Logging
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'



# --- Setup Logging ---
# logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger(__name__)



# --- Type Definitions ---
class QueryResponse(TypedDict):
    """Structured response for the query method."""
    response: str
    context: str
    source_nodes: List[Dict] # Store simplified source node info
    input_tokens: Optional[int]
    output_tokens: Optional[int]

class DocumentInfo(TypedDict):
    """Information about a document in the index."""
    filename: str
    doc_id: str


class ChatBot:
    """
    A base class for creating Retrieval-Augmented Generation (RAG) chatbots
    using LlamaIndex, ChromaDB, and configurable LLMs/embedding models.
    """

    DEFAULT_SYSTEM_PROMPT = (
        "You are an expert assistant that answers questions based solely on the provided documentation. "
        "Your goal is to provide accurate, concise, and helpful answers, based exclusively on the information available in the context. "
        "Do not use your prior knowledge or mention the sources of information in your answers. "
        "If the provided information is insufficient to answer completely, indicate only what you can extract from the context without speculating. "
        "Present your answers in a natural and conversational manner, as if the information were part of your own knowledge."
    )
    DEFAULT_QA_PROMPT_STR = (
        "Relevant information from the documentation:\n"
        "---------------------\n"
        "{context_str}\n"
        "---------------------\n"
        "Answer the following question based primarily on the information provided above.\n"
        "Be precise and concise. If the information is not sufficient to answer completely, mention only what you can extract from the documentation.\n"
        "Do not indicate to the user that you are using external documentation.\n\n"
        "Question: {query_str}\n"
        "Answer:"
    )
    DEFAULT_REFINE_PROMPT_STR = (
        "You have provided an initial answer. Now you have access to additional information that might be relevant:\n"
        "------------\n"
        "{context_msg}\n"
        "------------\n"
        "Evaluate if this new information improves your previous answer to the question: {query_str}\n"
        "- If the new information is relevant, incorporate these details into your original answer to make it more accurate or complete.\n"
        "- If the new information adds no value or contradicts the original answer, keep the original answer.\n"
        "- Do not mention the refinement process or the sources of information in your answer.\n\n"
        "Previous answer: {existing_answer}\n"
        "Refined answer:"
    )

    def __init__(
        self,
        embedding_storage_path: str,
        docs_folder_path: str,
        collection_name: str = DEFAULT_CHROMA_COLLECTION,
        remote_llm_model: str = DEFAULT_REMOTE_LLM_MODEL,
        remote_embed_model: str = DEFAULT_REMOTE_EMBED_MODEL,
        reranker_model: str = DEFAULT_RERANKER_MODEL,
        reranker_top_n: int = DEFAULT_RERANKER_TOP_N,
        system_prompt: Optional[str] = None,
        qa_prompt_str: Optional[str] = None,
        refine_prompt_str: Optional[str] = None,
        log_dir: str = DEFAULT_LOG_DIR,
        sql_engine: Optional[sqlalchemy.engine.base.Engine] = None,
        read_only: bool = False,
    ):
        """
        Initializes the ChatBot.

        Args:
            embedding_storage_path: Path to store/load ChromaDB vector store.
            docs_folder_path: Path to the folder containing documents for indexing.
            collection_name: Name of the collection within ChromaDB.
            remote_llm_model: Model name for remote Anthropic LLM.
            remote_embed_model: Model name for remote HuggingFace embedding model.
            reranker_model: Model name for the SentenceTransformer Reranker.
            reranker_top_n: Number of results to return after reranking.
            system_prompt: Custom system prompt. If None, uses default.
            qa_prompt_str: Custom QA prompt template string. If None, uses default.
            refine_prompt_str: Custom refine prompt template string. If None, uses default.
            log_dir: Directory to save query/response/context logs.
        """
        logger.info(f"Initializing ChatBot for collection '{collection_name}'...")
        self.embedding_storage_path = embedding_storage_path
        self.docs_folder_path = docs_folder_path
        self.collection_name = collection_name
        self.log_dir = log_dir
        self.sql_engine = sql_engine
        self.read_only = read_only

        # Validate paths
        if not os.path.isdir(self.embedding_storage_path):
             logger.warning(f"Embedding storage path '{self.embedding_storage_path}' does not exist. ChromaDB will attempt to create it.")
        if not os.path.isdir(self.docs_folder_path):
            logger.error(f"Documents folder path '{self.docs_folder_path}' does not exist or is not a directory.")
            raise FileNotFoundError(f"Documents folder not found: {self.docs_folder_path}")

        self._setup_logging(log_dir)
        self._configure_llama_index_settings(
            remote_llm_model, remote_embed_model,
            reranker_model, reranker_top_n
        )
        self._initialize_vector_store()
        self._initialize_index() # Load or build index
        self._setup_prompts(system_prompt, qa_prompt_str, refine_prompt_str)
        self._setup_query_engine()
        self._initialize_cache()
        # Clave: user_id (int), Valor: ChatMemoryBuffer
        logger.info("ChatBot initialization complete.")

    def _initialize_cache(self):
        """Inicializa una colección separada para el caché de preguntas frecuentes."""
        try:
            db = chromadb.PersistentClient(path=self.embedding_storage_path)
            # Creamos/Obtenemos una colección específica para el caché
            self.cache_collection = db.get_or_create_collection(f"{self.collection_name}_cache")
            logger.info("Cache collection initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize cache: {e}")
            self.cache_collection = None

    def _check_cache(self, query_text: str, threshold: float = 0.2) -> Tuple[Optional[str], Optional[List[Dict]]]:
        """
        Busca en el caché. Si encuentra algo, retorna la respuesta y sus fuentes originales.
        """
        if not self.cache_collection:
            return None, None

        try:
            query_embedding = Settings.embed_model.get_query_embedding(query_text)
            
            results = self.cache_collection.query(
                query_embeddings=[query_embedding],
                n_results=1,
                include=["documents", "distances", "metadatas"]
            )

            if results['ids'] and results['distances'][0]: # type: ignore
                distance = results['distances'][0][0] # type: ignore
                
                if distance < threshold:
                    cached_id = results['ids'][0][0]
                    cached_doc = results['documents'][0][0] # type: ignore
                    metadata = results['metadatas'][0][0] if results['metadatas'] else {}
                    
                    # --- LÓGICA DE CADUCIDAD (3 DÍAS) ---
                    timestamp_str = metadata.get("timestamp")
                    
                    if timestamp_str:
                        try:
                            stored_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f') # type: ignore
                            if datetime.now() - stored_time > timedelta(days=3):
                                logger.info(f"Cache entry expired (Age > 3 days). Deleting ID: {cached_id}")
                                self.cache_collection.delete(ids=[cached_id])
                                return None, None 
                                
                        except ValueError:
                            logger.warning("Error parsing cache timestamp. Treating as expired.")
                            return None, None

                    # Extraer fuentes desde los metadatos
                    source_nodes_str = metadata.get("source_nodes", "[]")
                    try:
                        source_nodes = json.loads(source_nodes_str) # type: ignore
                    except (json.JSONDecodeError, TypeError):
                        source_nodes = []

                    logger.info(f"Cache HIT (Dist: {distance:.4f}): {query_text[:30]}...")
                    return cached_doc, source_nodes
            
            logger.info("Cache MISS")
            return None, None

        except Exception as e:
            logger.error(f"Error checking cache: {e}")
            return None, None
    
    def _save_to_cache(self, query_text: str, response_text: str, source_nodes_data: List[Dict]):
        if not self.cache_collection:
            return

        try:
            query_embedding = Settings.embed_model.get_query_embedding(query_text)
            import uuid
            cache_id = str(uuid.uuid4())

            # Guardamos con timestamp y el JSON de los source_nodes
            self.cache_collection.add(
                ids=[cache_id],
                embeddings=[query_embedding],
                documents=[response_text],
                metadatas=[{
                    "original_query": query_text, 
                    "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'),
                    "source_nodes": json.dumps(source_nodes_data) # Serialización a JSON
                }]
            )
            logger.info(f"Saved to cache: {query_text[:50]}...")
        except Exception as e:
            logger.error(f"Error saving to cache: {e}")

    def clear_full_cache(self):
        """Elimina y recrea la colección de caché para purgar datos antiguos."""
        logger.info("Clearing semantic cache...")
        try:
            # Instanciamos el cliente para gestionar las colecciones
            db = chromadb.PersistentClient(path=self.embedding_storage_path)
            cache_name = f"{self.collection_name}_cache"
            
            try:
                # Borramos la colección entera
                db.delete_collection(cache_name)
                logger.info(f"Collection '{cache_name}' deleted.")
            except Exception as e:
                logger.warning(f"Could not delete collection '{cache_name}' (maybe it didn't exist): {e}")
            
            # La recreamos vacía inmediatamente
            self.cache_collection = db.get_or_create_collection(cache_name)
            logger.info("Cache collection recreated and empty.")
            
        except Exception as e:
            logger.error(f"Critical error clearing cache: {e}")

    async def _get_memory_for_user_async(self, user_id: int):
        loop = asyncio.get_running_loop()
        # Ejecuta la función sincrónica en un thread pool para no congelar la API
        return await loop.run_in_executor(None, self._get_memory_for_user, user_id)

    def _get_memory_for_user(self, user_id: int) -> ChatMemoryBuffer:
        """
        Reconstruye el historial del usuario desde la base de datos SQL.
        Esto permite que funcione con múltiples workers de Gunicorn.
        """
        # Límite de mensajes a recuperar para no saturar el contexto (ej. últimos 5 pares = 10 mensajes)
        history_limit = 5 
        
        # Inicializar buffer vacío
        memory = ChatMemoryBuffer.from_defaults(token_limit=3000)
        
        if not self.sql_engine:
            logger.warning("SQL Engine no disponible. Usando memoria volátil vacía.")
            return memory

        try:
            query = text("""
                SELECT query, response 
                FROM query_chatbots_logs
                WHERE user_id = :uid and active = 1
                ORDER BY fecha DESC
                LIMIT :limit
            """)
            
            with self.sql_engine.connect() as conn:
                result = conn.execute(query, {"limit": history_limit, "uid": user_id}).fetchall()

            # Los resultados vienen del más reciente al más antiguo, así que los invertimos
            for row in reversed(result):
                user_msg = row.query
                bot_msg = row.response
                
                if user_msg:
                    memory.put(ChatMessage(role=MessageRole.USER, content=str(user_msg)))
                if bot_msg:
                    memory.put(ChatMessage(role=MessageRole.ASSISTANT, content=str(bot_msg)))
            
            logger.info(f"Historial reconstruido para usuario {user_id} con {len(result)} interacciones previas.")

        except Exception as e:
            logger.error(f"Error recuperando historial de SQL: {e}")
            # Devolvemos memoria vacía en caso de error para no romper el flujo
        
        return memory

    def _setup_logging(self, log_dir: str):
        """Sets up the directory for query-specific logs."""
        self.query_log_dir = os.path.join(log_dir, "queries")
        try:
            os.makedirs(self.query_log_dir, exist_ok=True)
            logger.info(f"Query logs will be saved in: {self.query_log_dir}")
        except OSError as e:
            logger.error(f"Failed to create query log directory '{self.query_log_dir}': {e}")
            # Decide if this is fatal or not. For now, we'll log and continue.
            self.query_log_dir = None # Disable query logging if dir creation fails

    def _configure_llama_index_settings(
        self, remote_llm_model: str,
        remote_embed_model: str,
        reranker_model: str, reranker_top_n: int
    ):
        """Configures LlamaIndex global settings for LLM and embedding model."""
        logger.info(f"Configuring LlamaIndex settings)...")
        try:

            # 1. Inicializa el manejador de conteo de tokens.
            #    Usamos un tokenizer estándar como 'cl100k_base'.
            self.token_counter = TokenCountingHandler(
                tokenizer=tiktoken.get_encoding("cl100k_base").encode
            )

            # 2. Crea un CallbackManager y adjunta el contador de tokens.
            #    Esto interceptará todas las llamadas a LLMs y embeddings.
            Settings.callback_manager = CallbackManager([self.token_counter])
            
            logger.info("TokenCountingHandler initialized and attached to global settings.")
    
            Settings.embed_batch_size = 50  # type: ignore
            logger.info(f"Setting global embed_batch_size to: {Settings.embed_batch_size}") # type: ignore
            
            logger.info(f"Using remote Embedding Model: {remote_embed_model}")
            Settings.embed_model = HuggingFaceEmbedding(
                model_name=remote_embed_model # Modelo súper rápido y top para RAG
            )

            logger.info(f"Using remote LLM (Gemini): {remote_llm_model}")
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]

            Settings.llm = Gemini(
                model=remote_llm_model,
                temperature=DEFAULT_LLM_TEMP_REMOTE,
                api_key=settings.GEMINI_CHATBOT_API_KEY,
                safety_settings=safety_settings, # <--- Agregamos esto # type: ignore
            )

            self.reranker = SentenceTransformerRerank(
                model=reranker_model, top_n=reranker_top_n
            )
            logger.info(f"Using Reranker: {reranker_model} with top_n={reranker_top_n}")

            # Store models for potential later use/reference
            self.llm = Settings.llm
            self.embedding = Settings.embed_model

        except Exception as e:
            logger.exception(f"Fatal error configuring LlamaIndex settings: {e}")
            raise RuntimeError(f"Failed to configure LlamaIndex settings: {e}") from e

    def _initialize_vector_store(self):
        """Initializes the ChromaDB vector store and storage context."""
        logger.info(f"Initializing ChromaDB vector store at: {self.embedding_storage_path}")
        try:
            db = chromadb.PersistentClient(path=self.embedding_storage_path)
            logger.info(f"Getting or creating ChromaDB collection: {self.collection_name}")
            chroma_collection = db.get_or_create_collection(self.collection_name)
            self.vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
            self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
            logger.info("Vector store initialized successfully.")
        except ChromaError as e:
            logger.exception(f"ChromaDB error during initialization: {e}")
            raise RuntimeError(f"Failed to initialize ChromaDB: {e}") from e
        except Exception as e:
            logger.exception(f"Unexpected error initializing vector store: {e}")
            raise RuntimeError(f"Failed to initialize vector store: {e}") from e

    def _initialize_index(self):
        """Carga el índice existente o construye uno nuevo si está corrupto/vacío."""
        persist_dir = self.embedding_storage_path 
        docstore_path = os.path.join(persist_dir, "docstore.json")
        index_store_path = os.path.join(persist_dir, "index_store.json")

        index_loaded = False

        if os.path.exists(docstore_path) and os.path.exists(index_store_path):
            logger.info(f"Found existing docstore and index store in: {persist_dir}")
            try:
                logger.info("Attempting to load index by reconstructing StorageContext...")
                
                db = chromadb.PersistentClient(path=persist_dir)
                chroma_collection = db.get_collection(self.collection_name)
                vector_store_instance = ChromaVectorStore(chroma_collection=chroma_collection)
                
                # Reconstruir contexto desde disco
                reconstructed_storage_context = StorageContext.from_defaults(
                    vector_store=vector_store_instance,
                    persist_dir=persist_dir 
                )
                
                self.index = load_index_from_storage(
                    storage_context=reconstructed_storage_context,
                    show_progress=True,
                )
                self.storage_context = reconstructed_storage_context
                
                # --- VALIDACIÓN DE DOCSTORE ---
                # Si cargó pero el docstore está vacío, BM25 fallará. Forzamos reconstrucción.
                if not self.index.docstore or len(self.index.docstore.docs) == 0:
                    logger.warning("⚠️ Index loaded but Docstore is EMPTY! Index is inconsistent. Rebuilding...")
                    index_loaded = False # Esto activará el _build_index abajo
                else:
                    logger.info(f"Successfully loaded index with {len(self.index.docstore.docs)} documents.")
                    index_loaded = True

            except Exception as e:
                logger.warning(f"Failed to load index ({type(e).__name__}: {e}). Building new index...")
                index_loaded = False
        
        if not index_loaded:
            if self.read_only:
                # Si somos un worker de Gunicorn y falló la carga, NO construimos. Fallamos o iniciamos vacío.
                logger.warning("⚠️ MODO READ_ONLY: No se encontró índice válido y no se permite construir. Iniciando índice vacío en memoria.")
                self.index = VectorStoreIndex.from_documents([], storage_context=self.storage_context)
            else:
                # Si somos el script de inicialización, construimos.
                logger.info("Índice no encontrado o corrupto. Iniciando construcción (BUILD MODE)...")
                self._build_index()

    def _build_index(self):
        """Construye el índice usando Markdown + Semantic parsing y asegura persistencia."""
        logger.info(f"Building new index from documents in: {self.docs_folder_path}")

        try:
            # 1. Cargar documentos (Forzamos extensión .md si ese es tu formato)
            documents = SimpleDirectoryReader(
                self.docs_folder_path,
                filename_as_id=True,
                required_exts=[".md"] 
            ).load_data(show_progress=True)

            if not documents:
                logger.warning(f"No documents found in '{self.docs_folder_path}'. Index will be empty.")
                self.index = VectorStoreIndex.from_documents([], storage_context=self.storage_context)
                self.index.storage_context.persist(persist_dir=self.embedding_storage_path)
                return 

            logger.info(f"Found {len(documents)} documents. Starting Hybrid Parsing.")

            # 2. Pipelines de Parseo
            markdown_parser = MarkdownNodeParser(include_metadata=True)
            text_splitter = SentenceSplitter(chunk_size=512, chunk_overlap=50)

            pipeline = IngestionPipeline(
                transformations=[markdown_parser, text_splitter]
            )

            # 3. Generar Nodos
            nodes = pipeline.run(documents=documents, show_progress=True)
            
            # Filtrar nodos vacíos que rompen BM25
            nodes = [n for n in nodes if n.get_content() and n.get_content().strip()]
            
            logger.info(f"Generated {len(nodes)} valid nodes for indexing.")

            # 4. Añadir explícitamente al DocStore antes de indexar (Doble seguridad)
            self.storage_context.docstore.add_documents(nodes)

            # 5. Construir Índice Vectorial
            self.index = VectorStoreIndex(
                nodes, 
                storage_context=self.storage_context, 
                show_progress=True
            )

            # 6. Persistir TODO (Vectores + DocStore)
            self.index.storage_context.persist(persist_dir=self.embedding_storage_path)
            logger.info(f"New index built and persisted to {self.embedding_storage_path}")

        except Exception as e:
            logger.exception(f"Failed to build index: {e}")
            # Crear índice vacío de emergencia para no tumbar la API
            self.index = VectorStoreIndex.from_documents([], storage_context=self.storage_context)

    def _setup_prompts(
        self,
        system_prompt: Optional[str] = None,
        qa_prompt_str: Optional[str] = None,
        refine_prompt_str: Optional[str] = None,
    ):
        """Sets up the chat prompt templates using provided or default strings."""
        logger.info("Setting up chat prompt templates...")

        _system = system_prompt or self.DEFAULT_SYSTEM_PROMPT
        self.system_prompt = _system
        logger.debug(f"System Prompt configured: {_system}")
        
        _qa_str = qa_prompt_str or self.DEFAULT_QA_PROMPT_STR
        _refine_str = refine_prompt_str or self.DEFAULT_REFINE_PROMPT_STR

        # Text QA Prompt
        chat_text_qa_msgs = [("system", _system), ("user", _qa_str)]
        self.text_qa_template = ChatPromptTemplate.from_messages(chat_text_qa_msgs)
        logger.debug(f"QA Template configured: {chat_text_qa_msgs}")

        # Refine Prompt
        chat_refine_msgs = [("system", _system), ("user", _refine_str)]
        self.refine_template = ChatPromptTemplate.from_messages(chat_refine_msgs)
        logger.debug(f"Refine Template configured: {chat_refine_msgs}")

    def _setup_query_engine(self):
        """Creates the query engine from the initialized index."""
        if not hasattr(self, 'index') or self.index is None:
             logger.error("Cannot setup query engine: Index is not initialized.")
             raise RuntimeError("Index must be initialized before setting up the query engine.")
        if not hasattr(self, 'text_qa_template') or not hasattr(self, 'refine_template'):
             logger.error("Cannot setup query engine: Prompt templates are not set up.")
             raise RuntimeError("Prompts must be set up before the query engine.")
        if not hasattr(self, 'reranker'):
             logger.error("Cannot setup query engine: Reranker is not configured.")
             # Handle this - maybe proceed without reranker? For now, raise error.
             raise RuntimeError("Reranker must be configured before the query engine.")


        logger.info("Setting up query engine...")
        try:
            self.query_engine = self.index.as_query_engine(
                text_qa_template=self.text_qa_template,
                refine_template=self.refine_template,
                response_mode='refine', 
                similarity_top_k=10, 
                node_postprocessors=[self.reranker],
                streaming=False,
            )
            logger.info("Query engine setup complete.")
        except Exception as e:
            logger.exception(f"Failed to set up query engine: {e}")
            raise RuntimeError(f"Query engine setup failed: {e}") from e
    def _log_query_details(self, query: str, response: str, context: str, user_id: int, task_id: str, input_tokens: Optional[int] = None, output_tokens: Optional[int] = None, embedding_tokens: Optional[int] = None):
        """Logs query, response, and context to separate files."""
        
        diccionario = {
            "user_id":user_id,
            "query":query,
            "response":response,
            "context":context,
            'task_id':task_id,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'embedding_tokens': embedding_tokens,
        }
        
        df = pd.DataFrame([diccionario])
        if self.sql_engine:
            df.to_sql('query_chatbots_logs', self.sql_engine, if_exists='append', index=False)
        
        if not self.query_log_dir:
            logger.warning("Query logging disabled because log directory setup failed.")
            return

        try:
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f')
            base_filename = os.path.join(self.query_log_dir, f'{timestamp}')

            # Save query
            with open(f'{base_filename}_query.txt', mode='w', encoding='utf-8') as f:
                f.write(query)
            # Save response
            with open(f'{base_filename}_response.txt', mode='w', encoding='utf-8') as f:
                f.write(response)
            # Save context
            with open(f'{base_filename}_context.txt', mode='w', encoding='utf-8') as f:
                f.write(context)
        except Exception as e:
            logger.error(f"Failed to log query details for timestamp {timestamp}: {e}")

    def _build_hybrid_retriever(self, use_async: bool):
        """Construye el retriever híbrido (BM25 + Vectorial)."""
        def spanish_tokenizer(text: str) -> List[str]:
            return re.findall(r'\b\w+(?:-\w+)*\b', text.lower())

        try:
            if not self.index.docstore or len(self.index.docstore.docs) == 0:
                raise ValueError("Docstore vacío")

            vector_retriever = self.index.as_retriever(similarity_top_k=6)
            bm25_retriever = BM25Retriever.from_defaults(
                docstore=self.index.docstore, 
                similarity_top_k=6,
                tokenizer=spanish_tokenizer 
            )
            
            return QueryFusionRetriever(
                [vector_retriever, bm25_retriever],
                similarity_top_k=6,
                num_queries=1,
                mode="reciprocal_rerank", # pyright: ignore[reportArgumentType]
                use_async=use_async
            )
        except Exception as e:
            logger.warning(f"⚠️ Falló inicialización BM25 ({e}). Usando SOLO Vectorial.")
            return self.index.as_retriever(similarity_top_k=6)

    def _build_chat_engine(self, retriever, user_memory) -> ContextChatEngine:
        """Construye el motor de chat con su contexto y memoria."""
        return ContextChatEngine.from_defaults(
            retriever=retriever,
            memory=user_memory,
            system_prompt=self.system_prompt,
            node_postprocessors=[self.reranker],
            llm=self.llm
        )

    def _format_source_context(self, source_nodes, query_text: str):
        """Extrae y formatea la información de los nodos fuente."""
        source_nodes_data = []
        context_str = f"Q Original: {query_text}\n\n\nFuentes:\n"
        
        if source_nodes:
            for node in source_nodes:
                fname = node.metadata.get('file_name', 'N/A')
                score = node.score or 0.0
                node_text = node.get_content(metadata_mode=MetadataMode.NONE)
                
                context_str += f"--- Archivo: {fname} (Score: {score:.4f}) ---\n"
                context_str += f"Contenido:\n{node_text}\n\n"
                
                source_nodes_data.append({
                    "filename": os.path.basename(fname),
                    "doc_id": node.node_id,
                    "score": score,
                    "text_preview": node_text[:200] + "..."
                })
        else:
            context_str += "No source nodes found."
            
        return context_str, source_nodes_data

    def query(self, query_text: str, user_id: int, task_id: str) -> QueryResponse:
        """Flujo Síncrono: Recuperación Híbrida -> Respuesta con Memoria."""
        if not hasattr(self, 'index') or self.index is None:
             return QueryResponse(response="Error: El índice no está inicializado.", context="", source_nodes=[], input_tokens=0, output_tokens=0)

        logger.info(f"Task {task_id}: Starting sync processing for user {user_id}")

        # 1. Caché
        cached_response, cached_sources = self._check_cache(query_text)
        if cached_response:
            # Reconstruimos un mini context_str para los logs
            context_str = "Respuesta desde Caché\nFuentes recuperadas: " + ", ".join([s.get('filename', 'N/A') for s in (cached_sources or [])])
            self._log_query_details(query_text, cached_response, context_str, user_id, task_id, 0, 0, 0)
            return QueryResponse(response=cached_response, context=context_str, source_nodes=cached_sources or [], input_tokens=0, output_tokens=0)

        try:
            # 2. Preparar Componentes (Sync)
            retriever = self._build_hybrid_retriever(use_async=False)
            user_memory = self._get_memory_for_user(user_id)
            chat_engine = self._build_chat_engine(retriever, user_memory)

            # 3. Ejecutar
            self.token_counter.reset_counts()
            response_obj = chat_engine.chat(query_text)
            response_text = str(response_obj)

            # 4. Formatear
            context_str, source_nodes_data = self._format_source_context(response_obj.source_nodes, query_text)
            
            # Guardamos en caché AHORA, porque ya tenemos las fuentes
            if len(response_text) > 20 and "Error" not in response_text:
                self._save_to_cache(query_text, response_text, source_nodes_data)

            # Loguear
            input_tokens = self.token_counter.prompt_llm_token_count or 0
            output_tokens = self.token_counter.completion_llm_token_count or 0
            embedding_tokens = self.token_counter.total_embedding_token_count

            self._log_query_details(query_text, response_text, context_str, user_id, task_id, input_tokens, output_tokens, embedding_tokens)

            return QueryResponse(
                response=response_text, context=context_str, source_nodes=source_nodes_data, 
                input_tokens=input_tokens, output_tokens=output_tokens
            )

        except Exception as e:
            logger.exception(f"Error during query execution: {e}")
            return QueryResponse(response=f"Error during query: {e}", context="", source_nodes=[], input_tokens=0, output_tokens=0)


    async def stream_query(self, query_text: str, user_id: int, task_id: str):
        """Flujo Asíncrono (Streaming): Recuperación Híbrida -> Respuesta con Memoria."""
        if not hasattr(self, 'index') or self.index is None:
            yield "Error: El índice no está inicializado."
            return

        logger.info(f"Task {task_id}: Starting async processing for user {user_id}")

        # 1. Caché
        cached_response, cached_sources = self._check_cache(query_text)
        if cached_response:
            yield cached_response
            context_str = "Respuesta desde Caché\nFuentes recuperadas: " + ", ".join([s.get('filename', 'N/A') for s in (cached_sources or [])])
            self._log_query_details(query_text, cached_response, context_str, user_id, task_id, 0, 0, 0)
            return

        try:
            # 2. Preparar Componentes (Async)
            retriever = self._build_hybrid_retriever(use_async=True)
            user_memory = await self._get_memory_for_user_async(user_id)
            chat_engine = self._build_chat_engine(retriever, user_memory)

            # 3. Ejecutar Streaming
            self.token_counter.reset_counts()
            streaming_response = await chat_engine.astream_chat(query_text)

            full_response = ""
            async for token in streaming_response.async_response_gen():
                full_response += token
                yield token
            
            # 4. Formatear y Loguear (Observa que aquí quitamos el "_")
            context_str, source_nodes_data = self._format_source_context(streaming_response.source_nodes, query_text)

            # Guardamos en el caché después de procesar y tener los nodos
            if len(full_response) > 20 and "Error" not in full_response:
                self._save_to_cache(query_text, full_response, source_nodes_data)
            
            input_tokens = self.token_counter.prompt_llm_token_count or 0
            output_tokens = self.token_counter.completion_llm_token_count or 0
            embedding_tokens = self.token_counter.total_embedding_token_count

            self._log_query_details(query_text, full_response, context_str, user_id, task_id, input_tokens, output_tokens, embedding_tokens)

        except Exception as e:
            logger.exception(f"Critical error in stream_query: {e}")
            yield f"\n[Error del Sistema]: {str(e)}"

    # --- Document Management Methods ---

    def _persist_index(self, operation_name: str):
        """Helper method to persist index changes and log."""
        try:
            logger.info(f"Persisting index changes after {operation_name}...")
            self.index.storage_context.persist(persist_dir=self.embedding_storage_path)
            logger.info("Index persisted successfully.")
        except Exception as e:
            logger.exception(f"Failed to persist index after {operation_name}: {e}")
            # Depending on severity, might want to raise an error here

    def refresh_documents(self) -> List[bool]:
        """
        Refreshes the index based on documents currently in the docs folder.
        Adds new documents, updates changed ones, and removes deleted ones.

        Returns:
            A list indicating refresh status for documents (True=refreshed, False=error).
            Note: LlamaIndex refresh_ref_docs returns List[bool] directly.
        """
        logger.info("Starting document refresh process...")
        try:
            # SimpleDirectoryReader re-reads the directory
            documents = SimpleDirectoryReader(
                self.docs_folder_path,
                filename_as_id=True
            ).load_data(show_progress=True)

            logger.info(f"Found {len(documents)} documents in folder for refresh.")
            # refresh_ref_docs handles additions, deletions, and updates based on doc_id (filename)
            refresh_results = self.index.refresh_ref_docs(documents, show_progress=True)
            logger.info(f"Refresh results: {refresh_results}")

            self._persist_index("refresh_documents")
            
            self.clear_full_cache()

            return refresh_results # List[bool] indicating success/failure per doc
        except Exception as e:
            logger.exception(f"Error during document refresh: {e}")
            return [] # Return empty list on error
        
    def get_history(self, user_id: int) -> List[Dict[str, str]]:
        """
        Recupera el historial de chat desde la Base de Datos para el frontend.
        Esencial para que persista entre recargas y workers de Gunicorn.
        """
        if not self.sql_engine:
            return []
        
        history = []
        limit = 20 # Traer los últimos 20 mensajes (ajustable)

        try:
            # Consultamos query (usuario) y response (bot)
            # Ordenamos por ID descendente para obtener los más recientes primero
            query = text("""
                SELECT query, response 
                FROM query_chatbots_logs
                WHERE user_id = :uid and active = 1
                ORDER BY fecha DESC
                LIMIT :limit
            """)
            
            with self.sql_engine.connect() as conn:
                result = conn.execute(query, {"limit": limit, "uid": user_id}).fetchall()

            # Invertimos para que el orden sea cronológico (antiguo -> nuevo)
            for row in reversed(result):
                if row.query:
                    history.append({"role": "user", "content": str(row.query)})
                if row.response:
                    history.append({"role": "bot", "content": str(row.response)})
            
        except Exception as e:
            logger.error(f"Error leyendo historial desde SQL: {e}")
            return []

        return history

    def clear_history(self, user_id: int):
        """Borra el historial del usuario en la base de datos (Soft Delete o Hard Delete)."""
        if not self.sql_engine:
            return

        try:
            # Opción B: Soft Delete (Si agregas una columna 'active' o 'deleted_at')
            query = text("UPDATE dbo.[query_chatbots_logs] SET active = 0 WHERE user_id = :uid")
            
            with self.sql_engine.begin() as conn:
                conn.execute(query, {"uid": user_id})
            
            logger.info(f"Historial SQL borrado para el usuario {user_id}")

        except Exception as e:
            logger.error(f"Error borrando historial en SQL: {e}")

# --- Specialized ChatBot for Edesur Context ---

class finsight(ChatBot):
    # Specific paths and configuration for finsight
    EMBEDDING_STORAGE = FINSIGHT_EMBEDDING_STORAGE
    DOCS_FOLDER = FINSIGHT_DOCS_FOLDER

    # Specific prompts for Edesur context
    SYSTEM_PROMPT = """You are FinSight, an advanced Financial AI Assistant designed specifically to support Fraud and Risk Analysts. Your knowledge base consists strictly of official documents regarding fraud detection patterns, Anti-Money Laundering (AML) procedures, KYC (Know Your Customer) requirements, and PCI DSS compliance.

**Your Primary Objectives:**
1. **Regulatory and Theoretical Support:** Provide accurate explanations about financial policies, fraud indicators, and banking security procedures based on the provided literature.
2. **Absolute Rigor:** In the financial sector, precision is critical. Base your answers SOLELY on the provided context documents. Do not invent regulations, laws, or assume procedures that are not in your context.
3. **Traceability:** You act as an audit tool. The information you provide must be easily auditable by a human analyst.

**Response Rules:**
* If the requested information is not found in the provided context, clearly state: "I cannot find information regarding this topic in the document knowledge base." Do not attempt to guess, hallucinate, or use external knowledge.
* Maintain a professional, objective, analytical, and direct tone. Avoid colloquial language.
* Use **bold text** to highlight technical terms, regulations, or critical risk indicators.
* If asked about a step-by-step procedure (e.g., KYC procedures), structure your response using numbered lists to facilitate quick reading by the analyst.

---
*Disclaimer: This is an analytical prototype. Final decisions regarding transaction or account blocks must be validated by the Fraud Analysis team.*
"""


    def __init__(self,
        sql_engine: Optional[sqlalchemy.engine.base.Engine] = None,
        read_only: bool = False
        ):

        # Call the parent constructor with finsight specific configurations
        super().__init__(
            embedding_storage_path=self.EMBEDDING_STORAGE,
            docs_folder_path=self.DOCS_FOLDER,
            reranker_top_n=3,
            system_prompt=self.SYSTEM_PROMPT,
            sql_engine=sql_engine,
            read_only=read_only
        )
        logger.info("finsight instance initialized with specific configuration.")
