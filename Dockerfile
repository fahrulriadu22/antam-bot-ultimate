FROM python:3.11-slim

# Install system dependencies + Chrome
RUN apt-get update && apt-get install -y \
    wget curl unzip \
    fonts-liberation libasound2 libatk-bridge2.0-0 libdrm2 libgbm1 \
    libnspr4 libnss3 libxcomposite1 libxdamage1 libxrandr2 xdg-utils \
    && wget -q -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get install -y /tmp/chrome.deb \
    && wget -q -O /tmp/chromedriver.zip https://storage.googleapis.com/chrome-for-testing-public/120.0.6099.109/linux64/chromedriver-linux64.zip \
    && unzip /tmp/chromedriver.zip -d /tmp/ \
    && mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/ \
    && chmod +x /usr/local/bin/chromedriver \
    && rm -rf /tmp/* \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

# Create streamlit config
RUN mkdir -p .streamlit
RUN echo '[server]' > .streamlit/config.toml && \
    echo 'headless = true' >> .streamlit/config.toml && \
    echo 'enableCORS = false' >> .streamlit/config.toml && \
    echo '' >> .streamlit/config.toml && \
    echo '[browser]' >> .streamlit/config.toml && \
    echo 'gatherUsageStats = false' >> .streamlit/config.toml

RUN pip install -r requirements.txt

EXPOSE 8501

# Run dengan environment variables untuk skip onboarding
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true", "--browser.gatherUsageStats=false"]
