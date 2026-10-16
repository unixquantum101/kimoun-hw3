FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Injected by Jenkins. APP_VERSION is the exact git tag, so a running
# container always reports which release it was built from.
ARG APP_VERSION=dev
ARG GIT_SHA=unknown
ARG BUILD_NUMBER=0
ENV APP_VERSION=$APP_VERSION \
    GIT_SHA=$GIT_SHA \
    BUILD_NUMBER=$BUILD_NUMBER

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

RUN useradd --create-home --shell /usr/sbin/nologin appuser
USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:5000/health').status==200 else 1)"

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]
