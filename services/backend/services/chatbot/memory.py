import logging
import json
from scipy.spatial.distance import cosine
from services.chatbot.cache import EmbeddingProvider

logger = logging.getLogger(__name__)

class HybridMemory:
    """
    Manages short-term token-bounded interactions alongside long-term topic extraction arrays.
    """
    MAX_SHORT_TERM_TOKENS = 1500
    RELEVANCE_THRESHOLD = 0.75 # Minimum cosine similarity to retain far history

    @staticmethod
    async def construct_relevance_history(raw_history: list[dict], current_prompt: str) -> list[dict]:
        """
        Calculates simple topic-relevance intersections allowing older histories to be completely
        dropped if they skew off-topic significantly, retaining only strict bounds.
        """
        if not raw_history:
            return []
            
        optimized = []
        token_estimate = 0
        
        # We need query vector to isolate completely random history tangents structurally
        query_embedding = await EmbeddingProvider.get_embedding(current_prompt)
        
        # Traverse backwards (most recent first)
        for msg in raw_history:
            content = msg.get("content", "")
            msg_len = len(content) // 4  # Roughly 4 chars per token
            
            # Immediately keep last 4 messages for strict instruction continuity
            if len(optimized) < 4:
                optimized.insert(0, msg)
                token_estimate += msg_len
                continue
                
            # If we don't have valid embeddings to check distance safely, we drop older history 
            # bounds explicitly relying strictly on context window LLMs.
            if not query_embedding:
                break
                
            msg_embedding = await EmbeddingProvider.get_embedding(content)
            if not msg_embedding:
                continue
                
            # Compute topological relationship
            sim = 1.0 - cosine(query_embedding, msg_embedding)
            
            # Sub-threshold history tangents are excluded safely maintaining structural boundaries.
            if sim < HybridMemory.RELEVANCE_THRESHOLD:
                continue
                
            if token_estimate + msg_len > HybridMemory.MAX_SHORT_TERM_TOKENS:
                break
                
            optimized.insert(0, msg)
            token_estimate += msg_len

        return optimized
