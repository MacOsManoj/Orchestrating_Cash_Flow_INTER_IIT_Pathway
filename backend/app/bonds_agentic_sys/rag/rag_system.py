"""
RAG System with Vector Storage
Stores and retrieves information from news, CRISIL documents, RBI policies
"""

import chromadb
from chromadb.config import Settings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from typing import List, Dict, Any, Optional
import json
from datetime import datetime, timedelta
import hashlib

from schemas_v2 import (
    DocumentChunk,
    RAGQuery,
    RAGResult,
    DataSource,
    NewsArticle,
    CreditRating,
)
from dotenv import load_dotenv

load_dotenv()


class RAGSystem:
    """
    Vector database system for storing and retrieving documents
    """

    def __init__(self, config):
        self.config = config

        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=config.vector_db_path, settings=Settings(anonymized_telemetry=False)
        )

        # Create collections
        self.news_collection = self.client.get_or_create_collection(
            name="news_articles", metadata={"description": "Financial news articles"}
        )

        self.crisil_collection = self.client.get_or_create_collection(
            name="crisil_documents",
            metadata={"description": "CRISIL credit rating documents"},
        )

        self.rbi_collection = self.client.get_or_create_collection(
            name="rbi_policies",
            metadata={"description": "RBI monetary policy documents"},
        )

        # Initialize embeddings
        self.embeddings = OpenAIEmbeddings(
            model=config.embedding_model, api_key=config.openai_api_key
        )

        # Text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.rag_chunk_size,
            chunk_overlap=config.rag_chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def _generate_doc_id(self, content: str, source: str) -> str:
        """Generate unique document ID"""
        hash_input = f"{content}{source}{datetime.now().date()}"
        return hashlib.md5(hash_input.encode()).hexdigest()

    def index_news_article(self, article: NewsArticle) -> str:
        """
        Index a news article into vector database
        """
        # Create full text
        full_text = f"{article.title}\n\n{article.content or article.summary or ''}"

        # Generate chunks
        chunks = self.text_splitter.split_text(full_text)

        # Generate doc_id
        doc_id = self._generate_doc_id(full_text, article.source)
        article.doc_id = doc_id

        # Prepare metadata
        metadata = {
            "title": article.title,
            "source": article.source,
            "url": article.url,
            "sentiment": article.sentiment_score,
            "relevance": article.relevance_score,
            "published_at": article.published_at.isoformat()
            if article.published_at
            else None,
            "entities": json.dumps(article.entities),
            "doc_id": doc_id,
        }

        # Generate embeddings
        embeddings = self.embeddings.embed_documents(chunks)

        # Add to collection
        self.news_collection.add(
            documents=chunks,
            embeddings=embeddings,
            metadatas=[
                {**metadata, "chunk_id": f"{doc_id}_{i}"} for i in range(len(chunks))
            ],
            ids=[f"{doc_id}_{i}" for i in range(len(chunks))],
        )

        return doc_id

    def index_crisil_document(self, content: str, rating_info: CreditRating) -> str:
        """
        Index CRISIL document
        """
        # Split into chunks
        chunks = self.text_splitter.split_text(content)

        # Generate doc_id
        doc_id = self._generate_doc_id(content, "CRISIL")
        rating_info.doc_id = doc_id

        # Metadata
        metadata = {
            "issuer": rating_info.issuer,
            "isin": rating_info.isin or "",
            "rating": rating_info.rating,
            "outlook": rating_info.outlook,
            "rating_date": rating_info.rating_date.isoformat(),
            "source_url": rating_info.source_url,
            "doc_id": doc_id,
            "pd": rating_info.probability_default,
            "spread": rating_info.credit_spread,
        }

        # Embeddings
        embeddings = self.embeddings.embed_documents(chunks)

        # Add to collection
        self.crisil_collection.add(
            documents=chunks,
            embeddings=embeddings,
            metadatas=[
                {**metadata, "chunk_id": f"{doc_id}_{i}"} for i in range(len(chunks))
            ],
            ids=[f"{doc_id}_{i}" for i in range(len(chunks))],
        )

        return doc_id

    def index_rbi_policy(
        self, content: str, policy_date: datetime, policy_type: str = "MPC_Minutes"
    ) -> str:
        """
        Index RBI policy document
        """
        chunks = self.text_splitter.split_text(content)
        doc_id = self._generate_doc_id(content, "RBI")

        metadata = {
            "policy_date": policy_date.isoformat(),
            "policy_type": policy_type,
            "doc_id": doc_id,
            "source": "RBI",
        }

        embeddings = self.embeddings.embed_documents(chunks)

        self.rbi_collection.add(
            documents=chunks,
            embeddings=embeddings,
            metadatas=[
                {**metadata, "chunk_id": f"{doc_id}_{i}"} for i in range(len(chunks))
            ],
            ids=[f"{doc_id}_{i}" for i in range(len(chunks))],
        )

        return doc_id

    def retrieve(
        self, query: RAGQuery, collection_names: List[str] = None
    ) -> RAGResult:
        """
        Retrieve relevant documents from vector database
        """
        if collection_names is None:
            collection_names = ["news_articles", "crisil_documents", "rbi_policies"]

        # Generate query embedding
        query_embedding = self.embeddings.embed_query(query.query_text)

        all_chunks = []
        all_scores = []
        all_sources = []

        # Query each collection
        for collection_name in collection_names:
            collection = self.client.get_collection(collection_name)

            # Build where filter
            where_filter = None
            if query.filters:
                where_filter = {}
                for key, value in query.filters.items():
                    if isinstance(value, list):
                        where_filter[key] = {"$in": value}
                    else:
                        where_filter[key] = value

            # Query
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=query.top_k,
                where=where_filter if where_filter else None,
            )

            # Process results
            if results["documents"]:
                docs = (
                    results["documents"][0]
                    if results.get("documents") and results["documents"]
                    else []
                )
                metadatas = (
                    results["metadatas"][0]
                    if results.get("metadatas") and results["metadatas"]
                    else []
                )
                distances = (
                    results["distances"][0]
                    if results.get("distances") and results["distances"]
                    else []
                )

                for doc, meta, dist in zip(docs, metadatas, distances):
                    # Convert distance to relevance score (1 - normalized distance)
                    relevance = 1.0 / (1.0 + dist)

                    if relevance >= query.min_relevance:
                        chunk = DocumentChunk(
                            doc_id=meta.get("doc_id", ""),
                            chunk_id=meta.get("chunk_id", ""),
                            content=doc,
                            metadata=meta,
                            source=DataSource(collection_name.split("_")[0]),
                            created_at=datetime.now(),
                        )

                        all_chunks.append(chunk)
                        all_scores.append(relevance)
                        all_sources.append(meta.get("source_url", collection_name))

        # Sort by relevance
        sorted_indices = sorted(
            range(len(all_scores)), key=lambda i: all_scores[i], reverse=True
        )
        all_chunks = [all_chunks[i] for i in sorted_indices[: query.top_k]]
        all_scores = [all_scores[i] for i in sorted_indices[: query.top_k]]
        all_sources = list(set([all_sources[i] for i in sorted_indices[: query.top_k]]))

        return RAGResult(
            query=query.query_text,
            chunks=all_chunks,
            relevance_scores=all_scores,
            sources=all_sources,
        )

    def retrieve_by_entity(
        self, entity: str, entity_type: str = "issuer", top_k: int = 5
    ) -> RAGResult:
        """
        Retrieve documents mentioning a specific entity
        """
        query = RAGQuery(query_text=entity, filters={entity_type: entity}, top_k=top_k)
        return self.retrieve(query)

    def retrieve_recent_news(
        self, keywords: List[str], days_back: int = 7, top_k: int = 10
    ) -> RAGResult:
        """
        Retrieve recent news matching keywords
        """
        query_text = " ".join(keywords)
        cutoff_date = datetime.now() - timedelta(days=days_back)

        query = RAGQuery(query_text=query_text, top_k=top_k)

        # Query news collection specifically
        query_embedding = self.embeddings.embed_query(query_text)

        results = self.news_collection.query(
            query_embeddings=[query_embedding], n_results=top_k
        )

        chunks = []
        scores = []
        sources = []

        if results["documents"]:
            docs = results["documents"][0]
            metadatas = results["metadatas"][0]
            distances = results["distances"][0]

            for doc, meta, dist in zip(docs, metadatas, distances):
                # Filter by date
                published_at = meta.get("published_at")
                if published_at:
                    pub_date = datetime.fromisoformat(published_at)
                    if pub_date < cutoff_date:
                        continue

                relevance = 1.0 / (1.0 + dist)

                chunk = DocumentChunk(
                    doc_id=meta.get("doc_id", ""),
                    chunk_id=meta.get("chunk_id", ""),
                    content=doc,
                    metadata=meta,
                    source=DataSource.NEWS,
                    created_at=datetime.now(),
                )

                chunks.append(chunk)
                scores.append(relevance)
                sources.append(meta.get("url", ""))

        return RAGResult(
            query=query_text,
            chunks=chunks,
            relevance_scores=scores,
            sources=list(set(sources)),
        )

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about stored documents"""
        stats = {}

        for name in ["news_articles", "crisil_documents", "rbi_policies"]:
            collection = self.client.get_collection(name)
            stats[name] = {"count": collection.count(), "name": name}

        return stats

    def clear_old_news(self, days_old: int = 90):
        """Remove news articles older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days_old)

        # Get all news items
        all_news = self.news_collection.get()

        ids_to_delete = []
        for i, meta in enumerate(all_news["metadatas"]):
            published_at = meta.get("published_at")
            if published_at:
                pub_date = datetime.fromisoformat(published_at)
                if pub_date < cutoff_date:
                    ids_to_delete.append(all_news["ids"][i])

        if ids_to_delete:
            self.news_collection.delete(ids=ids_to_delete)
            return len(ids_to_delete)
        return 0


def create_rag_system(config) -> RAGSystem:
    """Factory function"""
    return RAGSystem(config)
