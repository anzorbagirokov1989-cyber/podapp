# ПРОДЕТИ_РИСК — прогноз ПОД (PoC)

Proof-of-concept прогнозирования **послеоперационного делирия (ПОД)** у детей: Jupyter-анализ, API (FastAPI) и React-таблица для ввода данных.

## Структура

| Путь | Описание |
|------|----------|
| `pod_delirium_poc.ipynb` | Обучение и ROC / feature importance |
| `api/` | Backend: модель (Random Forest), `/api/predict` |
| `web/` | React-приложение с таблицей ввода |
| `docker-compose.yml` | Запуск API + фронтенда |

## Docker (рекомендуется)

```bash
cd susana
docker compose up --build
```

- **UI:** http://localhost:8080 — таблица пациентов, колонка **Делирий** с прогнозом и вероятностью  
- **API:** http://localhost:8002/docs (внутри Docker — порт 8000)  

При сборке образа `api` модель переобучается на xlsx из корня `susana/`.

## Локальная разработка

### 1. Модель и API

```bash
cd susana
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r api/requirements.txt
python api/export_model.py          # создаёт api/artifacts/
cd api && uvicorn main:app --reload --port 8001
```

> Если порт 8000 занят другим сервисом, используйте 8001 и прокси в `web/vite.config.ts`.

### 2. Фронтенд

```bash
cd susana/web
npm install
npm run dev    # http://localhost:5173
```

Vite проксирует `/api` на `http://localhost:8000`. При API на 8001 измените `server.proxy` в `vite.config.ts`.

## Модель

- **Алгоритм:** случайный лес (лучший AUC на CV ≈ 0.81 в notebook)
- **Признаки:** 24 клинических и интраоперационных (без PACU — без утечки целевой переменной)
- **Выход:** вероятность ПОД, бинарный класс (порог 0.5), уровень риска

## Jupyter

```bash
source .venv/bin/activate
jupyter notebook pod_delirium_poc.ipynb
```
