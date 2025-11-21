# 📊 ANÁLISIS Y RECOMENDACIONES - APLICACIÓN STREAMLIT
## Sistema de Tolerancias por Clusters para Carozosapp

---

## 🎯 OBJETIVO DE LA APLICACIÓN

Crear una interfaz Streamlit que permita:
1. **Seleccionar ESPECIE y LÍNEA PRODUCTO** del usuario
2. **Cargar datos** correspondientes a la combinación seleccionada
3. **Parametrizar** cantidad de clusters (K) y percentiles (qmin/qmax)
4. **Visualizar y descargar** tolerancias agrupadas por clusters

---

## 🔍 ANÁLISIS DEL CÓDIGO ACTUAL

### Flujo Actual Identificado

```
1. ModeloCarozos2.py
   └─> Carga: Lotes_{Especie}.xlsx + Tolerancia_{Especie}.xlsx
   └─> Join por: ["ESPECIE", "LINEA PRODUCTO"]
   └─> Genera: ResumenMC (agrupado por MERCADO-CLIENTE)
   
2. cluster_total.py
   └─> Lee: ResumenMC del paso anterior
   └─> Clustering por: KILOS_ASIGNABLE
   └─> Genera: Tolerancias por cluster (Críticas, Laxas, Sugeridas)
```

### Mapeo de Archivos Detectado

**Especies disponibles:**
- Ciruela: Negra, Canela, Roja
- Durazno: Amarillo, Blanco
- Nectarin: Amarillo, Blanco

**Archivos por especie:**
- `Data/Lotes_{Especie}.xlsx` → Datos de lotes
- `Data/Tolerancia_{Especie}.xlsx` → Tolerancias por mercado-cliente

**Archivos compartidos:**
- `Disminucion.xlsx` → Porcentajes de disminución (500/600)
- `Cruce de Variables.xlsx` → Mapeo variables tolerancias → defectos

---

## ⚠️ PROBLEMAS IDENTIFICADOS EN EL CÓDIGO ACTUAL

### 1. **Código Hardcodeado**
```python
# ModeloCarozos2.py línea 18-19
F_NECT = BASE_DIR / "NectarinAm.xlsx"
F_TOL  = BASE_DIR / "Tolerancia_NectarinAm.xlsx"
```
- ❌ Solo funciona para Nectarin Amarillo
- ❌ No es genérico para otras especies

### 2. **No Filtra por LINEA PRODUCTO**
- ⚠️ El código actual carga todos los datos sin filtrar
- ⚠️ El join en línea 150 hace merge por ESPECIE y LINEA PRODUCTO, pero no filtra previamente
- ✅ Esto es correcto, pero necesita verificación

### 3. **Dependencia Entre Scripts**
- ⚠️ `cluster_total.py` requiere el output de `ModeloCarozos2.py`
- ⚠️ Necesita archivo intermedio (ResumenMC)
- ✅ Puede optimizarse para hacer todo en memoria

### 4. **Parámetros CLI no amigables**
- ⚠️ Percentiles se pasan como strings: `"0.9,0.7,0.5,0.3,0.1"`
- ✅ En Streamlit será más intuitivo con inputs numéricos

---

## 💡 RECOMENDACIONES DE ARQUITECTURA

### Arquitectura Propuesta para Streamlit

