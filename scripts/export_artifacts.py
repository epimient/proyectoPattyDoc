"""One-off: reconstruye preprocessors.pkl desde el Excel de datos.

Uso: python -m scripts.export_artifacts
"""
import pandas as pd

from app.core.config import DATA_PATH
from app.models.artifacts import build_artifacts, save_artifacts
from app.models.preprocessing import (
    CATEGORICAL_COLUMNS,
    FEATURE_COLUMNS,
    NUMERIC_COLUMNS,
    preprocess_data,
)


def main():
    df_raw = pd.read_excel(DATA_PATH)
    categorical_defaults = {
        col: str(df_raw[col].mode()[0]) for col in CATEGORICAL_COLUMNS
    }
    df, le_dict, target_encoders, scaler, num_classes = preprocess_data(df_raw)

    payload = build_artifacts(
        df=df,
        le_dict=le_dict,
        target_encoders=target_encoders,
        scaler=scaler,
        num_classes=num_classes,
        categorical_defaults=categorical_defaults,
    )
    save_artifacts(payload)

    print(f"Filas preprocesadas: {len(df)}")
    print(f"Features ({len(FEATURE_COLUMNS)}): {FEATURE_COLUMNS}")
    print(f"Clases por fase: {num_classes}")
    print(f"Defaults categoricos: {categorical_defaults}")


if __name__ == "__main__":
    main()
