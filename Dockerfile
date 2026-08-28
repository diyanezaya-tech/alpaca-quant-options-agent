FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Alpaca CLI oficial (github.com/alpacahq/cli), pin v0.0.13 -- mismo binario
# que se usa local en tools/alpaca.exe -- para que cli_executor.py lo
# encuentre vía PATH (shutil.which("alpaca")) y siga ejecutando órdenes por
# CLI, no por el SDK, cumpliendo el requisito "Trading API, MCP server and
# CLI" del hackathon.
RUN curl -sL -o /tmp/alpaca-cli.tar.gz \
      https://github.com/alpacahq/cli/releases/download/v0.0.13/cli_0.0.13_linux_amd64.tar.gz \
    && echo "50cd254d81b6bbc541259eeeb4bb1a8f7c319557fa49fc3b2765cddd72a66a82  /tmp/alpaca-cli.tar.gz" | sha256sum -c - \
    && tar -xzf /tmp/alpaca-cli.tar.gz -C /tmp \
    && mv /tmp/alpaca /usr/local/bin/alpaca \
    && chmod +x /usr/local/bin/alpaca \
    && rm /tmp/alpaca-cli.tar.gz \
    && alpaca version

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD ["python", "live_agent.py", "--use-cli"]
