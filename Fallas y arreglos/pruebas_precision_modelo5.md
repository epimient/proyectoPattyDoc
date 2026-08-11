# Plan de pruebas de precision - `fitness_plan_model5.py`

## Objetivo
Medir la precision del modelo 5 al predecir ejercicios para cada fase (calentamiento, entrenamiento, enfriamiento) e identificar problemas de aprendizaje.

---

## Problemas identificados que afectan la precision

### P1 - Split con separador incorrecto (`:32`)
```python
df[col] = df[col].apply(lambda x: x.split(',')[0].strip() if isinstance(x, str) else x)
```
Usa `','` pero los datos usan `'; '`. El label de entrenamiento termina siendo el string completo tipo `"Marcha en el lugar con cuerda guia; Elevacion de rodillas alternadas"`. Cada combinacion unica de 2 ejercicios se convierte en una clase distinta. El modelo memoriza pares en vez de aprender ejercicios individuales. La precision en test puede verse alta artificialmente porque solo hay que acertar el par exacto, pero el modelo no generaliza.

### P2 - Sin `stratify` en `train_test_split` (`:269-271`)
Si una clase tiene pocas muestras, puede caer toda en train o toda en test. Si cae toda en test, el modelo nunca aprendio esa clase -> precision 0%. Si cae toda en train, la metrica de test no refleja que exista.

### P3 - `collect_feedback` corrupto (`:220-255`)
Cuando se da feedback, el reentrenamiento corrompe el dataset completo. Las predicciones posteriores son esencialmente aleatorias. La precision post-feedback es impredecible y tipicamente mala.

### P4 - Sin guardado de modelo
Cada ejecucion es desde cero. No hay forma de medir si el modelo mejora con el tiempo o con feedback.

---

## Plan de pruebas

### Fase 1 - Pruebas de caja negra (estado actual)

Ejecutar el modelo existente y extraer metricas reales sobre el test set:

```python
# Despues del entrenamiento, en lugar de solo una prediccion:

predictions = model.predict(X_test)
y1_pred = predictions[0].argmax(axis=1)
y2_pred = predictions[1].argmax(axis=1)
y3_pred = predictions[2].argmax(axis=1)

y1_true = y1_test.argmax(axis=1)
y2_true = y2_test.argmax(axis=1)
y3_true = y3_test.argmax(axis=1)

from sklearn.metrics import classification_report, confusion_matrix

for i, fase in enumerate(['Calentamiento', 'Entrenamiento', 'Enfriamiento']):
    print(f"=== FASE {i+1} - {fase} ===")
    print(classification_report([y1_true, y2_true, y3_true][i], [y1_pred, y2_pred, y3_pred][i]))
```

**Metricas a extraer:**
- Accuracy global por fase
- Precision, recall, f1-score por clase (ejercicio individual)
- Matriz de confusion para detectar clases que nunca acierta
- Conteo de muestras por clase (detectar desbalanceo)

### Fase 2 - Distribucion de clases

Antes del split, inspeccionar cuantas muestras tiene cada clase:

```python
for col in target_columns:
    print(f"\n=== {col} ===")
    print(df[col].value_counts())
```

Esto revela:
- Clases con 1-2 muestras (imposible de aprender)
- Si el separador incorrecto genera clases artificiales
- Nivel de desbalanceo del dataset

### Fase 3 - Pruebas de coherencia logica

Probar inputs especificos que deberian dar resultados predecibles:

| Input | Resultado esperado |
|-------|-------------------|
| Edad > 60, Condicion Limitada | Ejercicios de baja intensidad |
| Ceguera Total | Ejercicios con guias tactiles/auditivas |
| IMC > 35, Obesidad Severa | Ejercicios de bajo impacto |

Si el modelo da resultados contradictorios (ej: ejercicio avanzado para alguien con condicion limitada), hay un problema de fondo en el aprendizaje.

### Fase 4 - Prueba de feedback

1. Ejecutar, obtener prediccion inicial sobre un registro
2. Dar feedback incorrecto (cambiar ejercicios)
3. Volver a predecir el mismo input
4. Verificar:
   - Que la nueva prediccion coincida con el feedback dado
   - Que la precision en otros inputs no se degrade drasticamente
   - Que los encoders no se hayan corrompido (verificar clases disponibles antes y despues)

### Fase 5 - Comparacion antes/despues de correcciones

1. Ejecutar Fase 1 con el codigo actual (bugs incluidos)
2. Corregir bugs (separador, fillna, collect_feedback)
3. Re-ejecutar Fase 1 y comparar metricas

---

## Interpretacion de resultados

