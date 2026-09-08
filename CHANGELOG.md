# Changelog

## 1.2.3 (2026-09-08)

- Capture the traceback of an unhandled view exception via `process_exception`
  and store it in the 5xx log entry as `{"error", "traceback"}`. Django converts
  the exception to a 500 response before the middleware runs, so the previous
  `try/except` around `get_response` never fired in a real request.
- 5xx logging is now on by default. The setting is renamed
  `DRF_API_LOGGER_LOG_SERVER_ERRORS`; `DRF_API_LOG_SERVER_ERROR` still works.
- The fallback exception path now respects the setting instead of bypassing it.
- Tracebacks and the error repr are truncated from the head to the response body
  limit, and query parameters in them are masked (body-shaped text is not).

## 1.2.2 (fork, 2026-06-27)

- Log 5xx responses regardless of content type behind `DRF_API_LOG_SERVER_ERROR`.
- Decode non-JSON bodies safely; `text/*` bodies are stored as text.
