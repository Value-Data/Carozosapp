# 📝 INFORME PRELIMINAR - Pestaña 4: Edición

## 🎯 Objetivo

Agregar una nueva pestaña "Edición" donde el usuario pueda:
1. **Visualizar** dos tablas específicas
2. **Editar** directamente los valores en la interfaz
3. **Descargar** las tablas editadas

## 📊 Tablas a Mostrar

### Tabla 1: Tolerancias Sugeridas Monotónicas
- **Fuente:** `clusters['tol_sug_mono']`
- **Estructura:**
  - Columna: `VARIABLE` (identificador)
  - Columnas: `C1`, `C2`, `C3`, ..., `CK` (valores por cluster)
- **Contenido:** Tolerancias recomendadas con monotonización aplicada
- **Editable:** ✅ Sí, todos los valores numéricos (C1 a CK)

### Tabla 2: Asignación de Mercados-Clientes a Clusters
- **Fuente:** `clusters['clusters_mc']`
- **Estructura:**
  - Columna: `MERCADO-CLIENTE` (identificador)
  - Columna: `KILOS_ASIGNABLE` (valores numéricos)
  - Columna: `CLUSTER` (asignación del cluster 1-K)
- **Contenido:** Qué mercado-cliente pertenece a cada cluster y sus kilos asignables
- **Editable:** ✅ Sí, valores de KILOS_ASIGNABLE y CLUSTER

## 🔧 Funcionalidades Requeridas

### 1. Visualización
- ✅ Mostrar ambas tablas en la pestaña
- ✅ Formato claro y legible (Streamlit `st.data_editor` o similar)
- ✅ Tablas separadas o con tabs/expanders

### 2. Edición Interactiva
- ✅ Edición directa en la interfaz usando `st.data_editor` de Streamlit
- ✅ Validación de tipos de datos:
  - Valores numéricos para tolerancias (decimales permitidos)
  - Valores numéricos para KILOS_ASIGNABLE
  - Valores enteros 1-K para CLUSTER
- ✅ Protección de columnas clave:
  - `VARIABLE` (no editable)
  - `MERCADO-CLIENTE` (no editable)

### 3. Guardado y Descarga
- ✅ Botón "Descargar Excel" con ambas tablas editadas
- ✅ Mantener estructura original de columnas
- ✅ Nombre de archivo descriptivo (ej: `Tolerancias_Editadas_{especie}_{linea}.xlsx`)

## 🎨 Diseño Propuesto

```
Pestaña 4: Edición
├─ Información contextual
│  └─ "Edita las tolerancias y asignaciones de clusters antes de descargar"
│
├─ Tabla 1: Tolerancias Sugeridas Monotónicas
│  └─ st.data_editor con tol_sug_mono
│     - VARIABLE: readonly
│     - C1, C2, ..., CK: editable (numérico)
│
├─ Tabla 2: Asignación de Clusters
│  └─ st.data_editor con clusters_mc
│     - MERCADO-CLIENTE: readonly
│     - KILOS_ASIGNABLE: editable (numérico)
│     - CLUSTER: editable (entero 1-K)
│
└─ Botón de Descarga
   └─ Genera Excel con ambas tablas editadas
```

## ⚠️ Consideraciones Técnicas

### 1. Estado de las Tablas Editadas
- **Pregunta:** ¿Las ediciones deben persistir entre pestañas o solo durante la sesión?
- **Propuesta:** Usar `st.session_state` para mantener las ediciones mientras el usuario navega

### 2. Validación de Datos
- **KILOS_ASIGNABLE:** Debe ser >= 0
- **CLUSTER:** Debe estar entre 1 y K (número de clusters)
- **Tolerancias:** Depende del tipo de variable (MIN/MAX), pero permitir cualquier numérico

### 3. Impacto en Resultados
- **Pregunta:** ¿Las ediciones deben afectar los cálculos en otras pestañas?
- **Propuesta:** Mantener las tablas editadas como versiones separadas, no modificar las originales

### 4. Formato de Descarga
- Excel con 2 hojas:
  - Hoja 1: "Tol_Sug_Mono_Editada"
  - Hoja 2: "ClustersMC_Editada"

## 📋 Preguntas para Confirmar

1. ✅ **¿Las ediciones deben afectar otras pestañas?**
   - Opción A: Solo en esta pestaña (aisladas)
   - Opción B: Actualizar resultados en otras pestañas (más complejo)
   - **Mi recomendación:** Opción A (más simple y seguro)

2. ✅ **¿Debe haber un botón "Resetear" para volver a los valores originales?**
   - Útil si el usuario hace cambios por error

3. ✅ **¿Necesitas validación especial para las tolerancias monotónicas?**
   - Por ejemplo, mantener la monotonía después de editar
   - O simplemente permitir cualquier valor numérico

4. ✅ **¿Las tablas deben estar en tabs separados dentro de la pestaña Edición?**
   - O una debajo de la otra (scroll)

5. ✅ **¿Qué formato de descarga prefieres?**
   - Solo Excel
   - O también CSV/JSON como opciones adicionales

## 🔄 Flujo Propuesto

```
1. Usuario procesa análisis (Pestaña 2)
2. Ve resultados (Pestaña 3)
3. Va a Pestaña 4: Edición
4. Edita valores directamente en las tablas
5. Hace clic en "Descargar Excel Editado"
6. Recibe archivo con tablas modificadas
```

## ✅ Confirmación de Entendimiento

Entiendo que necesitas:

1. ✅ Nueva pestaña "Edición" (Pestaña 4)
2. ✅ Mostrar Tabla 1: Tolerancias Sugeridas Monotónicas (tol_sug_mono)
3. ✅ Mostrar Tabla 2: Asignación Mercados-Clientes a Clusters (clusters_mc)
4. ✅ Edición interactiva de ambas tablas en la app
5. ✅ Descarga de las tablas editadas en Excel

## 🚀 Implementación Propuesta

1. Usar `st.data_editor()` de Streamlit para edición interactiva
2. Guardar ediciones en `st.session_state`
3. Botón de descarga que genere Excel con ambas hojas
4. Validación básica de tipos de datos
5. Indicadores visuales de qué campos son editables

---

**¿Es correcto mi entendimiento?** Por favor confirma o corrige cualquier punto antes de proceder con la implementación.

