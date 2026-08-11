import pandas as pd
from sklearn.preprocessing import StandardScaler, LabelEncoder

NUMERIC_COLUMNS = ["Edad", "IMC", "Tiempo de Actividad Física"]

CATEGORICAL_COLUMNS = [
    "Género",
    "Nivel de Visión",
    "Condición Física",
    "Condición Comórbida",
    "Preferencia de Accesibilidad",
    "Entorno de Ejercicio",
    "Motivación",
]

FEATURE_COLUMNS = NUMERIC_COLUMNS + CATEGORICAL_COLUMNS

TARGET_COLUMNS = [
    "Ejercicios Fase 1 de Calentamiento",
    "Ejercicios Fase 2 de Entrenamiento",
    "Ejercicios Fase 3 de Enfriamiento",
]

PHASE_NAMES = ["Calentamiento", "Entrenamiento", "Enfriamiento"]


def preprocess_data(df):
    df = df.copy()
    df[NUMERIC_COLUMNS] = df[NUMERIC_COLUMNS].apply(pd.to_numeric, errors="coerce").fillna(df[NUMERIC_COLUMNS].mean())
    cat_cols = df.columns.difference(NUMERIC_COLUMNS)
    df[cat_cols] = df[cat_cols].fillna("No aplica")

    le_dict = {}
    for col in CATEGORICAL_COLUMNS:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col].astype(str))
        le_dict[col] = le

    target_encoders = {}
    num_classes = {}
    for col in TARGET_COLUMNS:
        df[col] = df[col].apply(lambda x: x.split(";")[0].strip() if isinstance(x, str) else x)
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col].astype(str))
        target_encoders[col] = le
        num_classes[col] = len(le.classes_)

    scaler = StandardScaler()
    df[NUMERIC_COLUMNS] = scaler.fit_transform(df[NUMERIC_COLUMNS])

    return df, le_dict, target_encoders, scaler, num_classes
