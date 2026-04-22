import numpy as np
from typing import List, Optional
from sentence_transformers import SentenceTransformer
from agent2.file import File
from agent2.element import Element

class EmbeddingsModel:
    def __init__(self, model: SentenceTransformer):
        """
        Initialize embeddings model with a SentenceTransformer instance
        
        Args:
            model: Pre-trained SentenceTransformer model
        """
        self.model = model

    def create_docs(self, files: List[File]):
        """
        Generate embeddings for all elements (including nested) in files 
        that don't have embeddings
        
        Args:
            files: List of File objects to process
        """
        # Collect all elements needing embeddings (flattened hierarchy)
        elements_to_embed = []
        for file in files:
            stack = list(file.elements)
            while stack:
                element = stack.pop()
                if element.embedding is None:
                    elements_to_embed.append(element)
                # Add sub-elements to process
                stack.extend(element.elements)
        
        # Generate embeddings in batches
        if elements_to_embed:
            texts = [element.content for element in elements_to_embed]
            embeddings = self.model.encode(texts, show_progress_bar=True)
            
            # Assign embeddings back to elements as lists
            for element, embedding in zip(elements_to_embed, embeddings):
                element.embedding = embedding.tolist()

    def search_docs(self, files: List[File], query: str, count: int) -> List[dict]:
        """
        Search across all elements (including nested) in files for matches to query
        
        Args:
            files: List of File objects to search
            query: Search query string
            count: Number of matches to return
            
        Returns:
            List of match dictionaries with file and element references
        """
        # Get query embedding
        query_embedding = self.model.encode([query], prompt_name="s2p_query")[0]
        
        # Collect all elements with embeddings (flattened hierarchy)
        elements = []
        for file in files:
            stack = list(file.elements)
            while stack:
                element = stack.pop()
                if element.embedding is not None:
                    elements.append((file, element))
                stack.extend(element.elements)
        
        # Calculate similarities
        similarities = []
        for file, element in elements:
            element_embedding = np.array(element.embedding)
            similarity = self._cosine_similarity(query_embedding, element_embedding)
            similarities.append((file, element, similarity))
        
        # Sort by similarity and return top results
        similarities.sort(key=lambda x: x[2], reverse=True)
        return [{
            'file': file.path,  # Updated from file.file_path to file.path
            'element': element,
            'similarity': similarity
        } for file, element, similarity in similarities[:count]]

    def get_top_matches(self, files: List[File], query: str, 
                       similarity_percent: float = 0.5, 
                       max_count: int = 5) -> List[dict]:
        """
        Get matches above similarity threshold across all elements (including nested)
        
        Args:
            files: List of File objects to search
            query: Search query string
            similarity_percent: Minimum similarity threshold (0-1)
            max_count: Maximum number of matches to return
            
        Returns:
            List of match dictionaries with file and element references
        """
        # Get query embedding
        query_embedding = self.model.encode([query])[0]
        
        # Collect all elements with embeddings (flattened hierarchy)
        elements = []
        for file in files:
            stack = list(file.elements)
            while stack:
                element = stack.pop()
                if element.embedding is not None:
                    elements.append((file, element))
                stack.extend(element.elements)
        
        # Calculate similarities and filter by threshold
        matches = []
        for file, element in elements:
            element_embedding = np.array(element.embedding)
            similarity = self._cosine_similarity(query_embedding, element_embedding)
            
            if similarity >= similarity_percent:
                matches.append({
                    'file': file.path,  # Updated from file.file_path to file.path
                    'element': element,
                    'similarity': similarity
                })
                if len(matches) >= max_count:
                    break
        
        return matches

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two vectors
        
        Args:
            vec1: First vector (query embedding)
            vec2: Second vector (element embedding)
            
        Returns:
            Cosine similarity between vectors (0-1)
        """
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))