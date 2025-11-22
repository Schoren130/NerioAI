FROM python:3.8-slim

WORKDIR /app

COPY requirements.txt .

RUN python -m pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PATH="/usr/local/bin:${PATH}"

CMD ["gunicorn", "--bind", ":8080", "app:app"]