```
┌─────────────────────────────────────────────────┐
│         STREAMLIT APP (app.py)                  │
├─────────────────────────────────────────────────┤
│                                                 │
│  Tab 1: Carga y Selección                      │
│  └─> Select: ESPECIE                           │
│  └─> Select: LÍNEA PRODUCTO                    │
│  └─> Upload: Lotes Excel (opcional)            │
│  └─> Upload: Tolerancias Excel (opcional)      │
│                                                 │
│  Tab 2: Configuración                          │
│  └─> Slider: Cantidad de Clusters (K)          │
│  └─> Multi-Input: Percentiles MIN              │
│  └─> Multi-Input: Percentiles MAX              │
│                                                 │
│  Tab 3: Resultados                             │
│  └─> Tabla: Resumen por Cluster                │
│  └─> Tabla: Tolerancias Críticas               │
│  └─> Tabla: Tolerancias Laxas                  │
│  └─> Tabla: Tolerancias Sugeridas              │
│  └─> Download: Excel completo                  │
│                                                 │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│         MÓDULOS REFACTORIZADOS                  │
├─────────────────────────────────────────────────┤
│                                                 │
│  utils/                                         │
│  ├─> data_loader.py     → Carga y filtrado     │
│  ├─> processor.py       → Lógica ModeloCarozos2│
│  ├─> clustering.py      → Lógica cluster_total │
│  └─> helpers.py         → Funciones comunes    │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## 🏗️ RECOMENDACIONES TÉCNICAS

### 1. **Refactorización de Código**

#### ✅ Crear módulos reutilizables:
```
utils/
├── __init__.py
├── data_loader.py       # Carga de archivos Excel
├── data_processor.py    # Procesamiento de lotes y asignación
├── cluster_processor.py # Clustering y cálculo de tolerancias
└── helpers.py           # Funciones de normalización comunes
```

#### ✅ Función principal refactorizada:
```python
def process_species_linea(
    especie: str,
    linea_producto: str,
    num_clusters: int,
    qmin: list,
    qmax: list
) -> dict:
    """
    Procesa una combinación ESPECIE + LÍNEA PRODUCTO
    y devuelve todos los resultados en memoria.
    """
    # 1. Cargar datos
    # 2. Filtrar por ESPECIE y LINEA PRODUCTO
    # 3. Procesar asignaciones
    # 4. Calcular clusters
    # 5. Calcular tolerancias
    # 6. Retornar resultados
```

### 2. **Manejo de Archivos Dinámico**

#### ✅ Mapeo automático de archivos:
```python
ESPECIES_CONFIG = {
    "Ciruela Negra": {
        "lotes": "Data/Lotes_CiruelaNeg.xlsx",
        "tolerancias": "Data/Tolerancia_CiruelaNeg.xlsx"
    },
    "Nectarin Amarillo": {
        "lotes": "Data/Lotes_NectarinAm.xlsx",
        "tolerancias": "Data/Tolerancia_NectarinAm.xlsx"
    },
    # ... más especies
}
```

#### ✅ Detección automática de LÍNEA PRODUCTO:
```python
def get_lineas_producto(especie: str) -> list:
    """Lee los archivos y extrae las líneas de producto disponibles."""
    df_lotes = pd.read_excel(ESPECIES_CONFIG[especie]["lotes"])
    return df_lotes["LINEA PRODUCTO"].unique().tolist()
```

### 3. **Validación de Datos**

#### ✅ Validaciones necesarias:
- Verificar que ESPECIE existe en archivos
- Verificar que LÍNEA PRODUCTO existe para esa ESPECIE
- Validar formato de archivos Excel
- Validar columnas requeridas presentes
- Validar que hay datos después del filtro

### 4. **Interfaz Streamlit**

#### ✅ Estructura de pestañas:
```python
tab1, tab2, tab3 = st.tabs(["📥 Carga de Datos", "⚙️ Configuración", "📊 Resultados"])

with tab1:
    # Selección de especie y línea producto
    # Carga de archivos opcionales
    
with tab2:
    # Parámetros de clustering
    # Configuración de percentiles
    
with tab3:
    # Visualización de resultados
    # Descarga de Excel
```

#### ✅ Componentes UI recomendados:
- `st.selectbox` para ESPECIE
- `st.selectbox` para LÍNEA PRODUCTO (dependiente de ESPECIE)
- `st.number_input` para cantidad de clusters (1-10)
- `st.number_input` múltiples para percentiles (con validación)
- `st.dataframe` para visualizar tablas
- `st.download_button` para descargar Excel

### 5. **Optimización de Performance**

#### ✅ Cache con Streamlit:
```python
@st.cache_data
def load_data(especie: str):
    """Cache de carga de datos para evitar recargas innecesarias."""
    return pd.read_excel(ESPECIES_CONFIG[especie]["lotes"])

@st.cache_data
def process_clusters(data, k, qmin, qmax):
    """Cache de procesamiento si parámetros no cambian."""
    # ... procesamiento
```

### 6. **Manejo de Estados**

#### ✅ Session State:
```python
if 'resultados' not in st.session_state:
    st.session_state.resultados = None

if 'configuracion' not in st.session_state:
    st.session_state.configuracion = {
        'especie': None,
        'linea_producto': None,
        'clusters': 5,
        'qmin': [0.9, 0.7, 0.5, 0.3, 0.1],
        'qmax': [0.1, 0.3, 0.5, 0.7, 0.9]
    }
