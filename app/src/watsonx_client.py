"""
WatsonX AI client with exponential backoff retry and full call telemetry.

generate() returns a CallResult containing the generated text plus complete
token usage data extracted from the SDK's raw response object.

Token telemetry logged per call:
  model, input_tokens, output_tokens, total_tokens, stop_reason,
  latency_ms, attempt number.
"""
import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from ibm_watsonx_ai.credentials import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference

logger = logging.getLogger(__name__)


class WatsonxRetryExhausted(Exception):
    """Raised when all retry attempts have been exhausted."""


# ── Telemetry dataclass ────────────────────────────────────────────────── #

@dataclass
class CallTelemetry:
    """Token usage and timing for a single WatsonX inference call."""
    model_id: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    stop_reason: str = "unknown"
    latency_ms: float = 0.0
    attempts: int = 1                    # how many attempts before success
    raw_response: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id":     self.model_id,
            "input_tokens":  self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens":  self.total_tokens,
            "stop_reason":   self.stop_reason,
            "latency_ms":    round(self.latency_ms, 1),
            "attempts":      self.attempts,
        }


# ── Result dataclass ───────────────────────────────────────────────────── #

@dataclass
class CallResult:
    """Return type of WatsonxClient.generate() — text + full telemetry."""
    text: str
    telemetry: CallTelemetry


# ── Client ─────────────────────────────────────────────────────────────── #

class WatsonxClient:
    """
    Thin wrapper around IBM WatsonX ModelInference with:
    - Exponential backoff retry (2^attempt * base_delay + jitter)
    - Full token usage telemetry via generate() (not generate_text())
    - Structured per-call log line at INFO level

    Retryable:   rate-limit (429), 5xx, connection errors, timeouts.
    Not retried: 401 / 403 auth errors — fail fast.
    """

    def __init__(
        self,
        api_key: str,
        project_id: str,
        url: str = "https://us-south.ml.cloud.ibm.com",
        model_id: str = "mistralai/mistral-small-3-2-24b-instruct-2506",
        max_retries: int = 3,
        base_delay: float = 1.0,
    ):
        self._model_id = model_id
        self.max_retries = max_retries
        self.base_delay = base_delay

        credentials = Credentials(url=url, api_key=api_key)

        # Single model configuration — generous token budget for unified JSON output
        self._params = {
            "decoding_method": "greedy",
            "temperature": 0.1,
            "max_new_tokens": 1500,
            "min_new_tokens": 10,
            "repetition_penalty": 1.0,
        }

        self._model = ModelInference(
            model_id=model_id,
            params=self._params,
            credentials=credentials,
            project_id=project_id,
        )

        logger.info(
            "WatsonxClient ready | model=%s max_retries=%d max_new_tokens=%d",
            model_id,
            max_retries,
            self._params["max_new_tokens"],
        )

    # ------------------------------------------------------------------ #
    # Public interface                                                      #
    # ------------------------------------------------------------------ #

    def generate(self, prompt: str) -> CallResult:
        """
        Call the model with retry logic.

        Uses ModelInference.generate() (not generate_text()) so the full
        response dict — including token counts and stop reason — is available.

        Args:
            prompt: Fully-formed prompt string.

        Returns:
            CallResult with .text (generated string) and .telemetry (usage).

        Raises:
            WatsonxRetryExhausted: When all retry attempts are exhausted.
        """
        last_exc: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            t0 = time.perf_counter()
            try:
                logger.debug("WatsonX call | model=%s attempt=%d", self._model_id, attempt + 1)

                # Use generate() — returns full dict with token counts
                raw = self._model.generate(prompt=prompt, guardrails=False)
                latency_ms = (time.perf_counter() - t0) * 1000

                result_obj = raw.get("results", [{}])[0]
                generated_text = result_obj.get("generated_text", "")
                input_tokens   = int(result_obj.get("input_token_count", 0))
                output_tokens  = int(result_obj.get("generated_token_count", 0))
                stop_reason    = result_obj.get("stop_reason", "unknown")

                telemetry = CallTelemetry(
                    model_id=self._model_id,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=input_tokens + output_tokens,
                    stop_reason=stop_reason,
                    latency_ms=latency_ms,
                    attempts=attempt + 1,
                    raw_response=raw,
                )

                # ── Structured telemetry log line ────────────────────── #
                logger.info(
                    "WatsonX call complete | "
                    "model=%s | "
                    "input_tokens=%d | "
                    "output_tokens=%d | "
                    "total_tokens=%d | "
                    "stop_reason=%s | "
                    "latency_ms=%.1f | "
                    "attempt=%d/%d",
                    self._model_id,
                    input_tokens,
                    output_tokens,
                    input_tokens + output_tokens,
                    stop_reason,
                    latency_ms,
                    attempt + 1,
                    self.max_retries + 1,
                )

                return CallResult(text=generated_text, telemetry=telemetry)

            except Exception as exc:
                latency_ms = (time.perf_counter() - t0) * 1000
                last_exc = exc
                exc_str = str(exc)

                # Fail fast on authentication errors
                if any(kw in exc_str for kw in ("401", "403", "Unauthorized", "Forbidden")):
                    logger.error(
                        "WatsonX auth error (not retrying) | model=%s latency_ms=%.1f | %s",
                        self._model_id, latency_ms, exc_str[:200],
                    )
                    raise

                if attempt < self.max_retries:
                    wait = (2 ** attempt) * self.base_delay + random.uniform(0, 1)
                    logger.warning(
                        "WatsonX error | model=%s attempt=%d/%d latency_ms=%.1f retry_in=%.1fs | %s",
                        self._model_id,
                        attempt + 1,
                        self.max_retries + 1,
                        latency_ms,
                        wait,
                        exc_str[:200],
                    )
                    time.sleep(wait)
                else:
                    logger.error(
                        "WatsonX retries exhausted | model=%s attempts=%d | %s",
                        self._model_id,
                        self.max_retries + 1,
                        exc_str[:200],
                    )

        raise WatsonxRetryExhausted(
            f"WatsonX call failed after {self.max_retries + 1} attempts. "
            f"Last error: {last_exc}"
        ) from last_exc
