# 🔬 ANÁLISIS PROFUNDO - Problema Resetear

## 🔍 Revisión del Flujo de Ejecución

### Problema Reportado
El botón resetear no funciona: permite editar valores pero al hacer clic en resetear no pasa nada.

### Flujo Actual del Código

```python
# 1. Inicialización (líneas 320-325)
if 'ediciones_tol_sug_mono' not in st.session_state:
    st.session_state.ediciones_tol_sug_mono = clusters['tol_sug_mono'].copy()

# 2. Procesamiento de flags (líneas 332-360)
if st.session_state.reset_tol_flag:
    st.session_state.ediciones_tol_sug_mono = clusters['tol_sug_mono'].copy()
    if "editor_tol_sug_mono" in st.session_state:
        del st.session_state["editor_tol_sug_mono"]
    st.session_state.reset_tol_flag = False
    st.rerun()

# 3. Renderizado del editor (líneas 387-394)
edited_tol = st.data_editor(
    st.session_state.ediciones_tol_sug_mono,
    ...
    key="editor_tol_sug_mono"
)

# 4. Actualización del estado (línea 397)
st.session_state.ediciones_tol_sug_mono = edited_tol

# 5. Botón de reset (líneas 400-403)
if st.button("🔄 Resetear Tolerancias", key="reset_tol"):
    st.session_state.reset_tol_flag = True
    st.rerun()
```

## 🐛 Posibles Problemas Identificados

### Problema 1: Orden de Ejecución de st.rerun()

**Teoría:** `st.rerun()` puede no estar ejecutándose inmediatamente si hay otros widgets después.

**Flujo problemático:**
1. Usuario hace clic en botón → `reset_tol_flag = True`
2. `st.rerun()` se llama
3. PERO el código continúa ejecutándose hasta el final del bloque
4. El editor se renderiza ANTES de que el rerun tome efecto
5. El flag se procesa en el siguiente ciclo, pero el editor ya se renderizó

**Evidencia:** En Streamlit, cuando hay múltiples widgets en el mismo bloque, todos se ejecutan antes del rerun.

### Problema 2: st.data_editor Sobrescribe el Estado

**Teoría:** `st.data_editor` puede estar guardando cambios antes de que el reset se procese.

**Flujo problemático:**
1. Usuario edita valores en el editor
2. Hace clic en reset
3. `reset_tol_flag = True` y `st.rerun()`
4. En el rerun, se procesa el flag y se resetea
5. PERO el editor se renderiza y puede estar leyendo de algún caché interno
6. O el editor está guardando los valores editados en un lugar que no estamos limpiando

### Problema 3: Estado Interno de st.data_editor

**Teoría:** `st.data_editor` guarda el estado en `st.session_state[key]` de forma diferente a lo esperado.

**Investigación necesaria:**
- ¿Dónde guarda exactamente el estado el editor?
- ¿Hay otros keys que usa internamente?
- ¿El `del st.session_state["editor_tol_sug_mono"]` es suficiente?

## 🧪 Pruebas a Realizar

### Prueba 1: Verificar qué contiene session_state
Agregar logging para ver qué hay en session_state cuando se presiona reset:

```python
if st.button("🔄 Resetear Tolerancias", key="reset_tol"):
    st.write("DEBUG: Keys antes del reset:", [k for k in st.session_state.keys() if "editor" in k or "ediciones" in k])
    st.session_state.reset_tol_flag = True
    st.rerun()
```

### Prueba 2: Verificar timing del rerun
Usar `st.stop()` para ver si el código se detiene correctamente:

```python
if st.session_state.reset_tol_flag:
    st.session_state.ediciones_tol_sug_mono = clusters['tol_sug_mono'].copy()
    if "editor_tol_sug_mono" in st.session_state:
        del st.session_state["editor_tol_sug_mono"]
    st.session_state.reset_tol_flag = False
    st.success("Reset exitoso")
    st.rerun()
    st.stop()  # No debería llegar aquí si rerun funciona
```

### Prueba 3: Usar on_change callback
En lugar de botón separado, usar el parámetro `on_change` del editor (pero esto no existe en st.data_editor).