```

---

## 📋 CHECKLIST DE IMPLEMENTACIÓN

### Fase 1: Refactorización Base
- [ ] Crear estructura de módulos (`utils/`)
- [ ] Extraer funciones comunes a `helpers.py`
- [ ] Refactorizar `ModeloCarozos2.py` → `data_processor.py`
- [ ] Refactorizar `cluster_total.py` → `cluster_processor.py`
- [ ] Crear función unificada `process_species_linea()`

### Fase 2: Carga de Datos
- [ ] Crear `data_loader.py` con mapeo de especies
- [ ] Implementar detección automática de LÍNEA PRODUCTO
- [ ] Implementar filtrado por ESPECIE y LÍNEA PRODUCTO
- [ ] Agregar validaciones de datos

### Fase 3: Streamlit App
- [ ] Crear `app.py` con estructura de pestañas
- [ ] Implementar Tab 1: Selección y carga
- [ ] Implementar Tab 2: Configuración
- [ ] Implementar Tab 3: Visualización de resultados
- [ ] Agregar descarga de Excel

### Fase 4: Mejoras
- [ ] Agregar cache con `@st.cache_data`
- [ ] Agregar manejo de errores y mensajes
- [ ] Agregar indicadores de progreso (`st.progress`)
- [ ] Agregar gráficos visuales (opcional)

---

## ⚠️ PUNTOS CRÍTICOS A CONSIDERAR

### 1. **Filtrado por LINEA PRODUCTO**
- ✅ **IMPORTANTE**: El join actual en línea 150 ya filtra por ESPECIE y LINEA PRODUCTO
- ⚠️ Pero si un archivo tiene múltiples líneas, todas se procesan
- ✅ **Recomendación**: Filtrar PRIMERO por LÍNEA PRODUCTO antes del join

### 2. **Archivos de Disminución y Cruce**
- ⚠️ Estos archivos son compartidos entre todas las especies
- ✅ Pueden cargarse una sola vez al inicio de la app

### 3. **Nombres de Columnas**
- ⚠️ Hay normalización de nombres (caracteres especiales, mayúsculas)
- ✅ La función `canon()` ya existe para esto
- ✅ Reutilizar en la app

### 4. **Performance con Archivos Grandes**
- ⚠️ Si los archivos Excel son muy grandes, considerar:
  - Cache de datos cargados
  - Procesamiento en chunks
  - Indicadores de progreso

### 5. **Validación de Percentiles**
- ⚠️ Los percentiles deben:
  - Estar entre 0 y 1 (o 0 y 100)
  - Tener longitud igual a K (o ser interpolados)
  - Para MIN: ser decrecientes
  - Para MAX: ser crecientes

---

## 🎨 MEJORAS OPCIONALES (Futuro)

1. **Visualizaciones**:
   - Gráficos de distribución de kilos por cluster
   - Heatmap de tolerancias por cluster
   - Comparación visual de tolerancias críticas vs laxas

2. **Exportación Avanzada**:
   - Exportar a PDF
   - Exportar a CSV individual por cluster
   - Template personalizado de Excel

3. **Historial**:
   - Guardar configuraciones frecuentes
   - Comparar diferentes análisis

4. **Validación Avanzada**:
   - Previsualización de datos antes de procesar
   - Advertencias sobre datos faltantes
   - Sugerencias de parámetros óptimos

---

## 📝 RESUMEN DE RECOMENDACIONES PRIORITARIAS

### 🔴 ALTA PRIORIDAD (Antes de implementar)
1. **Refactorizar código** en módulos reutilizables
2. **Crear función unificada** que procese ESPECIE + LÍNEA PRODUCTO
3. **Implementar filtrado** explícito por LÍNEA PRODUCTO
4. **Mapeo dinámico** de archivos por especie

### 🟡 MEDIA PRIORIDAD (Durante implementación)
1. Validación de datos y manejo de errores
2. Cache de datos con Streamlit
3. UI intuitiva con pestañas
4. Descarga de resultados en Excel

### 🟢 BAJA PRIORIDAD (Mejoras futuras)
1. Visualizaciones gráficas
2. Historial de configuraciones
3. Exportación a otros formatos

---

## ✅ CONCLUSIÓN

**El proyecto es viable y bien estructurado**, pero necesita:
1. Refactorización para hacer el código genérico
2. Integración de ambos scripts en una función unificada
3. Interfaz Streamlit que simplifique la configuración

**El mayor desafío** será hacer que el código funcione para cualquier combinación de ESPECIE + LÍNEA PRODUCTO sin hardcodear nombres de archivos.

**Recomendación final**: Refactorizar primero, luego crear la app Streamlit. Esto facilitará el mantenimiento y la extensibilidad.


