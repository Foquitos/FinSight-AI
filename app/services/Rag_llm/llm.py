import os
import re
import json
import logging
import asyncio
import datetime
import tiktoken
import chromadb
import sqlalchemy
import pandas as pd

from sqlalchemy import text
from datetime import datetime, timedelta
from typing import Dict, List, Optional, TypedDict, Tuple

from app.config import settings
from llama_index.llms.gemini import Gemini
from google.genai.types import EmbedContentConfig
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.schema import Document, MetadataMode
from llama_index.core.chat_engine import ContextChatEngine
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core.retrievers import QueryFusionRetriever
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.postprocessor import SentenceTransformerRerank
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
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

        self.query_log_dir = os.path.join(log_dir, "queries")
        self._configure_llama_index_settings(
            remote_llm_model, remote_embed_model,
            reranker_model, reranker_top_n
        )
        self._initialize_vector_store()
        self._initialize_index() # Load or build index
        self._setup_prompts(system_prompt, qa_prompt_str, refine_prompt_str)
        self._setup_query_engine()
        self._initialize_cache()
        # Key: user_id (int), Value: ChatMemoryBuffer
        logger.info("ChatBot initialization complete.")

    def _initialize_cache(self):
        """Initializes a separate collection for the FAQ cache."""
        try:
            db = chromadb.PersistentClient(path=self.embedding_storage_path)
            # Create/Get a specific collection for the cache
            self.cache_collection = db.get_or_create_collection(f"{self.collection_name}_cache")
            logger.info("Cache collection initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize cache: {e}")
            self.cache_collection = None

    def _check_cache(self, query_text: str, threshold: float = 0.2) -> Tuple[Optional[str], Optional[List[Dict]]]:
        """
        Searches the cache. If found, returns the response and its original sources.
        """
        if not self.cache_collection:
            return None, None

        try:
            query_embedding = Settings.embed_model.get_query_embedding(query_text)
            
            # Request metadata and IDs in the query
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
                    
                    # --- EXPIRATION LOGIC (3 DAYS) ---
                    timestamp_str = metadata.get("timestamp")
                    
                    if timestamp_str:
                        try:
                            # Convert the saved string to a datetime object
                            stored_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f') # type: ignore
                            
                            # Check the age
                            if datetime.now() - stored_time > timedelta(days=3):
                                logger.info(f"Cache entry expired (Age > 3 days). Deleting ID: {cached_id}")
                                # Delete the old entry
                                self.cache_collection.delete(ids=[cached_id])
                                return None, None # Return None to force new generation
                                
                        except ValueError:
                            logger.warning("Error parsing cache timestamp. Treating as expired.")
                            return None, None

                    # Extract sources from metadata
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

            # Save with timestamp and the JSON of the source_nodes
            self.cache_collection.add(
                ids=[cache_id],
                embeddings=[query_embedding],
                documents=[response_text],
                metadatas=[{
                    "original_query": query_text, 
                    "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'),
                    "source_nodes": json.dumps(source_nodes_data) # JSON serialization
                }]
            )
            logger.info(f"Saved to cache: {query_text[:50]}...")
        except Exception as e:
            logger.error(f"Error saving to cache: {e}")

    def clear_full_cache(self):
        """Deletes and recreates the cache collection to purge old data."""
        logger.info("Clearing semantic cache...")
        try:
            # Instantiate the client to manage collections
            db = chromadb.PersistentClient(path=self.embedding_storage_path)
            cache_name = f"{self.collection_name}_cache"
            
            try:
                # Delete the entire collection
                db.delete_collection(cache_name)
                logger.info(f"Collection '{cache_name}' deleted.")
            except Exception as e:
                logger.warning(f"Could not delete collection '{cache_name}' (maybe it didn't exist): {e}")
            
            # Recreate it empty immediately
            self.cache_collection = db.get_or_create_collection(cache_name)
            logger.info("Cache collection recreated and empty.")
            
        except Exception as e:
            logger.error(f"Critical error clearing cache: {e}")

    async def _get_memory_for_user_async(self, user_id: int):
        loop = asyncio.get_running_loop()
        # Executes the synchronous function in a thread pool to avoid freezing the API
        return await loop.run_in_executor(None, self._get_memory_for_user, user_id)

    def _get_memory_for_user(self, user_id: int) -> ChatMemoryBuffer:
        """
        Reconstructs the user's history from the SQL database.
        This allows it to work with multiple Gunicorn workers.
        """
        # Limit of messages to retrieve to avoid saturating the context (e.g., last 5 pairs = 10 messages)
        history_limit = 5 
        
        # Initialize empty buffer
        memory = ChatMemoryBuffer.from_defaults(token_limit=3000)
        
        if not self.sql_engine:
            logger.warning("SQL Engine not available. Using empty volatile memory.")
            return memory

        try:
            query = text("""
                SELECT query, response 
                FROM query_chatbots_logs
                WHERE user_id = :uid and active = 1
                ORDER BY date DESC
                LIMIT :limit
            """)
            
            with self.sql_engine.connect() as conn:
                result = conn.execute(query, {"limit": history_limit, "uid": user_id}).fetchall()

            # Results come from newest to oldest, so we reverse them
            for row in reversed(result):
                user_msg = row.query
                bot_msg = row.response
                
                if user_msg:
                    memory.put(ChatMessage(role=MessageRole.USER, content=str(user_msg)))
                if bot_msg:
                    memory.put(ChatMessage(role=MessageRole.ASSISTANT, content=str(bot_msg)))
            
            logger.info(f"History reconstructed for user {user_id} with {len(result)} previous interactions.")

        except Exception as e:
            logger.error(f"Error retrieving history from SQL: {e}")
            # Return empty memory in case of error to avoid breaking the flow
        
        return memory

    def _configure_llama_index_settings(
        self, remote_llm_model: str,
        remote_embed_model: str,
        reranker_model: str, reranker_top_n: int
    ):
        """Configures LlamaIndex global settings for LLM and embedding model."""
        logger.info(f"Configuring LlamaIndex settings)...")
        try:

            # 1. Initializes the token counting handler.
            #    We use a standard tokenizer like 'cl100k_base'.
            self.token_counter = TokenCountingHandler(
                tokenizer=tiktoken.get_encoding("cl100k_base").encode
            )

            # 2. Creates a CallbackManager and attaches the token counter.
            #    This will intercept all calls to LLMs and embeddings.
            Settings.callback_manager = CallbackManager([self.token_counter])
            
            logger.info("TokenCountingHandler initialized and attached to global settings.")
    
            Settings.embed_batch_size = 50  # type: ignore
            logger.info(f"Setting global embed_batch_size to: {Settings.embed_batch_size}") # type: ignore
            
            logger.info(f"Using remote Embedding Model: {remote_embed_model}")
            Settings.embed_model = HuggingFaceEmbedding(
                model_name=remote_embed_model # Super fast and top model for RAG
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
                safety_settings=safety_settings, # <--- We add this # type: ignore
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
        """Loads the existing index or builds a new one if it is corrupted/empty."""
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
                
                # Reconstruct context from disk
                reconstructed_storage_context = StorageContext.from_defaults(
                    vector_store=vector_store_instance,
                    persist_dir=persist_dir 
                )
                
                self.index = load_index_from_storage(
                    storage_context=reconstructed_storage_context,
                    show_progress=True,
                )
                self.storage_context = reconstructed_storage_context
                
                # --- DOCSTORE VALIDATION ---
                # If loaded but the docstore is empty, BM25 will fail. Forcing reconstruction.
                if not self.index.docstore or len(self.index.docstore.docs) == 0:
                    logger.warning("⚠️ Index loaded but Docstore is EMPTY! Index is inconsistent. Rebuilding...")
                    index_loaded = False # This will trigger _build_index below
                else:
                    logger.info(f"Successfully loaded index with {len(self.index.docstore.docs)} documents.")
                    index_loaded = True

            except Exception as e:
                logger.warning(f"Failed to load index ({type(e).__name__}: {e}). Building new index...")
                index_loaded = False
        
        if not index_loaded:
            if self.read_only:
                # If we are a Gunicorn worker and loading failed, DO NOT build. Fail or start empty.
                logger.warning("⚠️ READ_ONLY MODE: No valid index found and building is not allowed. Starting empty index in memory.")
                self.index = VectorStoreIndex.from_documents([], storage_context=self.storage_context)
            else:
                # If we are the initialization script, we build.
                logger.info("Index not found or corrupted. Starting build (BUILD MODE)...")
                self._build_index()

    def _build_index(self):
        """Builds the index using Markdown + Semantic parsing and ensures persistence."""
        logger.info(f"Building new index from documents in: {self.docs_folder_path}")

        try:
            # 1. Load documents (Forcing .md extension if that's your format)
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

            # 2. Parsing Pipelines
            markdown_parser = MarkdownNodeParser(include_metadata=True)
            text_splitter = SentenceSplitter(chunk_size=512, chunk_overlap=50)

            pipeline = IngestionPipeline(
                transformations=[markdown_parser, text_splitter]
            )

            # 3. Generate Nodes
            nodes = pipeline.run(documents=documents, show_progress=True)
            
            # Filter empty nodes that break BM25
            nodes = [n for n in nodes if n.get_content() and n.get_content().strip()]
            
            logger.info(f"Generated {len(nodes)} valid nodes for indexing.")

            # 4. Explicitly add to DocStore before indexing (Double security)
            self.storage_context.docstore.add_documents(nodes)

            # 5. Build Vector Index
            self.index = VectorStoreIndex(
                nodes, 
                storage_context=self.storage_context, 
                show_progress=True
            )

            # 6. Persist EVERYTHING (Vectors + DocStore)
            self.index.storage_context.persist(persist_dir=self.embedding_storage_path)
            logger.info(f"New index built and persisted to {self.embedding_storage_path}")

        except Exception as e:
            logger.exception(f"Failed to build index: {e}")
            # Create an emergency empty index to avoid crashing the API
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

    def _log_query_details(self, query: str, response: str, context: str, user_id: int, task_id: str, input_tokens: Optional[int] = None, output_tokens: Optional[int] = None, embedding_tokens: Optional[int] = None, log_to_db: bool = True, log_to_files: bool = False):
        """Logs query, response, and context to separate files."""
        
        dictionary = {
            "user_id":user_id,
            "query":query,
            "response":response,
            "context":context,
            'task_id':task_id,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'embedding_tokens': embedding_tokens,
        }
        
        df = pd.DataFrame([dictionary])
        if self.sql_engine and log_to_db:
            df.to_sql('query_chatbots_logs', self.sql_engine, if_exists='append', index=False)
        
        if log_to_files:
            if not self.query_log_dir or not os.path.exists(self.query_log_dir):
                os.makedirs(self.query_log_dir, exist_ok=True) if self.query_log_dir else None
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
        """Builds the hybrid retriever (BM25 + Vectorial)."""
        def custom_tokenizer(text: str) -> List[str]:
            return re.findall(r'\b\w+(?:-\w+)*\b', text.lower())

        try:
            if not self.index.docstore or len(self.index.docstore.docs) == 0:
                raise ValueError("Empty docstore")

            vector_retriever = self.index.as_retriever(similarity_top_k=6)
            bm25_retriever = BM25Retriever.from_defaults(
                docstore=self.index.docstore, 
                similarity_top_k=6,
                tokenizer=custom_tokenizer 
            )
            
            return QueryFusionRetriever(
                [vector_retriever, bm25_retriever],
                similarity_top_k=6,
                num_queries=1,
                mode="reciprocal_rerank", # pyright: ignore[reportArgumentType]
                use_async=use_async
            )
        except Exception as e:
            logger.warning(f"⚠️ BM25 initialization failed ({e}). Using ONLY Vectorial.")
            return self.index.as_retriever(similarity_top_k=6)

    def _build_chat_engine(self, retriever, user_memory) -> ContextChatEngine:
        """Builds the chat engine with its context and memory."""
        return ContextChatEngine.from_defaults(
            retriever=retriever,
            memory=user_memory,
            system_prompt=self.system_prompt,
            node_postprocessors=[self.reranker],
            llm=self.llm
        )

    def _format_source_context(self, source_nodes, query_text: str):
        """Extracts and formats information from source nodes."""
        source_nodes_data = []
        context_str = f"Original Q: {query_text}\n\n\nSources:\n"
        
        if source_nodes:
            for node in source_nodes:
                fname = node.metadata.get('file_name', 'N/A')
                score = node.score or 0.0
                node_text = node.get_content(metadata_mode=MetadataMode.NONE)
                
                context_str += f"--- File: {fname} (Score: {score:.4f}) ---\n"
                context_str += f"Content:\n{node_text}\n\n"
                
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
        """Synchronous Flow: Hybrid Retrieval -> Response with Memory."""
        if not hasattr(self, 'index') or self.index is None:
             return QueryResponse(response="Error: The index is not initialized.", context="", source_nodes=[], input_tokens=0, output_tokens=0)

        logger.info(f"Task {task_id}: Starting sync processing for user {user_id}")

        # 1. Cache
        cached_response, cached_sources = self._check_cache(query_text)
        if cached_response:
            # Reconstruct a mini context_str for logs
            context_str = "Response from Cache\nRetrieved sources: " + ", ".join([s.get('filename', 'N/A') for s in (cached_sources or [])])
            self._log_query_details(query_text, cached_response, context_str, user_id, task_id, 0, 0, 0)
            return QueryResponse(response=cached_response, context=context_str, source_nodes=cached_sources or [], input_tokens=0, output_tokens=0)

        try:
            # 2. Prepare Components (Sync)
            retriever = self._build_hybrid_retriever(use_async=False)
            user_memory = self._get_memory_for_user(user_id)
            chat_engine = self._build_chat_engine(retriever, user_memory)

            # 3. Execute
            self.token_counter.reset_counts()
            response_obj = chat_engine.chat(query_text)
            response_text = str(response_obj)

            # 4. Format
            context_str, source_nodes_data = self._format_source_context(response_obj.source_nodes, query_text)
            
            # Save to cache NOW, because we already have the sources
            if len(response_text) > 20 and "Error" not in response_text:
                self._save_to_cache(query_text, response_text, source_nodes_data)

            # Log
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
        """Asynchronous Flow (Streaming): Hybrid Retrieval -> Response with Memory."""
        if not hasattr(self, 'index') or self.index is None:
            yield "Error: The index is not initialized."
            return

        logger.info(f"Task {task_id}: Starting async processing for user {user_id}")

        # 1. Cache
        cached_response, cached_sources = self._check_cache(query_text)
        if cached_response:
            yield cached_response
            context_str = "Response from Cache\nRetrieved sources: " + ", ".join([s.get('filename', 'N/A') for s in (cached_sources or [])])
            self._log_query_details(query_text, cached_response, context_str, user_id, task_id, 0, 0, 0)
            return

        try:
            # 2. Prepare Components (Async)
            retriever = self._build_hybrid_retriever(use_async=True)
            user_memory = await self._get_memory_for_user_async(user_id)
            chat_engine = self._build_chat_engine(retriever, user_memory)

            # 3. Execute Streaming
            self.token_counter.reset_counts()
            streaming_response = await chat_engine.astream_chat(query_text)

            full_response = ""
            async for token in streaming_response.async_response_gen():
                full_response += token
                yield token
            
            # 4. Format and Log (Note that we removed the "_")
            context_str, source_nodes_data = self._format_source_context(streaming_response.source_nodes, query_text)

            # Save to cache after processing and having the nodes
            if len(full_response) > 20 and "Error" not in full_response:
                self._save_to_cache(query_text, full_response, source_nodes_data)
            
            input_tokens = self.token_counter.prompt_llm_token_count or 0
            output_tokens = self.token_counter.completion_llm_token_count or 0
            embedding_tokens = self.token_counter.total_embedding_token_count

            self._log_query_details(query_text, full_response, context_str, user_id, task_id, input_tokens, output_tokens, embedding_tokens)

        except Exception as e:
            logger.exception(f"Critical error in stream_query: {e}")
            yield f"\n[System Error]: {str(e)}"

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
        Retrieves the chat history from the Database for the frontend.
        Essential for it to persist between reloads and Gunicorn workers.
        """
        if not self.sql_engine:
            return []
        
        history = []
        limit = 20 # Fetch the last 20 messages (adjustable)

        try:
            # Query query (user) and response (bot)
            # Order by ID descending to get the most recent first
            query = text("""
                SELECT query, response 
                FROM query_chatbots_logs
                WHERE user_id = :uid and active = 1
                ORDER BY date DESC
                LIMIT :limit
            """)
            
            with self.sql_engine.connect() as conn:
                result = conn.execute(query, {"limit": limit, "uid": user_id}).fetchall()

            # Reverse so the order is chronological (old -> new)
            for row in reversed(result):
                if row.query:
                    history.append({"role": "user", "content": str(row.query)})
                if row.response:
                    history.append({"role": "bot", "content": str(row.response)})
            
        except Exception as e:
            logger.error(f"Error reading history from SQL: {e}")
            return []

        return history

    def clear_history(self, user_id: int):
        """Deletes the user's history in the database (Soft Delete or Hard Delete)."""
        if not self.sql_engine:
            return

        try:
            query = text("UPDATE dbo.[query_chatbots_logs] SET active = 0 WHERE user_id = :uid")
            
            with self.sql_engine.begin() as conn:
                conn.execute(query, {"uid": user_id})
            
            logger.info(f"SQL history deleted for user {user_id}")

        except Exception as e:
            logger.error(f"Error deleting history in SQL: {e}")

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