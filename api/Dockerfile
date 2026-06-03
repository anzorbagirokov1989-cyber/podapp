FROM python:3.12-slim

WORKDIR /app/api

COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/export_model.py api/main.py ./
COPY "База_Многоцентровое_исследование_«ПРОДЕТИ_РИСК»_копия.xlsx" /data/dataset.xlsx

ENV DATASET_PATH=/data/dataset.xlsx
RUN python export_model.py

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
