"""GPT-OSS integration service for prompt enrichment."""
import requests
from utils.logging import logger

def query_gptoss(prompt: str) -> str:
    """Query local GPT-OSS model for prompt enrichment."""
    try:
        logger.info(f"[GPT-OSS] Enriching prompt: '{prompt[:50]}{'...' if len(prompt) > 50 else ''}'")
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "gpt-oss",
                "prompt": prompt,
                "stream": False
            },
            timeout=10  # Reduced timeout for faster fallback
        )
        
        if response.status_code == 200:
            enriched = response.json().get("response", "").strip()
            logger.info(f"[GPT-OSS] Enriched successfully: '{enriched[:50]}{'...' if len(enriched) > 50 else ''}'")
            return enriched
        else:
            logger.warning(f"[GPT-OSS] Request failed with status {response.status_code}")
            return prompt  # Fallback to original prompt
            
    except requests.exceptions.ConnectionError:
        logger.warning("[GPT-OSS] GPT-OSS unavailable - falling back to original prompt")
        return prompt  # Fallback to original prompt
    except requests.exceptions.Timeout:
        logger.warning("[GPT-OSS] Request timeout - falling back to original prompt")
        return prompt
    except Exception as e:
        logger.warning(f"[GPT-OSS] Error querying GPT-OSS: {e}")
        return prompt  # Fallback to original prompt