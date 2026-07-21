# Arbitrage Tracker — общий Dockerfile для API и бота.
# По умолчанию стартует API на 8000-м порту. Для бота используйте
# docker-compose.yml сервис ``bot`` с командой ``python run_bot.py``.
#
# Сборка:
#   docker build -t arb-tracker .
# Запуск API:
#   docker run --rm -p 8000:8000 --env-file .env arb-tracker
# Запуск бота (отдельный контейнер):
#   docker run --rm --env-file .env arb-tracker python run_bot.py

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Системные зависимости (matplotlib нужны libgl/libgomp; остальное
# минимально, чтобы образ оставался тонким).
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        ca-certificates \
        libgomp1 \
        curl \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install -r requirements.txt openpyxl

COPY . .

# По умолчанию — API. Бот стартует переопределением CMD.
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
