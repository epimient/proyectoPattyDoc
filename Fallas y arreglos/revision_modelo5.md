# Informe de Revisión - `fitness_plan_model5.py`

> **Enfoque exclusivo:** Modelo 5
> **Estado general:** 12/13 problemas **corregidos y verificados** - 1 pendiente (feedback hardcodeado)
> **Verificado contra:** código actual (`fitness_plan_model5.py`, 351 líneas)

---

## RESUMEN EJECUTIVO

| Éxito | Cantidad | Descripción |
|-------|----------|-------------|
| Errores críticos | **6/6 corregidos** | Split, imputación, feedback, inverse, sleeps |
| Errores graves | **3/3 corregidos** | Guardado del modelo, stratify, nombres en español |
| Advertencias | **3/4 resueltas** | output_dims, print vacío, import `;` - *queda W10* |

---

## ERRORES CRITICOS - Todos corregidos

### 1. Separador incorrecto en `split` - ahora `:42`
**¿Cuál era el problema?** Usaba `','` como separador, pero los datos usan `';'` (punto y coma + espacio). Al dividir por `,` no había separación y se tomaba la cadena completa como ejercicio.

**¿Cómo se arregló?** Se cambió `split(',')` -> `split(';')` dentro de `preprocess_data`:
```python
# Línea 42 - ya corregido
df[col] = df[col].apply(lambda x: x.split(';')[0].strip() if isinstance(x, str) else x)
```
**Verificado:** ahora sí separa correctamente `"Marcha en el lugar con cuerda guia; Elevacion de rodillas alternadas"`.

---

### 2. `fillna('No aplica')` masivo - ahora `:20-24`
**¿Cuál era el problema?** Convertía columnas numéricas (`Edad`, `IMC`, `Tiempo`) a string si tenían NaN, rompiendo el `StandardScaler`.

**¿Cómo se arregló?** Imputación separada: **media para numéricas**, `'No aplica'` solo para categóricas:
```python
# Líneas 20-24 - ya corregido
num_cols = ['Edad', 'IMC', 'Tiempo de Actividad Física']
df[num_cols] = df[num_cols].apply(pd.to_numeric, errors='coerce').fillna(df[num_cols].mean())
cat_cols = df.columns.difference(num_cols)
df[cat_cols] = df[cat_cols].fillna('No aplica')
```
**Nota:** la columna quedó renombrada a `'Tiempo de Actividad Física'` (con tilde).

---

### 3. `collect_feedback` corrupto - ahora `:221-260`
**¿Cuál era el problema?** 3 fallos encadenados: se concatenaba un dato sin preprocesar a un df preprocesado, se re-escalaba todo el df con datos ya escalados, y `safe_label_transform` corrompía el mapeo entero -> ejercicio.

**¿Cómo se arregló?** Se reescribió por completo: el `new_row` se **preprocesa ANTES de concatenar**, en el mismo formato que el df:
```python
# Líneas 226-248 - ya corregido
new_row = pd.DataFrame([feedback['input_data'].copy()])
# 1) Categóricas: transform con expansión de classes_ si hay etiqueta nueva
for col in [...]:
    val = str(new_row[col].iloc[0])
    if val not in le_dict[col].classes_:
        le_dict[col].classes_ = np.append(le_dict[col].classes_, val)
    new_row[col] = le_dict[col].transform([val])[0]
# 2) Numéricas escaladas con el mismo scaler
new_row[['Edad', 'IMC', 'Tiempo de Actividad Física']] = scaler.transform(...)
# 3) Targets codificados con target_encoders (también expandibles)
# ...y solo entonces: df = pd.concat([df, new_row], ignore_index=True)
```
**Bonus:** la función problemática `safe_label_transform` fue **eliminada** (resuelve también W12).

---

### 4. `inverse_transform` repetido x3 - ahora `:318`
**¿Cuál era el problema?** Se llamaba 3 veces con el mismo array -> ineficiente.

**¿Cómo se arregló?** Una sola llamada y desempaquetado:
```python
# Línea 318 - ya corregido
inverted = scaler.inverse_transform([[sample_input['Edad'], sample_input['IMC'], sample_input['Tiempo de Actividad Física']]])[0]
readable_input['Edad'] = inverted[0]
readable_input['IMC'] = inverted[1]
readable_input['Tiempo de Actividad Física'] = inverted[2]
```

---

### 5. `time.sleep(30)` al final - **eliminado**
**¿Cuál era el problema?** Mantenía el proceso vivo 30 s sin propósito.

**¿Cómo se arregló?** **Línea eliminada.** El script ahora termina justo después de `model.save(MODEL_PATH)` (`:350-351`).

---

### 6. `time.sleep(5)` en el loop TTS - ahora `:66-74`
**¿Cuál era el problema?** El `sleep` interfería con `engine.say()` (asíncrono) y alargaba la reproducción ~15 s.

**¿Cómo se arregló?** Se eliminó ese sleep y además se corrigió el **bug de Python 3.13** donde `runAndWait()` cortaba tras la 1ra frase, reemplazándolo por un bucle manual:
```python
# Líneas 66-74 - ya corregido
for phase, exercise in plan.items():
    engine.say(f"{phase}: {exercise}")
engine.startLoop(False)          # en vez de runAndWait()
while engine.isBusy():
    engine.iterate()
    time.sleep(0.02)             # microbucle, sin bloquear el TTS
engine.endLoop()
```

