"""Entrenamiento completo del modelo desde el Excel.

Uso: python -m scripts.train
"""
import os

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from tensorflow.keras.models import load_model
from tensorflow.keras.utils import to_categorical

from app.core.config import DATA_PATH, MODEL_PATH
from app.models.artifacts import build_artifacts, save_artifacts
from app.models.neural import build_model
from app.models.preprocessing import (
    CATEGORICAL_COLUMNS,
    FEATURE_COLUMNS,
    TARGET_COLUMNS,
    preprocess_data,
)


def main(epochs: int = 50):
    df_raw = pd.read_excel(DATA_PATH)
    categorical_defaults = {col: str(df_raw[col].mode()[0]) for col in CATEGORICAL_COLUMNS}
    df, le_dict, target_encoders, scaler, num_classes = preprocess_data(df_raw)

    X = df[FEATURE_COLUMNS]
    y1 = to_categorical(df[TARGET_COLUMNS[0]], num_classes=num_classes[TARGET_COLUMNS[0]])
    y2 = to_categorical(df[TARGET_COLUMNS[1]], num_classes=num_classes[TARGET_COLUMNS[1]])
    y3 = to_categorical(df[TARGET_COLUMNS[2]], num_classes=num_classes[TARGET_COLUMNS[2]])

    stratify_label = y1.argmax(axis=1) * 10 + y2.argmax(axis=1)
    vals, counts = np.unique(stratify_label, return_counts=True)
    rare = pd.Series(stratify_label).isin(vals[counts == 1]).to_numpy()
    X_common, X_rare = X[~rare], X[rare]
    y1_common, y1_rare = y1[~rare], y1[rare]
    y2_common, y2_rare = y2[~rare], y2[rare]
    y3_common, y3_rare = y3[~rare], y3[rare]

    X_train, X_test, y1_train, y1_test, y2_train, y2_test, y3_train, y3_test = train_test_split(
        X_common, y1_common, y2_common, y3_common, test_size=0.2, random_state=42,
        stratify=stratify_label[~rare],
    )
    X_train = pd.concat([X_train, X_rare])
    y1_train = np.concatenate([y1_train, y1_rare])
    y2_train = np.concatenate([y2_train, y2_rare])
    y3_train = np.concatenate([y3_train, y3_rare])

    if os.path.exists(MODEL_PATH):
        model = load_model(MODEL_PATH)
        print(f"Modelo cargado desde {MODEL_PATH}")
    else:
        model = build_model(len(FEATURE_COLUMNS), [num_classes[c] for c in TARGET_COLUMNS])
        print("Modelo creado desde cero")

    model.fit(
        X_train, [y1_train, y2_train, y3_train],
        validation_data=(X_test, [y1_test, y2_test, y3_test]),
        epochs=epochs, batch_size=32, verbose=1,
    )

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    model.save(MODEL_PATH)
    print(f"Modelo guardado en {MODEL_PATH}")

    payload = build_artifacts(
        df=df, le_dict=le_dict, target_encoders=target_encoders,
        scaler=scaler, num_classes=num_classes, categorical_defaults=categorical_defaults,
    )
    save_artifacts(payload)

    predictions = model.predict(X_test, verbose=0)
    y_preds = [p.argmax(axis=1) for p in predictions]
    y_trues = [y.argmax(axis=1) for y in [y1_test, y2_test, y3_test]]
    for i, fase in enumerate(["Calentamiento", "Entrenamiento", "Enfriamiento"]):
        acc = accuracy_score(y_trues[i], y_preds[i])
        print(f"{fase} - Accuracy test: {acc:.2%}")


if __name__ == "__main__":
    main()
