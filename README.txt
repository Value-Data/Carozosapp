================================================================================
                    INFORME DE ANÁLISIS - CAROZOSAPP
================================================================================

RESUMEN EJECUTIVO
-----------------
Carozosapp es una aplicación Python diseñada para la asignación inteligente de 
lotes de frutas (ciruelas, duraznos, nectarines) a diferentes mercados/clientes 
basándose en criterios de calidad y tolerancias específicas. El sistema evalúa 
lotes de frutas contra tolerancias de calidad, calcula asignaciones optimizadas 
y genera análisis mediante técnicas de clustering para agrupar mercados-clientes 
por nivel de exigencia.

ESTRUCTURA DEL PROYECTO
-----------------------

Archivos Principales:
---------------------
1. ModeloCarozos2.py (287 líneas)
   - Script principal para evaluación de lotes y asignación a mercado-cliente
   - Lee datos de lotes y tolerancias desde archivos Excel
   - Aplica reglas de calidad y genera asignaciones detalladas
   
2. cluster_total.py (339 líneas)
   - Script para clustering de mercados-clientes por nivel de exigencia
   - Calcula tolerancias críticas, laxas y sugeridas por cluster
   - Genera versiones monotónicas de tolerancias para consistencia

3. requirements.txt
   - Lista de dependencias del proyecto (pandas, numpy, openpyxl, etc.)

4. README.md
   - Actualmente contiene solo el título del proyecto

Datos:
------
- Carpeta Data/: Contiene archivos Excel con:
  * Lotes: Lotes_CiruelaNeg.xlsx, Lotes_DuraznoAm.xlsx, Lotes_NectarinAm.xlsx, etc.
  * Tolerancias: Tolerancia_CiruelaCan.xlsx, Tolerancia_DuraznoBl.xlsx, etc.
  * Especies procesadas: Ciruelas (Negra, Canela, Roja), Duraznos (Amarillo, 
    Blanco), Nectarines (Amarillo, Blanco)

Archivos de Configuración:
--------------------------
- Cruce de Variables.xlsx: Mapea variables de tolerancias a defectos específicos
- Disminucion.xlsx: Define porcentajes de disminución aplicables a variables 500/600
- env/: Entorno virtual Python

FUNCIONALIDAD DETALLADA
-----------------------

1. MODELOCAROZOS2.PY - Asignación de Lotes
===========================================

Propósito:
----------
Evaluar cada lote de frutas contra las tolerancias de cada mercado-cliente y 
determinar los kilos asignables para cada combinación.

Flujo de Trabajo:
-----------------
1. Carga de Datos:
   - Lotes desde Excel (ej: NectarinAm.xlsx)
   - Tolerancias por mercado-cliente (Tolerancia_NectarinAm.xlsx)
   - Archivo de disminuciones (Disminucion.xlsx)
   - Archivo de cruce de variables (Cruce de Variables.xlsx)

2. Preprocesamiento:
   - Normalización de rangos de calibre (invierte si están invertidos)
   - Aplicación de disminuciones a variables 500/600: valor * (1 - %disminucion)

3. Evaluación de Calidad:
   - BRIX: Verifica que el valor cumpla con el mínimo requerido
   - Firmeza: Evalúa que esté dentro del rango (inferior y superior)
   - Color: Calcula porcentaje mínimo de cubrimiento de color
   - Defectos individuales (500/600): Verifica máximos permitidos
   - Sumatorias: Valida sumatorias de condición y calidad
   - Calibres: Calcula % dentro del rango (no bloquea asignación)

4. Cálculo de Kilos Asignables:
   asignable = kilos * (pct_cal_in/100.0) if ok_base else 0.0

5. Generación de Salidas (Excel):
   - AsignacionDetalle: Evaluación detallada por lote y mercado-cliente
   - ResumenMC: Resumen por mercado-cliente (kilos asignables totales)
   - ResumenLote: Resumen por lote (mejores mercados y total asignable)
   - Check_{LOTE}: Verificación de disminuciones aplicadas (opcional)

Variables Evaluadas:
--------------------
- BRIX (PROMSOLSOL): Sólidos solubles - valor mínimo requerido
- Firmeza (PROMFIRMEZA): Rango entre límite inferior y superior
- Color: Porcentaje mínimo de cubrimiento de color
- Defectos 500/600: Variables individuales mapeadas desde "Cruce de Variables"
- Sumatorias: CONDICION y CALIDAD (máximos permitidos)
- Calibres 100.x: Distribución porcentual de calibres (no bloquea)


2. CLUSTER_TOTAL.PY - Clustering y Tolerancias Sugeridas
=========================================================

Propósito:
----------
Agrupar mercados-clientes en clusters según su nivel de exigencia (basado en 
kilos asignables) y calcular tolerancias sugeridas para cada cluster.

Flujo de Trabajo:
-----------------
1. Carga de Datos:
   - ResumenMC (generado por ModeloCarozos2.py)
   - Tolerancias originales
   - Archivo de cruce de variables

2. Clustering:
   - Agrupa mercado-cliente por KILOS_ASIGNABLE usando cuantiles
   - Genera K clusters (default: 5)
   - Asigna ranks por exigencia (menor kilos = más exigente)

