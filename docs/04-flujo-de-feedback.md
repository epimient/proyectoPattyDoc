# 🔁 Flujo de feedback y reentrenamiento

## 1. Idea general

Cuando el usuario considera que el plan sugerido **no es el adecuado**, el sistema permite corregir los ejercicios. Esa corrección se usa como **nuevo ejemplo de entrenamiento** para que el modelo aprenda de la preferencia del usuario.

## 2. Contrato de entrada

El endpoint `POST /api/feedback` recibe:

```json
{
  "suitable": false,
  "input_data": { "…perfil del usuario…" },
  "corrected_exercises": {
    "Calentamiento": "Rotaciones articulares suaves",
    "Entrenamiento": "Caminata en el lugar",
    "Enfriamiento": "Respiraciones profundas"
  }
}
```

- Si `suitable: true` → el plan es adecuado → **no se reentrena**. Respuesta inmediata:
  ```json
  { "status": "ok", "retrained": false, "message": "Plan adecuado, no se requiere reentrenamiento" }
  ```
- Si `suitable: false` → se **reentrena** con las correcciones.

## 3. Algoritmo de reentrenamiento (`PlanService.apply_feedback`)

```
1. Si suitable == true → devolver sin reentrenar (guard clause)
2. new_row = input_data (perfil humano)
3. Codificar categóricas:
     para cada columna categórica:
       si valor desconocido → expandir le_dict[col].classes_ y recodificar
4. Escalar numéricas con el mismo StandardScaler
5. Codificar targets (ejercicios corregidos):
     para cada fase (Calentamiento/Entrenamiento/Enfriamiento):
       si el ejercicio no existe en la fase → expandir target_encoder
         y actualizar num_classes[fase] += 1
6. df = concat(dataset_preprocesado, new_row)
7. y1,y2,y3 = to_categorical(targets, num_classes)
8. modelo = build_model(10, [9,9,7])   ← con num_classes actualizadas
9. modelo.fit(X, [y1,y2,y3], epochs=10, batch_size=32)
10. modelo.save(artifacts/modelo5.keras)
11. guardar preprocessors.pkl actualizado (df, encoders, scaler, num_classes)
```

## 4. Efectos visibles

| Efecto | Detalle |
|--------|---------|
| **Expansión de clases** | Si el ejercicio corregido es nuevo, `num_classes` de esa fase crece (p. ej. Fase 2 de 9 → 10) |
| **Catálogo actualizado** | El ejercicio nuevo aparece en `GET /api/exercises` |
| **Modelo persistido** | Se guarda `modelo5.keras` reentrenado |
| **Preprocesadores persistidos** | Se guarda `preprocessors.pkl` con los encoders expandidos |

## 5. Consideraciones

- **No idempotente:** cada feedback `false` modifica el estado de los artefactos.
- **Coste:** el reentrenamiento ejecuta 10 épocas sobre el dataset completo (CPU). Un `POST /api/feedback` tarda unos segundos.
- **Prevención en tests:** la suite de pruebas inyecta un `PlanService` con **artefactos temporales** (`tmp_path`) mediante `app.dependency_overrides`, para que el reentrenamiento **jamás contamine** los artefactos de producción. Ver `tests/conftest.py`.

## 6. Muestra de respuesta tras reentrenar

```json
{
  "status": "ok",
  "retrained": true,
  "message": "Modelo reentrenado y guardado"
}
```

Y `GET /api/health` refleja la expansión:

```json
{
  "num_classes": {
    "Ejercicios Fase 1 de Calentamiento": 9,
    "Ejercicios Fase 2 de Entrenamiento": 10,
    "Ejercicios Fase 3 de Enfriamiento": 7
  }
}
```
