import time

from groq import APIConnectionError, APITimeoutError, InternalServerError, RateLimitError

# Transient failures worth retrying: rate limits, connection hiccups, timeouts,
# and 5xx errors from Groq's servers. Anything else (bad request, auth failure,
# etc.) is a real error and should surface immediately instead of being retried.
RETRYABLE_GROQ_ERRORS = (RateLimitError, APIConnectionError, APITimeoutError, InternalServerError)


def invoke_with_retry(chain, payload, *, max_attempts=3, base_delay_seconds=2.0, logger=None):
    """
    Calls `chain.invoke(payload)`, retrying on transient Groq failures (rate
    limits, timeouts, connection errors, 5xx) with exponential backoff.

    Groq's free tier has strict per-minute request caps, so a single
    rate-limited call shouldn't immediately fail that stock's whole analysis;
    this gives it `max_attempts` tries with increasing delay (2s, 4s, 8s, ...)
    before giving up and letting the exception propagate to the caller's
    existing per-stock try/except.

    `logger` is an optional callable (e.g. st.session_state.analysis_logs.append)
    used to record each retry; if omitted, retries happen silently.
    """
    last_exception = None
    for attempt in range(1, max_attempts + 1):
        try:
            return chain.invoke(payload)
        except RETRYABLE_GROQ_ERRORS as e:
            last_exception = e
            if attempt == max_attempts:
                break
            delay = base_delay_seconds * (2 ** (attempt - 1))
            if logger:
                logger(
                    f"Groq call failed ({type(e).__name__}: {e}); "
                    f"retrying in {delay:.0f}s (attempt {attempt}/{max_attempts})..."
                )
            time.sleep(delay)

    raise last_exception