3. Cálculo de Tolerancias por Cluster:
   - Críticas: Valores más estrictos (MIN o MAX según variable)
   - Laxas: Valores más permisivos (MIN o MAX según variable)
   - Sugeridas: Cuantiles ponderados por kilos asignables

4. Monotonización:
   - Garantiza que tolerancias sean monotónicas entre clusters
   - MIN: no-creciente (cluster 1 >= cluster 2 >= ...)
   - MAX: no-decreciente (cluster 1 <= cluster 2 <= ...)

5. Generación de Salidas (Excel):
   - ClustersMC: Asignación de mercado-cliente a clusters
   - Clusters_Summary: Estadísticas por cluster
   - Tol_Criticos, Tol_Laxos: Tolerancias extremas
   - Tol_Crit_Mono, Tol_Lax_Mono: Versiones monotónicas
   - Tol_Sugeridas: Cuantiles ponderados (configurables)
   - Tol_Sug_Mono: Versión monotónica de sugeridas
   - Tol_Crit_Src, Tol_Lax_Src: Origen de cada tolerancia

Parámetros CLI:
---------------
--in-res     : Archivo con ResumenMC (default: Asignacion_NectarinAm_por_MercadoCliente.xlsx)
--in-tol     : Archivo de tolerancias (default: Tolerancia_NectarinAm.xlsx)
--in-cruce   : Archivo de cruce (default: Cruce de Variables.xlsx)
--out        : Archivo de salida (default: Asignacion_NectarinAm_Cluster_Total.xlsx)
--clusters   : Número de clusters K (default: 5)
--qmin       : Cuantiles MIN (ej: "0.9,0.7,0.5,0.3,0.1" o "90,70,50,30,10")
--qmax       : Cuantiles MAX (ej: "0.1,0.3,0.5,0.7,0.9" o "10,30,50,70,90")

Ejemplo de uso:
---------------
python cluster_total.py --clusters 5 --qmin "0.9,0.7,0.5,0.3,0.1" --qmax "0.1,0.3,0.5,0.7,0.9"


VARIABLES PROCESADAS
--------------------
- BRIX: Sólidos solubles (MIN - menor es más exigente)
- Firmeza: Inferior y superior (rangos)
- Color: Porcentaje mínimo de cubrimiento (MIN - menor es más exigente)
- Sumatorias: Condición y Calidad (MAX - mayor es más exigente)
- Defectos 500/600: Variables individuales mapeadas desde "Cruce de Variables"
- Calibres 100.x: Distribución porcentual de calibres

TECNOLOGÍAS UTILIZADAS
----------------------
- Python 3.x
- pandas: Manipulación de datos y DataFrames
- numpy: Cálculos numéricos y estadísticos
- openpyxl/xlsxwriter: Lectura y escritura de archivos Excel
- jenkspy: Clustering (declarado en requirements pero no usado actualmente)

FLUJO DE TRABAJO TÍPICO
-----------------------
1. Ejecutar ModeloCarozos2.py
   ↓
   Genera: Asignacion_NectarinAm_por_MercadoCliente.xlsx
   ↓
2. Ejecutar cluster_total.py (lee ResumenMC del paso 1)
   ↓
   Genera: Asignacion_NectarinAm_Cluster_Total.xlsx

FORTALEZAS DEL PROYECTO
-----------------------
1. Manejo robusto de datos: Normalización automática de columnas, manejo de 
   rangos invertidos, valores faltantes
2. Configurabilidad: Parámetros CLI en cluster_total.py (K, cuantiles)
3. Trazabilidad: Identifica la fuente de cada tolerancia crítica/laxa
4. Normalización inteligente: Funciones para normalizar nombres de columnas 
   (maneja caracteres especiales, acentos, mayúsculas)
5. Monotonización: Garantiza consistencia en tolerancias entre clusters
6. Cuantiles ponderados: Considera el peso (kilos asignables) al calcular 
   tolerancias sugeridas

ÁREAS DE MEJORA IDENTIFICADAS
------------------------------
1. Documentación incompleta: El README.md solo contiene el título
2. Código hardcodeado: Nombres de archivos y especies están hardcodeados en 
   ModeloCarozos2.py
3. Falta de modularización: Funciones podrían estar en módulos separados para 
   reutilización
4. Dependencia no usada: jenkspy está en requirements pero no se utiliza
5. Sin tests: No hay pruebas unitarias o de integración
6. Manejo de errores limitado: Algunos casos de error no están cubiertos
7. Validación de entrada: No valida que archivos de entrada existan o tengan 
   formato correcto

CONCLUSIÓN
----------
Carozosapp es un sistema funcional y completo para asignación y optimización 
de tolerancias de calidad en el sector frutícola. El código es robusto y 
maneja casos complejos como rangos invertidos, normalización de datos y 
cálculos estadísticos avanzados. 

Recomendaciones:
- Completar la documentación del README
- Modularizar el código para facilitar mantenimiento
- Agregar validación de entrada y manejo de errores
- Implementar tests para garantizar calidad
- Generalizar para soportar múltiples especies automáticamente

================================================================================
                              FIN DEL INFORME
================================================================================


