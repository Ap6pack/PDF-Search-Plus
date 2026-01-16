"""
Document similarity search for PDF Search Plus.

This module provides functionality for finding similar documents based on
text content. It uses TF-IDF vectorization and cosine similarity to
calculate document similarity.
"""

import numpy as np
import logging
from typing import List, Dict, Tuple, Optional, Set
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from pdf_search_plus.utils.db import PDFDatabase
from pdf_search_plus.utils.security import sanitize_text


class SimilaritySearch:
    """
    Document similarity search using TF-IDF and cosine similarity.
    
    This class provides methods for finding similar documents based on
    their text content. It uses TF-IDF vectorization to convert text
    into numerical vectors and cosine similarity to measure similarity.
    """
    
    def __init__(self, db: PDFDatabase):
        """
        Initialize the similarity search.
        
        Args:
            db: Database manager
        """
        self.db = db
        self.logger = logging.getLogger(__name__)
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.85
        )
    
    def get_document_text(self, pdf_id: int) -> str:
        """
        Get the combined text of a document.
        
        Args:
            pdf_id: ID of the PDF document
            
        Returns:
            Combined text of the document
            
        Raises:
            ValueError: If the document is not found
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get PDF text
                cursor.execute(
                    """
                    SELECT text FROM pages
                    WHERE pdf_id = ?
                    ORDER BY page_number
                    """,
                    (pdf_id,)
                )
                
                pdf_text = " ".join(row[0] for row in cursor.fetchall() if row[0])
                
                # Get OCR text
                cursor.execute(
                    """
                    SELECT ocr_text FROM ocr_text
                    WHERE pdf_id = ?
                    ORDER BY page_number
                    """,
                    (pdf_id,)
                )
                
                ocr_text = " ".join(row[0] for row in cursor.fetchall() if row[0])
                
                # Combine text
                combined_text = f"{pdf_text} {ocr_text}".strip()
                
                if not combined_text:
                    self.logger.warning(f"No text found for PDF ID {pdf_id}")
                    return ""
                
                return combined_text
        except Exception as e:
            self.logger.error(f"Error getting document text: {e}")
            raise
    
    def get_all_documents(self) -> Dict[int, str]:
        """
        Get all documents with their text.
        
        Returns:
            Dictionary mapping PDF IDs to document text
            
        Raises:
            Exception: If an error occurs while retrieving documents
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get all PDF IDs
                cursor.execute("SELECT id FROM pdf_files")
                pdf_ids = [row[0] for row in cursor.fetchall()]
                
                # Get text for each PDF
                documents = {}
                for pdf_id in pdf_ids:
                    text = self.get_document_text(pdf_id)
                    if text:
                        documents[pdf_id] = text
                
                return documents
        except Exception as e:
            self.logger.error(f"Error getting all documents: {e}")
            raise
    
    def find_similar_documents(self, pdf_id: int, threshold: float = 0.3, max_results: int = 10) -> List[Tuple[int, float]]:
        """
        Find documents similar to the given document.
        
        Args:
            pdf_id: ID of the PDF document to find similar documents for
            threshold: Similarity threshold (0-1, higher means more similar)
            max_results: Maximum number of results to return
            
        Returns:
            List of tuples containing (pdf_id, similarity_score) sorted by similarity
            
        Raises:
            ValueError: If the document is not found
            Exception: If an error occurs during similarity calculation
        """
        try:
            # Get the query document text
            query_text = self.get_document_text(pdf_id)
            if not query_text:
                raise ValueError(f"No text found for PDF ID {pdf_id}")
            
            # Get all documents
            documents = self.get_all_documents()
            if not documents:
                return []
            
            # Remove the query document from the corpus
            if pdf_id in documents:
                del documents[pdf_id]
            
            if not documents:
                return []
            
            # Create document IDs and corpus
            doc_ids = list(documents.keys())
            corpus = list(documents.values())
            
            # Add the query document to the end of the corpus
            corpus.append(query_text)
            
            # Vectorize the corpus
            try:
                tfidf_matrix = self.vectorizer.fit_transform(corpus)
            except Exception as e:
                self.logger.error(f"Error vectorizing documents: {e}")
                raise
            
            # Calculate cosine similarity between the query document and all other documents
            # Note: scipy sparse matrices have indexing but type stubs are incomplete
            query_vector = tfidf_matrix[-1]  # type: ignore[index]
            corpus_vectors = tfidf_matrix[:-1]  # type: ignore[index]

            similarities = cosine_similarity(query_vector, corpus_vectors).flatten()
            
            # Create a list of (pdf_id, similarity) tuples
            similarity_scores = list(zip(doc_ids, similarities))
            
            # Filter by threshold and sort by similarity (descending)
            filtered_scores = [
                (doc_id, score) for doc_id, score in similarity_scores
                if score >= threshold
            ]
            
            sorted_scores = sorted(filtered_scores, key=lambda x: x[1], reverse=True)
            
            # Limit the number of results
            return sorted_scores[:max_results]
        except ValueError as e:
            self.logger.error(f"Value error in similarity search: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error finding similar documents: {e}")
            raise
    
    def search_by_text(self, query_text: str, threshold: float = 0.3, max_results: int = 10) -> List[Tuple[int, float]]:
        """
        Find documents similar to the given text query.
        
        Args:
            query_text: Text to find similar documents for
            threshold: Similarity threshold (0-1, higher means more similar)
            max_results: Maximum number of results to return
            
        Returns:
            List of tuples containing (pdf_id, similarity_score) sorted by similarity
            
        Raises:
            ValueError: If the query text is empty
            Exception: If an error occurs during similarity calculation
        """
        # Sanitize the query text
        query_text = sanitize_text(query_text)
        
        if not query_text:
            raise ValueError("Query text cannot be empty")
            
        try:
            # Get all documents
            documents = self.get_all_documents()
            if not documents:
                return []
            
            # Create document IDs and corpus
            doc_ids = list(documents.keys())
            corpus = list(documents.values())
            
            # Add the query text to the end of the corpus
            corpus.append(query_text)
            
            # Vectorize the corpus
            try:
                tfidf_matrix = self.vectorizer.fit_transform(corpus)
            except Exception as e:
                self.logger.error(f"Error vectorizing documents: {e}")
                raise
            
            # Calculate cosine similarity between the query text and all documents
            # Note: scipy sparse matrices have indexing but type stubs are incomplete
            query_vector = tfidf_matrix[-1]  # type: ignore[index]
            corpus_vectors = tfidf_matrix[:-1]  # type: ignore[index]

            similarities = cosine_similarity(query_vector, corpus_vectors).flatten()
            
            # Create a list of (pdf_id, similarity) tuples
            similarity_scores = list(zip(doc_ids, similarities))
            
            # Filter by threshold and sort by similarity (descending)
            filtered_scores = [
                (doc_id, score) for doc_id, score in similarity_scores
                if score >= threshold
            ]
            
            sorted_scores = sorted(filtered_scores, key=lambda x: x[1], reverse=True)
            
            # Limit the number of results
            return sorted_scores[:max_results]
        except ValueError as e:
            self.logger.error(f"Value error in text similarity search: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error finding similar documents by text: {e}")
            raise
    
    def get_document_clusters(self, threshold: float = 0.3, min_cluster_size: int = 2) -> List[Set[int]]:
        """
        Cluster documents based on similarity.
        
        Args:
            threshold: Similarity threshold (0-1, higher means more similar)
            min_cluster_size: Minimum number of documents in a cluster
            
        Returns:
            List of sets, where each set contains PDF IDs in a cluster
            
        Raises:
            Exception: If an error occurs during clustering
        """
        try:
            # Get all documents
            documents = self.get_all_documents()
            if not documents:
                return []
            
            # Create document IDs and corpus
            doc_ids = list(documents.keys())
            corpus = list(documents.values())
            
            # Vectorize the corpus
            try:
                tfidf_matrix = self.vectorizer.fit_transform(corpus)
            except Exception as e:
                self.logger.error(f"Error vectorizing documents: {e}")
                raise
            
            # Calculate pairwise cosine similarity
            similarity_matrix = cosine_similarity(tfidf_matrix)
            
            # Create clusters using a simple threshold-based approach
            clusters = []
            visited = set()
            
            for i, doc_id in enumerate(doc_ids):
                if doc_id in visited:
                    continue
                    
                # Start a new cluster
                cluster = {doc_id}
                visited.add(doc_id)
                
                # Find similar documents
                for j, other_id in enumerate(doc_ids):
                    if other_id == doc_id or other_id in visited:
                        continue
                        
                    if similarity_matrix[i, j] >= threshold:
                        cluster.add(other_id)
                        visited.add(other_id)
                
                # Add the cluster if it meets the minimum size
                if len(cluster) >= min_cluster_size:
                    clusters.append(cluster)
            
            return clusters
        except Exception as e:
            self.logger.error(f"Error clustering documents: {e}")
            raise
