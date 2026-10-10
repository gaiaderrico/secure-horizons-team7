"""`python -m mirage.core [port]` == `uvicorn mirage.core.api:app --port 8000`."""

import sys

import uvicorn

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    uvicorn.run("mirage.core.api:app", host="127.0.0.1", port=port)