| Escenario | Que esperar |
|-----------|-------------|
| Accuracy ~100% en test | Sospechoso. Probablemente el split incorrecto creo una clase por combinacion unica y el modelo memorizo. Revisar con Fase 2. |
| Accuracy baja (~30-50%) | El modelo no aprende patrones. Revisar desbalanceo y coherencia logica. |
| Accuracy ~70-85% | Razonable para datos sinteticos. Verificar que no haya fuga de datos. |
| Precision 0% en alguna clase | Clase minoritaria sin representacion en train. Agregar stratify. |

---

## Script de diagnostico rapido

Agregar al final del `__main__` (antes del feedback hardcodeado):

```python
# === DIAGNOSTICO DE PRECISION ===
print("\n" + "="*60)
print("DIAGNOSTICO DE PRECISION")
print("="*60)

# Distribucion de clases
for col in target_columns:
    counts = df[col].value_counts()
    print(f"\n--- {col} ({len(counts)} clases) ---")
    print(counts)

# Metricas en test set
predictions = model.predict(X_test)
y_preds = [p.argmax(axis=1) for p in predictions]
y_trues = [y.argmax(axis=1) for y in [y1_test, y2_test, y3_test]]

from sklearn.metrics import accuracy_score
for i, fase in enumerate(['Calentamiento', 'Entrenamiento', 'Enfriamiento']):
    acc = accuracy_score(y_trues[i], y_preds[i])
    print(f"\n{fase} - Accuracy: {acc:.2%}")
```

---

## Clasificacion de errores por gravedad

### Criticos - Impiden el funcionamiento correcto

#### E1 - Separador incorrecto en split (`:32`)

**Gravedad:** Critico

**Que es:** Usa `split(',')` pero los datos usan `'; '`.

**Por que ocurre:** El CSV se genero con `'; '.join(...)` en `ModeloDatos.py` pero el codigo asume separador por coma.

**Como afecta la precision:**
- Cada par de ejercicios (`"Marcha...; Elevacion..."`) se convierte en una clase unica
- El numero de clases escala combinatorialmente en vez de mantenerse en ~4 por fase
- El modelo memoriza combinaciones exactas, no aprende ejercicios
- Accuracy en test puede verse artificialmente alta, pero el modelo no generaliza a nuevas combinaciones
- Cuando se de feedback con un ejercicio nuevo, la prediccion colapsa

**Solucion:**
```python
df[col] = df[col].apply(lambda x: x.split(';')[0].strip() if isinstance(x, str) else x)
```

#### E2 - fillna masivo en todo el DataFrame (`:15`)

**Gravedad:** Critico

**Que es:** `df = df.fillna('No aplica')` aplica string a TODAS las columnas, incluyendo numericas.

**Por que ocurre:** No se separaron columnas numericas de categoricas.

**Como afecta la precision:**
- Si Edad/IMC/Tiempo tienen NaN, se convierten a string
- `StandardScaler.fit_transform` falla con strings -> excepcion en tiempo de ejecucion
- Si no hay NaN actualmente, el bug esta latente y aparece cuando llegue un registro con dato faltante
- Error directo, no hay precision que medir porque el script se rompe

**Solucion:**
```python
num_cols = ['Edad', 'IMC', 'Tiempo de Actividad Fisica']
cat_cols = [c for c in df.columns if c not in num_cols]
df[num_cols] = df[num_cols].fillna(df[num_cols].mean())
df[cat_cols] = df[cat_cols].fillna('No aplica')
```

#### E3 - collect_feedback corrupto (`:220-255`)

**Gravedad:** Critico

**Que es:** Tres problemas encadenados:
1. `new_data` (valores humanos) se concatena a `df` (valores codificados/escalados)
2. `safe_label_transform` recibe enteros + strings mezclados en targets, recodifica los enteros como etiquetas nuevas
3. `scaler.transform` re-escala todo el df incluyendo datos ya escalados

**Por que ocurre:** No hay preprocesamiento del nuevo dato antes de integrarlo al dataset.

**Como afecta la precision:**
- El dataset original se modifica con cada feedback
- El mapeo entero -> nombre de ejercicio se pierde
- Las predicciones post-feedback son esencialmente aleatorias
- Cualquier mejora aparente es ilusoria, los datos de entrenamiento estan corruptos
- Impacto directo: precision post-feedback = 0% o valores sin sentido

