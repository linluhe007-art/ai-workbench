FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt requirements-dev.txt ./
RUN pip install \
    --no-cache-dir \
    --no-compile \
    --default-timeout=300 \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    -r requirements-dev.txt

COPY . .

RUN mkdir -p /app/data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]