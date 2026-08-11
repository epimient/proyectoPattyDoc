import os
os.environ['TCL_LIBRARY'] = r'C:\Users\Laboratorio CIE 1\AppData\Local\Programs\Python\Python313\tcl\tcl8.6'
os.environ['TK_LIBRARY'] = r'C:\Users\Laboratorio CIE 1\AppData\Local\Programs\Python\Python313\tcl\tk8.6'

import pandas as pd
import numpy as np
import tkinter as tk
from tkinter import ttk, scrolledtext
import pyttsx3
import time
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Dense, Input
# pyrefly: ignore [missing-import]
from tensorflow.keras.utils import to_categorical

# Function to preprocess the dataset
def preprocess_data(df):
    # Imputacion separada: media para numericas, 'No aplica' para categoricas
    num_cols = ['Edad', 'IMC', 'Tiempo de Actividad Física']
    df[num_cols] = df[num_cols].apply(pd.to_numeric, errors='coerce').fillna(df[num_cols].mean())
    cat_cols = df.columns.difference(num_cols)
    df[cat_cols] = df[cat_cols].fillna('No aplica')

    feature_columns = ['Edad', 'Género', 'IMC', 'Nivel de Visión', 'Condición Física', 
                       'Tiempo de Actividad Física', 'Condición Comórbida', 
                       'Preferencia de Accesibilidad', 'Entorno de Ejercicio', 'Motivación']
    target_columns = ['Ejercicios Fase 1 de Calentamiento', 'Ejercicios Fase 2 de Entrenamiento', 
                      'Ejercicios Fase 3 de Enfriamiento']
    
    le_dict = {}
    for col in ['Género', 'Nivel de Visión', 'Condición Física', 'Condición Comórbida', 
                'Preferencia de Accesibilidad', 'Entorno de Ejercicio', 'Motivación']:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col].astype(str))
        le_dict[col] = le
    
    target_encoders = {}
    num_classes = {}
    for col in target_columns:
        df[col] = df[col].apply(lambda x: x.split(';')[0].strip() if isinstance(x, str) else x)
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col].astype(str))
        target_encoders[col] = le
        num_classes[col] = len(le.classes_)
    
    scaler = StandardScaler()
    df[['Edad', 'IMC', 'Tiempo de Actividad Física']] = scaler.fit_transform(
        df[['Edad', 'IMC', 'Tiempo de Actividad Física']]
    )
    
    return df, feature_columns, target_columns, le_dict, target_encoders, scaler, num_classes

# Accessibility: Announce fitness plan
def announce_plan(plan, language='es', rate=150):
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', rate)
        engine.setProperty('volume', 0.9)
        voices = engine.getProperty('voices')
        for voice in voices:
            if language in voice.id.lower():
                engine.setProperty('voice', voice.id)
                break
        for phase, exercise in plan.items():
            engine.say(f"{phase}: {exercise}")

        # Bucle manual: runAndWait corta tras la 1ra frase en Python 3.13
        engine.startLoop(False)
        while engine.isBusy():
            engine.iterate()
            time.sleep(0.02)
        engine.endLoop()
    except Exception as e:
        print(f"Error announcing plan: {e}. Please ensure audio output is available.")

