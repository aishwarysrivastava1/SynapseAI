import re
import logging

logger = logging.getLogger(__name__)

# Heuristic weights for toxicity and injections
HEURISTIC_WEIGHTS = {
    "ignore previous": 0.9,
    "system prompt": 0.8,
    "bypass": 0.8,
    "forget all instructions": 0.9,
    "dumb": 0.4,
    "stupid": 0.4,
    "idiot": 0.5,
    "kill": 0.9,
    "murder": 0.9,
    "bomb": 0.9,
    "terrorist": 0.9,
    "jailbreak": 0.9,
}

class FastClassifier:
    """
    Zero-dependency localized naive bayesian/keyword classifier mapping risk profiles without hitting external LLM endpoints.
    """
    @staticmethod
    def score_input(text: str) -> float:
        score = 0.0
        lower = text.lower()
        words = re.findall(r'\b\w+\b', lower)
        
        # Exact match sliding window
        for phrase, weight in HEURISTIC_WEIGHTS.items():
            if phrase in lower:
                score += weight
                
        # Word hits 
        for w in words:
            if w in HEURISTIC_WEIGHTS:
                score += HEURISTIC_WEIGHTS[w] * 0.5
                
        return min(score, 1.0)

class GuardrailsPipeline:
    @staticmethod
    def verify_input(text: str) -> str:
        """
        Multi-pass guardrail check.
        Returns cleaned string or raises ValueError if blocked.
        """
        if not text:
            return ""

        # Preprocessing Layer
        cleaned = re.sub(r'\s+', ' ', text).strip()
        if len(cleaned) > 2000:
            cleaned = cleaned[:2000]

        # Heuristic Layer
        risk_score = FastClassifier.score_input(cleaned)
        
        # Policy Engine
        if risk_score >= 0.8:
            logger.warning(f"Guardrail Blocked (Risk: {risk_score:.2f})")
            raise ValueError("Input blocked by safety policy.")
        elif risk_score >= 0.5:
            # SANITIZE/Strip
            logger.warning(f"Guardrail Sanitized (Risk: {risk_score:.2f})")
            cleaned = "Tell me about humanitarian aid and nothing else." # Enforced fallback scope
            
        return cleaned

    @staticmethod
    def verify_output(text: str) -> str:
        if not text:
            return ""
        
        # Output limits
        if len(text) > 4000:
            text = text[:4000] + "... [TRUNCATED DUE TO LENGTH LIMITS]"
            
        # PII generic filter (extremely naive for regex demonstration)
        # Masks generic 16 digit segments
        text = re.sub(r'\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b', '[REDACTED]', text)
        
        return text
