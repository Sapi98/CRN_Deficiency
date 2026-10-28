"""Deployment-configurable web limits, shared by HTTP and analysis workers."""
import os


def positive_integer(name, default):
    """Read an optional positive integer; reject invalid deployment settings."""
    try:
        value = int(os.environ.get(name, default))
    except ValueError:
        raise ValueError(f'{name} must be a positive integer') from None
    if value <= 0:
        raise ValueError(f'{name} must be a positive integer')
    return value


MAX_INPUT_BYTES = positive_integer('CRNT_WEB_MAX_INPUT_BYTES', 1024 * 1024)
MAX_RESULT_BYTES = positive_integer('CRNT_WEB_MAX_RESULT_BYTES', 8 * 1024 * 1024)
MAX_COMPLEXES = positive_integer('CRNT_WEB_MAX_COMPLEXES', 10000)
MAX_REACTIONS = positive_integer('CRNT_WEB_MAX_REACTIONS', 50000)
MAX_RENDER_COMPLEXES = positive_integer('CRNT_WEB_MAX_RENDER_COMPLEXES', 300)
MAX_RENDER_REACTIONS = positive_integer('CRNT_WEB_MAX_RENDER_REACTIONS', 1000)
ANALYSIS_TIMEOUT = positive_integer('CRNT_WEB_TIMEOUT_SECONDS', 60)
# Dash sends result state back for some callbacks; budget for JSON/base64 overhead.
MIN_REQUEST_BYTES = max(8 * MAX_INPUT_BYTES, 3 * MAX_RESULT_BYTES)
MAX_REQUEST_BYTES = positive_integer('CRNT_WEB_MAX_REQUEST_BYTES', MIN_REQUEST_BYTES)
if MAX_REQUEST_BYTES < MIN_REQUEST_BYTES:
    raise ValueError(f'CRNT_WEB_MAX_REQUEST_BYTES must be at least {MIN_REQUEST_BYTES} '
                     'for the configured input/result sizes')


def input_size_message():
    return f'Models must be at most {MAX_INPUT_BYTES / 1048576:g} MiB ({MAX_INPUT_BYTES:,} bytes).'
