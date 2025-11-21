# 🔍 INFORME DE ERROR - Durazno Blanco

## ❌ Error Encontrado

```
ValueError: Bin labels must be one fewer than the number of bin edges
```

## 📊 Análisis del Problema

### Contexto
El error ocurre al procesar **Durazno Blanco** cuando se intenta crear clusters con `K >= 3`.

### Causa Raíz

**Durazno Blanco tiene características especiales:**

1. **Cantidad de datos limitada:**
   - Total de mercados-clientes: **7**
   - Valores únicos de KILOS_ASIGNABLE: **4**
   - Valores repetidos: **4 mercados tienen exactamente el mismo valor** (45,851.24)

2. **Distribución de valores:**
   ```
   Valor          | Frecuencia
   -------------- | ----------
   5,310.83       | 1 vez
   40,660.56      | 1 vez
   45,851.24      | 4 veces (57% de los datos)
   53,139.87      | 1 vez
   ```

3. **Problema técnico:**
   - `pd.qcut()` intenta crear `K` bins basándose en cuantiles
   - Cuando `K > valores_únicos`, `pd.qcut()` puede crear **menos bins** de los solicitados debido a valores duplicados
   - Sin embargo, se le pasan `K` labels (`range(1, K+1)`)
   - **Resultado**: Más labels que bins disponibles → Error

### Cuándo Ocurre

El error se produce cuando:
- `K >= valores_únicos` (en este caso, `K >= 4`)
- Hay valores duplicados en la serie
- `pd.qcut()` crea menos bins de los solicitados por `duplicates="drop"`

### Ejemplo del Flujo

```python
# Durazno Blanco: 7 valores, 4 únicos
K = 5  # Se solicitan 5 clusters

# pd.qcut intenta crear 5 bins
# Pero solo hay 4 valores únicos
# duplicates="drop" elimina bins vacíos
# Resultado: Solo se crean 4 bins

# Pero se le pasan 5 labels: range(1, 6) = [1, 2, 3, 4, 5]
# 4 bins vs 5 labels → ValueError
```

## 🔧 Solución Propuesta

### Opción 1: Ajustar dinámicamente K (Recomendada)
Ajustar automáticamente `K` para que no sea mayor que el número de valores únicos:

```python
def assign_clusters_quantiles(series: pd.Series, k: int):
    s = pd.to_numeric(series, errors="coerce").fillna(0.0)
    if s.nunique() <= 1:
        return pd.Series(np.ones(len(s), dtype=int), index=s.index)
    
    # Ajustar K al número de valores únicos
    k_ajustado = min(k, s.nunique())
    
    try:
        labels = pd.qcut(
            s.rank(method="average", ascending=True),
            q=k_ajustado,
            labels=range(1, k_ajustado+1),
            duplicates="drop"
        ).astype(int)
    except ValueError:
        # Si aún falla, usar bins uniformes
        bins = np.linspace(s.min(), s.max(), num=k_ajustado+1)
        labels = pd.cut(s, bins=bins, labels=range(1, k_ajustado+1), include_lowest=True).astype(int)
    
    # Si se pidieron más clusters de los posibles, rellenar
    if labels.nunique() < k_ajustado:
        bins = np.linspace(s.min(), s.max(), num=k_ajustado+1)
        labels = pd.cut(s, bins=bins, labels=range(1, k_ajustado+1), include_lowest=True).astype(int)
    
    return labels
```

### Opción 2: Usar pd.cut() directamente
Cuando hay valores duplicados, usar división uniforme en lugar de cuantiles:

```python
def assign_clusters_quantiles(series: pd.Series, k: int):
    s = pd.to_numeric(series, errors="coerce").fillna(0.0)
    if s.nunique() <= 1:
        return pd.Series(np.ones(len(s), dtype=int), index=s.index)
    
    k_ajustado = min(k, s.nunique())
    
    # Si hay valores duplicados significativos, usar cut
    if s.nunique() < len(s) * 0.5:  # Más del 50% duplicados
        bins = np.linspace(s.min(), s.max(), num=k_ajustado+1)
        return pd.cut(s, bins=bins, labels=range(1, k_ajustado+1), include_lowest=True).astype(int)
    
    # Caso normal: usar qcut
    try:
        labels = pd.qcut(
            s.rank(method="average", ascending=True),
            q=k_ajustado,
            labels=range(1, k_ajustado+1),
            duplicates="drop"
        ).astype(int)
        
        if labels.nunique() < k_ajustado:
            bins = np.linspace(s.min(), s.max(), num=k_ajustado+1)
            labels = pd.cut(s, bins=bins, labels=range(1, k_ajustado+1), include_lowest=True).astype(int)
        
        return labels
    except ValueError:
        bins = np.linspace(s.min(), s.max(), num=k_ajustado+1)
        return pd.cut(s, bins=bins, labels=range(1, k_ajustado+1), include_lowest=True).astype(int)
```

### Opción 3: Validación en la UI (Preventiva)
Advertir al usuario cuando `K > mercados_clientes`:

```python
# En app.py
if k > len(resumen_mc):
    st.warning(f"⚠️ Advertencia: El número de clusters ({k}) es mayor que el número de mercados-clientes ({len(resumen_mc)}). Se ajustará automáticamente.")
    k = min(k, len(resumen_mc))
```

## 📈 Comparación de Casos

| Especie | Mercados-Clientes | Valores Únicos | K Máximo Viable | Estado |
|---------|-------------------|----------------|-----------------|--------|
| Nectarin Amarillo | 32 | 32 | 32 | ✅ OK |
| Durazno Blanco | 7 | 4 | 4 | ❌ Error con K>=3 |

## ✅ Recomendación Final

**Implementar Opción 1 con Opción 3:**
1. Ajustar automáticamente `K` en la función de clustering
2. Advertir al usuario en la UI si se solicitan más clusters de los posibles
3. Mostrar información sobre cuántos clusters realmente se crearon

Esto garantiza:
- ✅ Compatibilidad con todos los casos (muchos o pocos datos)
- ✅ Experiencia de usuario clara
- ✅ Sin errores inesperados
- ✅ Resultados consistentes

## 🧪 Pruebas Recomendadas

1. ✅ Durazno Blanco (caso con pocos datos)
2. ✅ Nectarin Amarillo (caso normal)
3. ✅ Caso extremo: 3 mercados-clientes, K=5
4. ✅ Caso extremo: Todos los valores iguales

## 📝 Notas Adicionales

- Este problema es común cuando hay **datos desbalanceados** o **muestras pequeñas**
- La solución debe ser **robusta** y manejar todos los casos edge
- Es importante **informar al usuario** cuando se hace un ajuste automático

