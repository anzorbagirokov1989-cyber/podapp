from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
STATIC_DIR = Path(__file__).resolve().parent / "static"
MODEL_PATH = ARTIFACTS_DIR / "model.joblib"
FEATURES_PATH = ARTIFACTS_DIR / "features.json"

app = FastAPI(
    title="ПРОДЕТИ_РИСК — прогноз ПОД",
    description="API прогнозирования послеоперационного делирия у детей",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_meta: dict[str, Any] | None = None
_model = None
_key_to_column: dict[str, str] = {}


def _load_artifacts() -> None:
    global _meta, _model, _key_to_column
    if not MODEL_PATH.exists() or not FEATURES_PATH.exists():
        raise RuntimeError(
            "Артефакты модели не найдены. Запустите: python export_model.py"
        )
    _meta = json.loads(FEATURES_PATH.read_text(encoding="utf-8"))
    _model = joblib.load(MODEL_PATH)
    _key_to_column = {f["key"]: f["column"] for f in _meta["fields"]}


@app.on_event("startup")
def startup() -> None:
    _load_artifacts()


class PatientInput(BaseModel):
    """Один пациент — все признаки опциональны до расчёта; пустые → медиана в модели."""

    age_years: float | None = None
    age_months: float | None = None
    sex: int | None = None
    weight_kg: float | None = None
    height_cm: float | None = None
    surgery_type: int | None = None
    planned_duration: int | None = None
    asa_class: int | None = None
    neuro_comorbidity: int | None = None
    comorbidity_type: int | None = None
    prior_anesthesia_experience: int | None = None
    m_ypas: float | None = None
    anxiety_category: int | None = None
    premedication: int | None = None
    planned_anesthetic: int | None = None
    induction_method: int | None = None
    induction_behavior: int | None = None
    maintenance_anesthetic: int | None = None
    opioid_use: int | None = None
    opioid_dose: float | None = None
    dexmedetomidine_use: int | None = None
    dexmedetomidine_dose: float | None = None
    anesthesia_duration_min: float | None = None
    intraop_complications: int | None = None


class PredictRequest(BaseModel):
    patients: list[PatientInput] = Field(..., min_length=1)


class PredictionResult(BaseModel):
    probability: float
    label: int
    label_text: str
    risk_level: str


class PredictResponse(BaseModel):
    predictions: list[PredictionResult]
    threshold: float
    model_name: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/features")
def get_features() -> dict[str, Any]:
    return _meta


def _patient_to_row(patient: PatientInput) -> dict[str, float | None]:
    data = patient.model_dump()
    return {_key_to_column[k]: data.get(k) for k in _meta["feature_keys"]}


def _risk_level(probability: float) -> str:
    if probability >= 0.7:
        return "высокий"
    if probability >= 0.4:
        return "умеренный"
    return "низкий"


@app.post("/api/predict", response_model=PredictResponse)
def predict(body: PredictRequest) -> PredictResponse:
    if _model is None or _meta is None:
        raise HTTPException(503, "Модель не загружена")

    rows = [_patient_to_row(p) for p in body.patients]
    columns = [_key_to_column[k] for k in _meta["feature_keys"]]
    df = pd.DataFrame(rows, columns=columns)
    df = df.apply(pd.to_numeric, errors="coerce")

    try:
        proba = _model.predict_proba(df)[:, 1]
    except Exception as exc:
        raise HTTPException(400, f"Ошибка предсказания: {exc}") from exc

    threshold = float(_meta.get("threshold", 0.5))
    results: list[PredictionResult] = []
    for p in proba:
        label = int(p >= threshold)
        results.append(
            PredictionResult(
                probability=round(float(p), 4),
                label=label,
                label_text="ПОД: да" if label else "ПОД: нет",
                risk_level=_risk_level(float(p)),
            )
        )

    return PredictResponse(
        predictions=results,
        threshold=threshold,
        model_name=_meta.get("model_name", "model"),
    )


def _mount_frontend() -> None:
    if not STATIC_DIR.is_dir():
        return

    assets_dir = STATIC_DIR / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/")
    def spa_index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/{path:path}")
    def spa_fallback(path: str) -> FileResponse:
        if path.startswith("api") or path == "health":
            raise HTTPException(404)
        candidate = STATIC_DIR / path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(STATIC_DIR / "index.html")


_mount_frontend()
