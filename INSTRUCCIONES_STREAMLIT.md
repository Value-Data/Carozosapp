# 🚀 Instrucciones de Uso - Aplicación Streamlit

## Instalación

### 1. Activar entorno virtual (recomendado)
```bash
# Windows
.\env\Scripts\activate

# Linux/Mac
source env/bin/activate
```

### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 3. Ejecutar la aplicación
```bash
streamlit run app.py
```

La aplicación se abrirá automáticamente en tu navegador en `http://localhost:8501`

---

## Uso de la Aplicación

### Pestaña 1: Carga de Datos 📥

1. **Seleccionar Especie**
   - Elige una especie de la lista desplegable
   - Especies disponibles:
     - Ciruela Negra
     - Ciruela Candy ⚠️ (corregido desde "Canela")
     - Ciruela Roja
     - Durazno Amarillo
     - Durazno Blanco
     - Nectarin Amarillo
     - Nectarin Blanco

2. **Seleccionar Línea de Producto**
   - Después de seleccionar la especie, se cargarán automáticamente las líneas de producto disponibles
   - Selecciona la línea específica que deseas analizar

### Pestaña 2: Configuración ⚙️

1. **Número de Clusters (K)**
   - Define cuántos grupos quieres crear (1-10)
   - Por defecto: 5
   - Cluster 1 = más exigente (menor kilos asignables)
   - Cluster K = menos exigente (mayor kilos asignables)

2. **Percentiles MIN**
   - Para variables tipo MIN (BRIX, Color mínimo)
   - Cluster 1 debe tener el percentil más alto (más exigente)
   - Cluster K debe tener el percentil más bajo (menos exigente)
   - Ejemplo: [0.9, 0.7, 0.5, 0.3, 0.1] para 5 clusters

3. **Percentiles MAX**
   - Para variables tipo MAX (Defectos, Sumatorias)
   - Cluster 1 debe tener el percentil más bajo (menos exigente)
   - Cluster K debe tener el percentil más alto (más exigente)
   - Ejemplo: [0.1, 0.3, 0.5, 0.7, 0.9] para 5 clusters

4. **Procesar Análisis**
   - Haz clic en el botón "🔄 Procesar Análisis"
   - Espera a que se complete el procesamiento (puede tardar unos segundos)

### Pestaña 3: Resultados 📊

1. **Resumen de Clusters**
   - Muestra estadísticas por cluster (número de clientes, kilos totales, promedios)

2. **Tolerancias Sugeridas**
   - Tabla principal con las tolerancias recomendadas por cluster
   - Versión monotónica disponible en expandible

3. **Tolerancias Críticas y Laxas**
   - Comparación entre valores más estrictos y más permisivos
   - Incluye versiones monotónicas

4. **Asignación de Mercados-Clientes**
   - Muestra qué mercado-cliente pertenece a cada cluster

5. **Descarga de Excel**
   - Descarga completa con todas las hojas de cálculo
   - Incluye:
     - ClustersMC
     - Clusters_Summary
     - Tol_Criticos
     - Tol_Laxos
     - Tol_Crit_Mono
     - Tol_Lax_Mono
     - Tol_Sugeridas
     - Tol_Sug_Mono
     - Tol_Crit_Src
     - Tol_Lax_Src
     - AsignacionDetalle
     - ResumenMC
     - ResumenLote

---

## Estructura de Archivos

```
Carozosapp/
├── app.py                      # Aplicación Streamlit principal
├── utils/                      # Módulos refactorizados
│   ├── __init__.py
│   ├── helpers.py             # Funciones auxiliares
│   ├── data_loader.py         # Carga de datos por especie
│   ├── data_processor.py      # Procesamiento de asignación
│   ├── cluster_processor.py   # Procesamiento de clusters
│   └── processor.py           # Función unificada
├── Data/                       # Archivos Excel de datos
├── requirements.txt            # Dependencias
└── INSTRUCCIONES_STREAMLIT.md  # Este archivo
```

---

## Solución de Problemas

### Error: "Archivo no encontrado"
- Verifica que los archivos Excel estén en la carpeta `Data/`
- Verifica que los nombres de archivos coincidan con `ESPECIES_CONFIG` en `utils/data_loader.py`

### Error: "No se encontraron líneas de producto"
- Verifica que el archivo de lotes tenga la columna "LINEA PRODUCTO"
- Verifica que haya datos en el archivo Excel

### Error: "Error al procesar"
- Revisa que todos los archivos requeridos existan:
  - Archivo de lotes de la especie
  - Archivo de tolerancias de la especie
  - `Disminucion.xlsx`
  - `Cruce de Variables.xlsx`
- Verifica que las columnas requeridas existan en los archivos

---

## Notas Importantes

1. **Corrección de Especie**: "Ciruela Canela" ha sido corregida a "Ciruela Candy" como solicitado.

2. **Filtrado**: El sistema ahora filtra automáticamente por ESPECIE y LÍNEA PRODUCTO antes del procesamiento.

3. **Cache**: Streamlit cachea los resultados para mejorar el rendimiento. Si cambias los archivos Excel, es posible que necesites reiniciar la app.

4. **Percentiles**: Los percentiles deben estar entre 0 y 1. Si ingresas valores como 90, 70, etc., el sistema los interpretará como porcentajes y los convertirá automáticamente.

---

## Soporte

Para más información, consulta el archivo `ANALISIS_STREAMLIT.md` que contiene el análisis técnico completo del proyecto.