## ✅ Soluciones Alternativas

### Solución A: Usar st.experimental_rerun() (deprecated pero puede funcionar diferente)
```python
st.experimental_rerun()  # Versión antigua, puede comportarse diferente
```

### Solución B: No usar key en st.data_editor
Eliminar el `key` del editor para que no mantenga estado interno:

```python
edited_tol = st.data_editor(
    st.session_state.ediciones_tol_sug_mono,
    column_config=column_config,
    use_container_width=True,
    num_rows="fixed",
    # SIN key - esto hace que no guarde estado interno
)
```

**Problema:** Esto puede hacer que el editor no recuerde qué celda está editando.

### Solución C: Usar un contador de reset
Usar un contador que cambie el key del editor cada vez que se resetea:

```python
# Inicializar contador
if 'reset_counter_tol' not in st.session_state:
    st.session_state.reset_counter_tol = 0

# En el reset
if st.button("🔄 Resetear Tolerancias", key="reset_tol"):
    st.session_state.ediciones_tol_sug_mono = clusters['tol_sug_mono'].copy()
    st.session_state.reset_counter_tol += 1
    st.rerun()

# En el editor, usar key dinámico
edited_tol = st.data_editor(
    st.session_state.ediciones_tol_sug_mono,
    key=f"editor_tol_sug_mono_{st.session_state.reset_counter_tol}",
    ...
)
```

**Ventaja:** Cada reset cambia el key, forzando un nuevo editor.

### Solución D: Limpiar TODOS los keys relacionados
El editor puede estar guardando estado en múltiples lugares:

```python
# Limpiar todos los keys posibles del editor
keys_to_delete = [k for k in st.session_state.keys() if k.startswith("editor_tol_sug_mono")]
for key in keys_to_delete:
    del st.session_state[key]
```

### Solución E: Renderizar condicionalmente
Solo renderizar el editor si no hay reset pendiente:

```python
if not st.session_state.reset_tol_flag:
    edited_tol = st.data_editor(...)
else:
    edited_tol = st.session_state.ediciones_tol_sug_mono
```

## 🎯 Solución Recomendada: Combinación de C y D

Combinar el contador de reset con limpieza completa de keys:

```python
# Inicializar contadores
if 'reset_counter_tol' not in st.session_state:
    st.session_state.reset_counter_tol = 0
if 'reset_counter_mc' not in st.session_state:
    st.session_state.reset_counter_mc = 0

# Procesar resets
if st.session_state.get('reset_tol_flag', False):
    st.session_state.ediciones_tol_sug_mono = clusters['tol_sug_mono'].copy()
    # Limpiar TODOS los keys relacionados
    keys_to_delete = [k for k in st.session_state.keys() 
                     if 'editor_tol_sug_mono' in str(k)]
    for key in keys_to_delete:
        del st.session_state[key]
    st.session_state.reset_counter_tol += 1
    st.session_state.reset_tol_flag = False
    st.rerun()

# Editor con key dinámico
edited_tol = st.data_editor(
    st.session_state.ediciones_tol_sug_mono,
    key=f"editor_tol_{st.session_state.reset_counter_tol}",
    ...
)
```

## 🔍 Debugging Adicional

Agregar información de debug para entender qué está pasando:

```python
# Al inicio de la pestaña
with st.expander("🔍 Debug Info (temporal)", expanded=False):
    st.write("reset_tol_flag:", st.session_state.get('reset_tol_flag', False))
    st.write("reset_counter_tol:", st.session_state.get('reset_counter_tol', 0))
    st.write("Keys con 'editor':", [k for k in st.session_state.keys() if 'editor' in k])
    st.write("Keys con 'ediciones':", [k for k in st.session_state.keys() if 'ediciones' in k])
```

## 📝 Conclusión del Análisis

**Problema más probable:** El `st.data_editor` está manteniendo estado interno que no se está limpiando correctamente, o el timing del `st.rerun()` está causando que el editor se renderice antes de que el reset se complete.

**Solución más robusta:** Usar contador de reset + key dinámico + limpieza completa de keys relacionados.

