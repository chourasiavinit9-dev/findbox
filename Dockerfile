# syntax=docker/dockerfile:1
FROM python:3.11-slim

LABEL org.opencontainers.image.title="findbox"
LABEL org.opencontainers.image.description="Drop it in. Forget it. Find it by what you remember. Local AI file organizer powered by open-weight Gemma."
LABEL org.opencontainers.image.source="https://github.com/chourasiavinit9-dev/findbox"
LABEL org.opencontainers.image.licenses="MIT"

# ── System deps for PDF/DOCX text extraction ──────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    # For python-docx (already pure-python, but lxml needs libxml2)
    libxml2-dev \
    libxslt1-dev \
    # Curl for Ollama health check
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── App user (never run as root) ──────────────────────────────
RUN useradd -m -u 1000 sloth
WORKDIR /app

# ── Install Python deps ───────────────────────────────────────
# findbox uses stdlib only — no pip install needed!
# Optional: install python-docx for .docx support
# RUN pip install --no-cache-dir python-docx

# ── Copy source ───────────────────────────────────────────────
COPY --chown=sloth:sloth . /app

RUN mkdir -p /inbox /home/sloth/SlothBox && chown -R sloth:sloth /inbox /home/sloth/SlothBox

# ── Volume for the user's inbox and SlothBox output ───────────
# Mount your Downloads/Desktop etc. here:
#   docker run -v ~/Downloads:/inbox -v ~/SlothBox:/home/sloth/SlothBox findbox
VOLUME ["/inbox", "/home/sloth/SlothBox"]

# ── Expose the local web UI port ──────────────────────────────
EXPOSE 8765

# ── Switch to non-root user ───────────────────────────────────
USER sloth

# ── Environment ───────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1 \
    SLOTH_HOME=/home/sloth/SlothBox \
    SLOTHBOX_INBOX=/inbox \
    # Point Ollama to host machine (change if Ollama runs elsewhere)
    OLLAMA_HOST=http://host.docker.internal:11434

# ── Default: run the web UI ───────────────────────────────────
# Override with: docker run ... findbox python3 sloth_box.py run --apply
CMD ["python3", "sloth_box.py", "serve", "--host", "0.0.0.0"]