# ==========================================
#  Función que crea y muestra la ventana
# ==========================================
def mostrar_plan_grafico(user_data, plan):

    window = tk.Tk()
    window.title("Plan de Acondicionamiento Físico Personalizado")
    window.geometry("650x600")
    window.configure(bg="#f0f4f8")

    # Estilo
    style = ttk.Style()
    style.configure("TLabel", background="#f0f4f8", font=("Helvetica", 11))
    style.configure("Header.TLabel", font=("Helvetica", 16, "bold"), background="#f0f4f8")
    style.configure("Phase.TLabel", font=("Helvetica", 13, "bold"), foreground="#2c3e50")

    # Título
    ttk.Label(window, text="Plan de Ejercicio Personalizado", style="Header.TLabel").pack(pady=(20, 10))

    # Frame datos del usuario
    frame_user = ttk.LabelFrame(window, text="Datos de la persona", padding=10)
    frame_user.pack(fill="x", padx=20, pady=5)

    # Mostrar datos del usuario en dos columnas
    row = 0
    for key, value in user_data.items():
        ttk.Label(frame_user, text=f"{key}:", font=("Helvetica", 10, "bold")).grid(row=row, column=0, sticky="e", padx=10, pady=3)
        ttk.Label(frame_user, text=str(value), wraplength=400).grid(row=row, column=1, sticky="w", pady=3)
        row += 1

    # Separador
    ttk.Separator(window, orient="horizontal").pack(fill="x", padx=20, pady=15)

    # Título del plan
    ttk.Label(window, text="Plan sugerido", style="Header.TLabel").pack(pady=(0,10))

    # Área con scroll para el plan
    plan_frame = ttk.Frame(window)
    plan_frame.pack(fill="both", expand=True, padx=20, pady=5)

    canvas = tk.Canvas(plan_frame, bg="white")
    scrollbar = ttk.Scrollbar(plan_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Mostrar cada fase
    for phase, exercise in plan.items():
        phase_label = ttk.Label(scrollable_frame, text=phase.upper(), style="Phase.TLabel")
        phase_label.pack(anchor="w", pady=(15,5), padx=10)

        ex_label = ttk.Label(scrollable_frame, text=exercise, wraplength=550, justify="left")
        ex_label.pack(anchor="w", padx=30, pady=(0,10))

    # Botones inferiores
    btn_frame = ttk.Frame(window)
    btn_frame.pack(pady=20)

    def reproducir():
        announce_plan(plan)

    ttk.Button(btn_frame, text="Reproducir plan en voz", command=reproducir, width=25).pack(side="left", padx=10)
    ttk.Button(btn_frame, text="Cerrar", command=window.destroy, width=15).pack(side="left", padx=10)

    window.mainloop()

# Define the neural network model
def build_model(input_dim, output_dims):
    inputs = Input(shape=(input_dim,))
    x = Dense(128, activation='relu')(inputs)
    x = Dense(64, activation='relu')(x)
    output1 = Dense(output_dims[0], activation='softmax', name='phase1')(x)
    output2 = Dense(output_dims[1], activation='softmax', name='phase2')(x)
    output3 = Dense(output_dims[2], activation='softmax', name='phase3')(x)
    
    model = Model(inputs=inputs, outputs=[output1, output2, output3])
    model.compile(optimizer='adam',
                  loss={'phase1': 'categorical_crossentropy',
                        'phase2': 'categorical_crossentropy',
                        'phase3': 'categorical_crossentropy'},
                  metrics={'phase1': 'accuracy',
                           'phase2': 'accuracy',
                           'phase3': 'accuracy'})
    return model

# Diagnostic function
def diagnostico_excel(df, le_dict, target_columns, target_encoders):
    print("\n Diagnóstico del archivo Excel:\n")
    print(" Tipos de datos por columna:")
    print(df.dtypes)
    print("\n")
    print(" Valores únicos en columnas categóricas:")
    for col in le_dict.keys():
        print(f"- {col}: {df[col].unique()} (Encoded: {le_dict[col].classes_})")
    print("\n")
    print(" Verificación de etiquetas nuevas en columnas de salida:")
    for col in target_columns:
        encoder = target_encoders.get(col)
        if encoder:
            nuevas = set(df[col].astype(str)) - set(encoder.classes_)
            if nuevas:
                print(f"- {col}: etiquetas nuevas detectadas → {nuevas}")
            else:
                print(f"- {col}: sin etiquetas nuevas")
        else:
            print(f"- {col}: no se encontró encoder asociado")
    print("\n Diagnóstico completo.\n")

# Function to generate fitness plan
def generate_fitness_plan(model, input_data, scaler, le_dict, target_encoders, is_preprocessed=False):
    input_df = pd.DataFrame([input_data])
    
    if not is_preprocessed:
        # Encode categorical features if input is not preprocessed
        for col in ['Género', 'Nivel de Visión', 'Condición Física', 'Condición Comórbida', 
                    'Preferencia de Accesibilidad', 'Entorno de Ejercicio', 'Motivación']:
            input_df[col] = le_dict[col].transform(input_df[col].astype(str))
        # Scale numerical features
        input_df[['Edad', 'IMC', 'Tiempo de Actividad Física']] = scaler.transform(
            input_df[['Edad', 'IMC', 'Tiempo de Actividad Física']]
        )
    
    predictions = model.predict(input_df)
    plan = {
        'Calentamiento': target_encoders['Ejercicios Fase 1 de Calentamiento'].inverse_transform(
            [np.argmax(predictions[0])])[0],
        'Entrenamiento': target_encoders['Ejercicios Fase 2 de Entrenamiento'].inverse_transform(
            [np.argmax(predictions[1])])[0],
        'Enfriamiento': target_encoders['Ejercicios Fase 3 de Enfriamiento'].inverse_transform(
            [np.argmax(predictions[2])])[0]
    }
    return plan

# Function to collect feedback and update model
def collect_feedback(plan, feedback, df, model, feature_columns, target_columns, scaler, le_dict, target_encoders, num_classes):
    if feedback['suitable']:
        print("Feedback: Plan is suitable. No updates needed.")
        return model, target_encoders, num_classes
    
    new_row = pd.DataFrame([feedback['input_data'].copy()])
    
    # Preprocesar el dato nuevo ANTES de concatenarlo (mismo formato que df)
    for col in ['Género', 'Nivel de Visión', 'Condición Física', 'Condición Comórbida',
                'Preferencia de Accesibilidad', 'Entorno de Ejercicio', 'Motivación']:
        val = str(new_row[col].iloc[0])
        if val not in le_dict[col].classes_:
            le_dict[col].classes_ = np.append(le_dict[col].classes_, val)
        new_row[col] = le_dict[col].transform([val])[0]
    
    new_row[['Edad', 'IMC', 'Tiempo de Actividad Física']] = scaler.transform(
        new_row[['Edad', 'IMC', 'Tiempo de Actividad Física']]
    )
    
    # Codificar ejercicios corregidos, expandiendo encoders si hay etiqueta nueva
    for col, fase in zip(target_columns, ['Calentamiento', 'Entrenamiento', 'Enfriamiento']):
        val = feedback['corrected_exercises'][fase]
        if val not in target_encoders[col].classes_:
            target_encoders[col].classes_ = np.append(target_encoders[col].classes_, val)
            num_classes[col] = len(target_encoders[col].classes_)
        new_row[col] = target_encoders[col].transform([val])[0]
    
    df = pd.concat([df, new_row], ignore_index=True)
    
    X = df[feature_columns]
    y1 = to_categorical(df['Ejercicios Fase 1 de Calentamiento'], num_classes=num_classes['Ejercicios Fase 1 de Calentamiento'])
    y2 = to_categorical(df['Ejercicios Fase 2 de Entrenamiento'], num_classes=num_classes['Ejercicios Fase 2 de Entrenamiento'])
    y3 = to_categorical(df['Ejercicios Fase 3 de Enfriamiento'], num_classes=num_classes['Ejercicios Fase 3 de Enfriamiento'])
    
    model = build_model(input_dim=len(feature_columns), output_dims=[num_classes['Ejercicios Fase 1 de Calentamiento'],
                                                                    num_classes['Ejercicios Fase 2 de Entrenamiento'],
                                                                    num_classes['Ejercicios Fase 3 de Enfriamiento']])
    model.fit(X, [y1, y2, y3], epochs=10, batch_size=32, verbose=0)
    print("Model retrained with feedback.")
    return model, target_encoders, num_classes

# Main execution
if __name__ == "__main__":
    MODEL_PATH = "artifacts/modelo5.keras"

    df = pd.read_excel("data/Datos generados con modelo.xlsx")
    df, feature_columns, target_columns, le_dict, target_encoders, scaler, num_classes = preprocess_data(df)
    
    diagnostico_excel(df, le_dict, target_columns, target_encoders)
    
    X = df[feature_columns]
    y1 = to_categorical(df['Ejercicios Fase 1 de Calentamiento'], num_classes=num_classes['Ejercicios Fase 1 de Calentamiento'])
    y2 = to_categorical(df['Ejercicios Fase 2 de Entrenamiento'], num_classes=num_classes['Ejercicios Fase 2 de Entrenamiento'])
    y3 = to_categorical(df['Ejercicios Fase 3 de Enfriamiento'], num_classes=num_classes['Ejercicios Fase 3 de Enfriamiento'])
    
    # Estratificar por combinacion de fase 1 y 2 (etiquetas demasiado esparsas
    # con las 3 fases, y1+y2 es lo que sugiere el readme)
    stratify_label = y1.argmax(axis=1) * 10 + y2.argmax(axis=1)
    vals, counts = np.unique(stratify_label, return_counts=True)
    rare = pd.Series(stratify_label).isin(vals[counts == 1]).to_numpy()
    X_common, X_rare = X[~rare], X[rare]
    y1_common, y1_rare = y1[~rare], y1[rare]
    y2_common, y2_rare = y2[~rare], y2[rare]
    y3_common, y3_rare = y3[~rare], y3[rare]

    X_train, X_test, y1_train, y1_test, y2_train, y2_test, y3_train, y3_test = train_test_split(
        X_common, y1_common, y2_common, y3_common, test_size=0.2, random_state=42,
        stratify=stratify_label[~rare]
    )
    # Reincorporar las clases singulares al train
    X_train = pd.concat([X_train, X_rare])
    y1_train = np.concatenate([y1_train, y1_rare])
    y2_train = np.concatenate([y2_train, y2_rare])
    y3_train = np.concatenate([y3_train, y3_rare])
    
    if os.path.exists(MODEL_PATH):
        from tensorflow.keras.models import load_model
        model = load_model(MODEL_PATH)
        print(f"Modelo cargado desde {MODEL_PATH}")
    else:
        model = build_model(
            input_dim=len(feature_columns),
            output_dims=[num_classes['Ejercicios Fase 1 de Calentamiento'],
                         num_classes['Ejercicios Fase 2 de Entrenamiento'],
                         num_classes['Ejercicios Fase 3 de Enfriamiento']]
        )
        model.fit(
            X_train, [y1_train, y2_train, y3_train],
            validation_data=(X_test, [y1_test, y2_test, y3_test]),
            epochs=50, batch_size=32, verbose=1
        )
    
    # Select a random record from the dataset
    sample_input = df[feature_columns].sample(n=1).to_dict(orient='records')[0]
    
    # Reverse preprocessing for human-readable input
    readable_input = sample_input.copy()
    inverted = scaler.inverse_transform([[sample_input['Edad'], sample_input['IMC'], sample_input['Tiempo de Actividad Física']]])[0]
    readable_input['Edad'] = inverted[0]
    readable_input['IMC'] = inverted[1]
    readable_input['Tiempo de Actividad Física'] = inverted[2]
    for col in ['Género', 'Nivel de Visión', 'Condición Física', 'Condición Comórbida', 
                'Preferencia de Accesibilidad', 'Entorno de Ejercicio', 'Motivación']:
        readable_input[col] = le_dict[col].inverse_transform([int(sample_input[col])])[0]
    
    print("\nRandomly Selected Input:")
    for key, value in readable_input.items():
        print(f"{key}: {value}")
    
    # Pass preprocessed input to generate_fitness_plan
    plan = generate_fitness_plan(model, sample_input, scaler, le_dict, target_encoders, is_preprocessed=True)
    mostrar_plan_grafico(readable_input, plan)
    print("\nSuggested Fitness Plan:")
    for phase, exercise in plan.items():
        print(f"{phase}: {exercise}")
    
    announce_plan(plan)
    
    feedback = {
        'suitable': False,
        'input_data': readable_input,  # Use human-readable input for feedback
        'corrected_exercises': {
            'Calentamiento': 'Rotaciones articulares suaves',
            'Entrenamiento': 'Caminata en el lugar',
            'Enfriamiento': 'Respiraciones profundas'
        }
    }
    
    model, target_encoders, num_classes = collect_feedback(plan, feedback, df, model, feature_columns, target_columns, scaler, le_dict, target_encoders, num_classes)
    model.save(MODEL_PATH)
    print(f"Modelo guardado en {MODEL_PATH}")