"""Сравнение моделей, ROC и feature importance → reports/ + model_metrics.json."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import (
    GradientBoostingClassifier,
    HistGradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import RocCurveDisplay, roc_auc_score, roc_curve
from sklearn.model_selection import StratifiedKFold, cross_val_predict, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

RANDOM_STATE = 42
ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "База_Многоцентровое_исследование_«ПРОДЕТИ_РИСК»_копия.xlsx"
REPORTS = ROOT / "reports"
TARGET_COL = "Послеоперационный делирий (0 нет,1 да)"

SHORT_NAMES = {
    "Поведение при индукции (1 спокойно,2 умеренное беспокойство,3 выраженное беспокойство,4 выраженная борьба)": "Поведение при индукции",
    "Длительность анестезии (мин)": "Длит. анестезии",
    "Тип операции (1 офтальмологическая,2 ЛОР,3 стоматологическая,4 урологическая,5 ортопедическая,6 другое)": "Тип операции",
    "m-YPAS, %": "m-YPAS",
    "Возраст (годы)": "Возраст, лет",
    "Возраст (месяцы)": "Возраст, мес",
}


def load_data() -> tuple[pd.DataFrame, np.ndarray, list[str], list[str]]:
    raw = pd.read_excel(DATA_PATH, sheet_name=0, header=None)
    df = raw.iloc[2:].copy()
    df.columns = raw.iloc[1].tolist()
    feature_cols = list(df.columns[3:27])
    data = df.dropna(subset=[TARGET_COL]).copy()
    X = data[feature_cols].apply(pd.to_numeric, errors="coerce")
    y = data[TARGET_COL].astype(int).values
    display_names = [SHORT_NAMES.get(c, c.split("(")[0].strip()) for c in feature_cols]
    return X, y, feature_cols, display_names


def build_models() -> dict[str, Pipeline]:
    models: dict[str, Pipeline] = {
        "Логистическая регрессия": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                (
                    "clf",
                    LogisticRegression(
                        max_iter=3000,
                        class_weight="balanced",
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),
        "Случайный лес": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "clf",
                    RandomForestClassifier(
                        n_estimators=300,
                        max_depth=4,
                        min_samples_leaf=3,
                        class_weight="balanced",
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),
        "Gradient Boosting (sklearn)": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "clf",
                    GradientBoostingClassifier(
                        n_estimators=120,
                        max_depth=2,
                        learning_rate=0.05,
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),
        "HistGradientBoosting": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "clf",
                    HistGradientBoostingClassifier(
                        max_depth=3,
                        learning_rate=0.05,
                        max_iter=200,
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),
    }
    try:
        from xgboost import XGBClassifier  # noqa: PLC0415

        models["XGBoost"] = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "clf",
                    XGBClassifier(
                        n_estimators=120,
                        max_depth=2,
                        learning_rate=0.05,
                        subsample=0.9,
                        colsample_bytree=0.9,
                        eval_metric="logloss",
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        )
    except Exception:
        pass
    return models


def plot_roc_cv(cv_results: dict, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 6))
    colors = sns.color_palette("deep", len(cv_results))
    for (name, res), color in zip(cv_results.items(), colors):
        ax.plot(
            res["fpr"],
            res["tpr"],
            lw=2,
            color=color,
            label=f"{name} (AUC={res['auc']:.3f})",
        )
    ax.plot([0, 1], [0, 1], "k--", lw=1, alpha=0.5)
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC: прогноз ПОД (5-fold stratified CV)")
    ax.legend(loc="lower right", fontsize=8)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_roc_holdout(models: dict, X, y, out_path: Path) -> dict[str, float]:
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=RANDOM_STATE
    )
    holdout_aucs: dict[str, float] = {}
    n = len(models)
    fig, axes = plt.subplots(1, n, figsize=(4 * n, 4))
    if n == 1:
        axes = [axes]
    for ax, (name, pipe) in zip(axes, models.items()):
        pipe.fit(X_train, y_train)
        proba = pipe.predict_proba(X_test)[:, 1]
        holdout_aucs[name] = float(roc_auc_score(y_test, proba))
        RocCurveDisplay.from_predictions(y_test, proba, ax=ax, name=name)
        ax.set_title(f"{name}\nAUC hold-out = {holdout_aucs[name]:.3f}")
    plt.suptitle("ROC на отложенной выборке (20%)", y=1.02)
    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return holdout_aucs


def plot_feature_importance(
    models: dict,
    display_names: list[str],
    out_rf: Path,
    out_gb: Path,
) -> dict[str, list[dict]]:
    def bar_plot(importances, title: str, path: Path) -> list[dict]:
        imp = np.asarray(importances, dtype=float)
        order = np.argsort(imp)[::-1]
        top = order[:15]
        fig, ax = plt.subplots(figsize=(9, 6))
        labels = [display_names[i] for i in top]
        vals = imp[top]
        ax.barh(labels[::-1], vals[::-1], color="#4C78A8")
        ax.set_xlabel("Важность")
        ax.set_title(title)
        plt.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        total = imp.sum() or 1.0
        rows = []
        for i in order[:10]:
            rows.append(
                {
                    "feature": display_names[i],
                    "importance": round(float(imp[i]), 4),
                    "share_pct": round(100 * float(imp[i]) / total, 1),
                }
            )
        return rows

    X, y, _, display_names = load_data()
    rankings: dict[str, list[dict]] = {}

    rf_pipe = models["Случайный лес"]
    rf_pipe.fit(X, y)
    rf_clf = rf_pipe.named_steps["clf"]
    rankings["random_forest"] = bar_plot(
        rf_clf.feature_importances_,
        "Случайный лес — Gini importance (полная выборка)",
        out_rf,
    )

    gb_key = "Gradient Boosting (sklearn)"
    if gb_key in models:
        gb_pipe = models[gb_key]
        gb_pipe.fit(X, y)
        gb_clf = gb_pipe.named_steps["clf"]
        rankings["gradient_boosting"] = bar_plot(
            gb_clf.feature_importances_,
            "Gradient Boosting — importance (полная выборка)",
            out_gb,
        )
    return rankings


def main() -> None:
    sns.set_theme(style="whitegrid", context="notebook")
    REPORTS.mkdir(parents=True, exist_ok=True)

    X, y, _, display_names = load_data()
    models = build_models()
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)

    cv_results: dict[str, dict] = {}
    comparison: list[dict] = []
    for name, pipe in models.items():
        proba = cross_val_predict(pipe, X, y, cv=cv, method="predict_proba")[:, 1]
        fpr, tpr, _ = roc_curve(y, proba)
        auc_cv = float(roc_auc_score(y, proba))
        cv_results[name] = {"fpr": fpr.tolist(), "tpr": tpr.tolist(), "auc": auc_cv}
        comparison.append({"model": name, "auc_cv": round(auc_cv, 3)})

    plot_roc_cv(cv_results, REPORTS / "roc_cv.png")
    holdout_aucs = plot_roc_holdout(models, X, y, REPORTS / "roc_holdout.png")
    for row in comparison:
        row["auc_holdout"] = round(holdout_aucs[row["model"]], 3)

    rankings = plot_feature_importance(
        models,
        display_names,
        REPORTS / "feature_importance_rf.png",
        REPORTS / "feature_importance_gb.png",
    )

    best_cv = max(comparison, key=lambda r: r["auc_cv"])
    best_hold = max(comparison, key=lambda r: r["auc_holdout"])

    metrics = {
        "n_samples": int(len(y)),
        "n_features": int(X.shape[1]),
        "pod_rate": round(float(y.mean()), 3),
        "models": comparison,
        "best_cv": best_cv["model"],
        "best_holdout": best_hold["model"],
        "feature_importance_top_rf": rankings.get("random_forest", []),
        "xgboost_available": "XGBoost" in models,
        "figures": {
            "roc_cv": "reports/roc_cv.png",
            "roc_holdout": "reports/roc_holdout.png",
            "feature_importance_rf": "reports/feature_importance_rf.png",
            "feature_importance_gb": "reports/feature_importance_gb.png",
        },
    }
    (REPORTS / "model_metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