**Solucion:** Preprocesar `new_data` antes de concatenar:
```python
new_data = feedback['input_data'].copy()

# 1. Codificar categoricas
for col in ['Genero', 'Nivel de Vision', 'Condicion Fisica', ...]:
    new_data[col] = le_dict[col].transform([new_data[col]])[0]

# 2. Escalar numericas
new_data[['Edad', 'IMC', 'Tiempo']] = scaler.transform(pd.DataFrame([new_data])[['Edad', 'IMC', 'Tiempo']])

# 3. Codificar targets
for col, fase in zip(target_columns, ['Warm-up', 'Main Training', 'Cool-down']):
    val = feedback['corrected_exercises'][fase]
    if val in target_encoders[col].classes_:
        new_data[col] = target_encoders[col].transform([val])[0]
    else:
        # Nueva etiqueta: expandir encoder antes
        target_encoders[col].classes_ = np.append(target_encoders[col].classes_, val)
        new_data[col] = target_encoders[col].transform([val])[0]
        num_classes[col] = len(target_encoders[col].classes_)

# 4. Ahora concatenar (todo esta en el mismo formato)
df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
# No hace falta safe_label_transform ni re-escalar
```

---

### Medios - Afectan calidad y consistencia

#### E4 - Sin stratify en train_test_split (`:269-271`)

**Gravedad:** Medio

**Que es:** `train_test_split` sin `stratify`.

**Por que ocurre:** No se considero el desbalanceo de clases.

**Como afecta la precision:**
- Clases con pocas muestras pueden desaparecer de train o test
- Si desaparecen de train, el modelo nunca las aprende -> precision 0% en esas clases
- Si desaparecen de test, la metrica no refleja la realidad
- Las clases minoritarias (ejercicios raros) quedan invisibles

**Solucion:**
```python
# Crear etiqueta combinada para estratificar
combined = y1.argmax(axis=1) * 100 + y2.argmax(axis=1)

X_train, X_test, y1_train, y1_test, y2_train, y2_test, y3_train, y3_test = train_test_split(
    X, y1, y2, y3, test_size=0.2, random_state=42, stratify=combined
)
```

#### E5 - Nombres de fase en ingles (`:196-201`)

**Gravedad:** Medio

**Que es:** `'Warm-up'`, `'Main Training'`, `'Cool-down'` en las claves del plan.

**Por que ocurre:** Se desarrollo en ingles y no se tradujo.

**Como afecta la precision:**
- No afecta la precision numerica directamente
- Afecta la usabilidad: el TTS pronuncia en ingles, la UI muestra en ingles mientras el resto esta en espanol
- Las claves en ingles se usan en el feedback hardcodeado, creando dependencia de strings en ingles

**Solucion:**
```python
plan = {
    'Calentamiento': target_encoders[...].inverse_transform(...)[0],
    'Entrenamiento': target_encoders[...].inverse_transform(...)[0],
    'Enfriamiento': target_encoders[...].inverse_transform(...)[0]
}
```

---

### Bajos - Cosmetica y eficiencia

#### E6 - `time.sleep(30)` al final (`:321`)

**Gravedad:** Bajo

**Que es:** Mantiene el proceso vivo 30 segundos sin proposito.

**Como afecta la precision:** No afecta.

**Solucion:** Eliminar la linea.

#### E7 - `time.sleep(5)` dentro del loop TTS (`:58`)

**Gravedad:** Bajo

**Que es:** Sleep dentro del loop antes de `engine.runAndWait()`.

**Como afecta la precision:** No afecta la prediccion. Solo alarga innecesariamente la reproduccion de voz.

**Solucion:** Mover `time.sleep(5)` despues de `engine.runAndWait()` o eliminar.

#### E8 - Inverse transform repetido 3 veces (`:290-292`)

**Gravedad:** Bajo

**Que es:** `scaler.inverse_transform` llamado 3 veces con los mismos datos.

**Como afecta la precision:** No afecta. Solo es ineficiente.

**Solucion:**
```python
inversed = scaler.inverse_transform([[Edad, IMC, Tiempo]])[0]
readable_input['Edad'], readable_input['IMC'], readable_input['Tiempo de Actividad Fisica'] = inversed
```

#### E9 - print() vacio (`:207`) y punto y coma (`:6`)

**Gravedad:** Bajo

**Que es:** `print()` sin contenido y `import time;`.

**Como afecta la precision:** No afecta.

**Solucion:** Eliminar ambos.

---

## Impacto acumulado en la precision

| Error | Impacto en precision | Prioridad de fix |
|-------|---------------------|------------------|
| E1 - Separador incorrecto | Alto. Distorsiona las clases totalmente. | 1 |
| E2 - fillna masivo | Critico. Rompe el script si hay NaN. | 2 |
| E3 - collect_feedback corrupto | Alto. Corrompe dataset post-feedback. | 3 |
| E4 - Sin stratify | Medio. Clases minoritarias ignoradas. | 4 |
| E5 - Nombres en ingles | Nulo en precision. | 5 |
| E6-E9 - Bajos | Nulo. | 6-9 |

**Orden recomendado:** E1 -> E2 -> E3 -> E4 -> E5 -> E6-E9

---

*Documento generado el 12/06/2026 - Actualizado con clasificacion de errores y soluciones*