---

## ERRORES GRAVES - Todos corregidos

### 7. Modelo no guardado - ahora `:264, 296-299, 350`
**¿Cuál era el problema?** No había `model.save()` ni `load_model()`. Cada ejecución reentrenaba desde cero y el feedback se perdía.

**¿Cómo se arregló?** Guardado y carga automática:
```python
# Línea 264: MODEL_PATH = "modelo5.keras"
# Líneas 296-299 - ya corregido
if os.path.exists(MODEL_PATH):
    from tensorflow.keras.models import load_model
    model = load_model(MODEL_PATH)
# Línea 350 - ya corregido
model.save(MODEL_PATH)
```

---

### 8. `train_test_split` sin `stratify` - ahora `:276-294`
**¿Cuál era el problema?** Sin estratificación, las clases minoritarias podían no aparecer en train/test -> métricas engañosas.

**¿Cómo se arregló?** Estratificación por combinación de fase 1 + fase 2 (como sugiere el readme), con manejo especial de clases únicas (`rare`) que se reincorporan al train:
```python
# Líneas 276-294 - ya corregido
stratify_label = y1.argmax(axis=1) * 10 + y2.argmax(axis=1)
# ...se separan las clases con count==1...
X_train, X_test, ... = train_test_split(X_common, ..., test_size=0.2,
                                        random_state=42, stratify=stratify_label[~rare])
# Reincorporar las clases singulares al train:
X_train = pd.concat([X_train, X_rare])
y1_train = np.concatenate([y1_train, y1_rare])  # y2, y3 igual
```

---

### 9. Nombres de fase en inglés - ahora `:210-217, 241`
**¿Cuál era el problema?** `'Warm-up'`, `'Main Training'`, `'Cool-down'` - el TTS los pronunciaba en inglés.

**¿Cómo se arregló?** Traducidos a español en `generate_fitness_plan` y `collect_feedback`:
```python
# Líneas 210-217 - ya corregido
plan = {
    'Calentamiento':   ...,
    'Entrenamiento':   ...,
    'Enfriamiento':    ...
}
```

---

## ADVERTENCIAS - 3 resueltas, 1 pendiente

### 10. Feedback hardcodeado - `:339-347` - **PENDIENTE**
**¿Cuál es el problema?** `suitable: False` con ejercicios fijos (`'Rotaciones articulares suaves'`...), sin interacción real con el usuario.

**¿Cómo arreglarlo (pendiente)?** Implementar una **ventana de diálogo real** que pregunte al usuario si el plan le sirve y deje elegir/corregir los ejercicios antes de llamar a `collect_feedback`.

---

### 11. `output_dims` duplicado - **resuelto**
**¿Cuál era el problema?** `output_dims` existía como parámetro de `build_model` y como variable local en `collect_feedback`.

**¿Cómo se arregló?** Refactor: ya no existe variable local conflictiva. En `collect_feedback` se pasa **inline** como kwarg:
```python
# Línea 255 - ya corregido
model = build_model(input_dim=len(feature_columns), output_dims=[num_classes[...], ...])
```

---

### 12. `print()` vacío - **resuelto**
**¿Cuál era el problema?** `safe_label_transform` tenía un `print()` sin contenido.

**¿Cómo se arregló?** La función `safe_label_transform` fue **eliminada** (su lógica se integró directamente en `collect_feedback`). El vacío diagnóstico ahora lo cubre `diagnostico_excel` (`:173-193`).

---

### 13. Punto y coma sobrante en `import time` - ahora `:10`
**¿Cuál era el problema?** `import time;`

**¿Cómo se arregló?** Se eliminó el `;` -> `import time`

---

## RESULTADO DEL PLAN DE ACCION

| Estado | Error | Cómo se resolvió | Línea actual |
|--------|-------|------------------|--------------|
| Corregido | C1 - Split separador | `split(';')` | `:42` |
| Corregido | C2 - fillna masivo | Imputación separada numérica/categórica | `:20-24` |
| Corregido | C3 - collect_feedback corrupto | Preprocesar `new_row` antes de concatenar | `:226-248` |
| Corregido | C4 - inverse_transform triplicado | Una sola llamada + desempaquetar | `:318` |
| Corregido | C5 - time.sleep(30) final | Línea eliminada | - |
| Corregido | C6 - time.sleep(5) TTS | Eliminado + bucle `iterate()` p/ Python 3.13 | `:66-74` |
| Corregido | M7 - Modelo no guardado | `save()`/`load_model` con `modelo5.keras` | `:264, 296-299, 350` |
| Corregido | M8 - Split sin stratify | Stratify fase1+fase2 + reintroducir clases únicas | `:276-294` |
| Corregido | M9 - Nombres fase en inglés | Traducidos a español | `:210-217, 241` |
| Pendiente | W10 - Feedback hardcodeado | **Pendiente**: ventana de diálogo real | `:339-347` |
| Corregido | W11 - output_dims duplicado | Inline como kwarg (sin variable local) | `:255` |
| Corregido | W12 - print() vacío | `safe_label_transform` eliminada | - |
| Corregido | W13 - `import time;` | Eliminado el `;` | `:10` |

**Único pendiente:** W10 - el feedback sigue simulado. Todo lo demás correto y verificado en el código actual.

---

*Revisión verificada y actualizada el 11/08/2026 - Enfoque exclusivo en `fitness_plan_model5.py`*