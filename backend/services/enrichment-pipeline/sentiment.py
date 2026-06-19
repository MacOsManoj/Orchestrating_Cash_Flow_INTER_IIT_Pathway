"""
FinBERT Sentiment Analyzer
- Real FinBERT model (ProsusAI/finbert)
- GPU acceleration when available
- Returns label, score, confidence
"""

import logging
from typing import Any, Dict

import numpy as np
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

logger = logging.getLogger(__name__)


class FinBERTAnalyzer:
    """FinBERT sentiment analysis for financial news"""

    LABELS = ["positive", "negative", "neutral"]
    MODEL_NAME = "ProsusAI/finbert"

    def __init__(self):
        self.tokenizer = None
        self.model = None
        self.device = None
        self._initialize()

    def _initialize(self):
        """Load FinBERT model"""
        try:
            logger.info(f"Loading FinBERT model: {self.MODEL_NAME}")

            self.tokenizer = AutoTokenizer.from_pretrained(self.MODEL_NAME)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                self.MODEL_NAME
            )

            # Use GPU if available
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model.to(self.device)
            self.model.eval()

            logger.info(f"FinBERT loaded on {self.device}")
        except Exception as e:
            logger.error(f"Failed to load FinBERT: {e}")
            raise

    def analyze(self, text: str, title: str = None) -> Dict[str, Any]:
        """
        Analyze sentiment of text using FinBERT.

        For short/poor content, relies more on title analysis.
        For long texts, analyzes multiple chunks and aggregates results.

        Args:
            text: Full text content to analyze
            title: Article title (analyzed separately if content is short)

        Returns:
            {
                'label': 'positive'|'negative'|'neutral',
                'score': float (0-1),
                'confidence': 'high'|'medium'|'low',
                'scores': {'positive': float, 'negative': float, 'neutral': float}
            }
        """
        if not text or not self.model:
            return self._default_result()

        try:
            # If content is very short (likely failed fetch), analyze title separately
            # and mark as low confidence
            if len(text) < 200 and title:
                logger.warning(
                    f"Short content ({len(text)} chars), using title for sentiment"
                )

                inputs = self.tokenizer(
                    title,
                    return_tensors="pt",
                    truncation=True,
                    max_length=512,
                    padding=True,
                ).to(self.device)

                with torch.no_grad():
                    outputs = self.model(**inputs)
                    probs = torch.nn.functional.softmax(outputs.logits, dim=-1)

                scores = probs[0].cpu().numpy()
                max_idx = np.argmax(scores)

                return {
                    "label": self.LABELS[max_idx],
                    "score": float(scores[max_idx]),
                    "confidence": "low",  # Always low confidence for title-only
                    "scores": {
                        "positive": float(scores[0]),
                        "negative": float(scores[1]),
                        "neutral": float(scores[2]),
                    },
                }

            # For longer texts, analyze strategically selected chunks
            chunks = []
            chunk_size = 450  # Leave room for tokenization

            # Strategy: Focus on beginning (most important in news)
            if len(text) > chunk_size:
                # First chunk (highest weight)
                chunks.append(text[:chunk_size])

                # Only add more chunks if text is substantially longer
                if len(text) > chunk_size * 2:
                    # Middle chunk
                    mid_start = len(text) // 2 - chunk_size // 2
                    chunks.append(text[mid_start : mid_start + chunk_size])
            else:
                chunks = [text]

            # Analyze each chunk
            all_scores = []
            for chunk in chunks:
                inputs = self.tokenizer(
                    chunk,
                    return_tensors="pt",
                    truncation=True,
                    max_length=512,
                    padding=True,
                ).to(self.device)

                with torch.no_grad():
                    outputs = self.model(**inputs)
                    probs = torch.nn.functional.softmax(outputs.logits, dim=-1)

                all_scores.append(probs[0].cpu().numpy())

            # Aggregate scores (first chunk gets 70%, rest split 30%)
            if len(all_scores) == 1:
                scores = all_scores[0]
            else:
                weights = [0.7] + [0.3 / (len(all_scores) - 1)] * (len(all_scores) - 1)
                scores = np.average(all_scores, axis=0, weights=weights)

            max_idx = np.argmax(scores)
            label = self.LABELS[max_idx]
            score = float(scores[max_idx])

            # Confidence level - stricter thresholds
            if score > 0.85:
                confidence = "high"
            elif score > 0.65:
                confidence = "medium"
            else:
                confidence = "low"

            return {
                "label": label,
                "score": score,
                "confidence": confidence,
                "scores": {
                    "positive": float(scores[0]),
                    "negative": float(scores[1]),
                    "neutral": float(scores[2]),
                },
            }

        except Exception as e:
            logger.error(f"Sentiment analysis error: {e}")
            return self._default_result()

    @staticmethod
    def _default_result() -> Dict[str, Any]:
        """Default result for errors/empty text"""
        return {
            "label": "neutral",
            "score": 0.5,
            "confidence": "low",
            "scores": {"positive": 0.33, "negative": 0.33, "neutral": 0.34},
        }
