import logging

logger = logging.getLogger(__name__)

class TokenOptimizer:
    @staticmethod
    def minimize_tokens(history: list[dict], max_messages: int = 10) -> list[dict]:
        """
        Preprocesses and compresses history to minimize costs.
        Instead of calling an LLM to summarize every time to save tokens,
        we use an aggressive sliding window approach and filter large repetitive payloads.
        """
        if not history:
            return []

        # Sliding window: keep only the most recent 'max_messages'
        compressed = history[-max_messages:]
        
        # We could implement a real summarization strategy here, e.g.:
        # If history length > max_messages, substitute the truncated start 
        # with a generic summarized prefix.
        
        optimized_history = []
        for msg in compressed:
            # Deduplicate huge text loops or unnecessary JSON blobs inside history
            content = msg.get("content", "")
            if len(content) > 1000:
                # Keep first and last 400 chars of very long history messages to prevent token blowout
                content = content[:400] + f"\n... [removed {len(content)-800} chars] ...\n" + content[-400:]
                
            optimized_history.append({
                "role": msg.get("role", "user"),
                "content": content
            })

        return optimized_history
