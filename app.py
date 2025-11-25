# -*- coding: utf-8 -*-
"""
Aplicación Streamlit para cálculo de tolerancias por clusters
Carozosapp - Sistema de asignación de frutas
"""

import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
from io import BytesIO

from utils.data_loader import get_especies_disponibles, get_lineas_producto
from utils.processor import process_species_linea


# Configuración de página
st.set_page_config(
    page_title="Carozosapp - Tolerancias por Clusters",
    page_icon="🍑",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título principal
st.title("🍑 Carozosapp - Tolerancias por Clusters")
st.markdown("---")

# Session State
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

# Sidebar - Información
with st.sidebar:
    st.header("ℹ️ Información")
    st.markdown("""
    Esta aplicación permite:
    - Seleccionar especie y línea de producto
    - Configurar número de clusters
    - Definir percentiles personalizados
    - Visualizar y descargar tolerancias por cluster
    """)
    
    st.markdown("---")
    st.markdown("**Desarrollado por:** Carozosapp Team")

# Pestañas principales
tab1, tab2, tab3, tab4 = st.tabs(["📥 Carga de Datos", "⚙️ Configuración", "📊 Resultados", "✏️ Edición"])

# TAB 1: Carga de Datos
with tab1:
    st.header("Selección de Especie y Línea de Producto")
    
    col1, col2 = st.columns(2)
    
    with col1:
        especies = get_especies_disponibles()
        especie_seleccionada = st.selectbox(
            "Seleccione la Especie:",
            options=especies,
            index=0 if st.session_state.configuracion['especie'] is None 
                   else especies.index(st.session_state.configuracion['especie']) 
                   if st.session_state.configuracion['especie'] in especies else 0,
            help="Seleccione la especie frutícola a procesar"
        )
        st.session_state.configuracion['especie'] = especie_seleccionada
    
    with col2:
        if especie_seleccionada:
            try:
                lineas = get_lineas_producto(especie_seleccionada)
                if len(lineas) == 0:
                    st.warning("⚠️ No se encontraron líneas de producto para esta especie")
                    linea_seleccionada = None
                else:
                    linea_seleccionada = st.selectbox(
                        "Seleccione la Línea de Producto:",
                        options=lineas,
                        index=0 if st.session_state.configuracion['linea_producto'] is None
                               else lineas.index(st.session_state.configuracion['linea_producto'])
                               if st.session_state.configuracion['linea_producto'] in lineas else 0,
                        help="Seleccione la línea de producto específica"
                    )
                    st.session_state.configuracion['linea_producto'] = linea_seleccionada
            except Exception as e:
                st.error(f"❌ Error al cargar líneas de producto: {str(e)}")
                linea_seleccionada = None
        else:
            linea_seleccionada = None
    
    st.markdown("---")
    
    # Información sobre selección
    if especie_seleccionada and linea_seleccionada:
        st.success(f"✅ Seleccionado: **{especie_seleccionada}** - **{linea_seleccionada}**")
        st.info("💡 Continúe a la pestaña 'Configuración' para ajustar los parámetros del análisis.")

# TAB 2: Configuración
with tab2:
    st.header("Configuración de Clusters y Percentiles")
    
    if not st.session_state.configuracion['especie'] or not st.session_state.configuracion['linea_producto']:
        st.warning("⚠️ Por favor, seleccione primero la Especie y Línea de Producto en la pestaña 'Carga de Datos'.")
    else:
        st.success(f"Procesando: **{st.session_state.configuracion['especie']}** - **{st.session_state.configuracion['linea_producto']}**")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            k = st.number_input(
                "Número de Clusters (K):",
                min_value=1,
                max_value=10,
                value=st.session_state.configuracion['clusters'],
                step=1,
                help="Cantidad de grupos en que se dividirán los mercados-clientes. El sistema ajustará automáticamente si hay valores duplicados."
            )
            st.session_state.configuracion['clusters'] = k
            
            # Advertencia informativa
            st.info("💡 **Nota:** Si hay valores duplicados de kilos asignables, el número real de clusters puede ser menor que K. El sistema ajustará automáticamente.")
        
        with col2:
            st.markdown("**Configuración de Percentiles**")
            st.markdown("*Los percentiles definen los valores de tolerancias sugeridas para cada cluster*")
        
        st.markdown("---")
        
        # Percentiles MIN
        st.subheader("Percentiles MIN (para variables tipo MIN)")
        st.markdown("*Estas variables son más exigentes cuando el valor es menor (ej: BRIX, Color mínimo)*")
        st.markdown("*Cluster 1 = más exigente, Cluster K = menos exigente*")
        
        qmin_values = []
        for i in range(k):
            default_val = st.session_state.configuracion['qmin'][i] if i < len(st.session_state.configuracion['qmin']) else 0.9 - (i * 0.2)
            val = st.slider(
                f"Percentil MIN Cluster {i+1}:",
                min_value=0.0,
                max_value=1.0,
                value=min(max(default_val, 0.0), 1.0),
                step=0.01,
                format="%.2f",
                key=f"qmin_{i}"
            )
            qmin_values.append(val)
        
        st.session_state.configuracion['qmin'] = qmin_values
        
        st.markdown("---")
        
        # Percentiles MAX
        st.subheader("Percentiles MAX (para variables tipo MAX)")
        st.markdown("*Estas variables son más exigentes cuando el valor es mayor (ej: Defectos, Sumatorias)*")
        st.markdown("*Cluster 1 = menos exigente, Cluster K = más exigente*")
        
        qmax_values = []
        for i in range(k):
            default_val = st.session_state.configuracion['qmax'][i] if i < len(st.session_state.configuracion['qmax']) else 0.1 + (i * 0.2)
            val = st.slider(
                f"Percentil MAX Cluster {i+1}:",
                min_value=0.0,
                max_value=1.0,
                value=min(max(default_val, 0.0), 1.0),
                step=0.01,
                format="%.2f",
                key=f"qmax_{i}"
            )
            qmax_values.append(val)
        
        st.session_state.configuracion['qmax'] = qmax_values
        
        st.markdown("---")
        
        # Botón de procesamiento
        if st.button("🔄 Procesar Análisis", type="primary", use_container_width=True):
            with st.spinner("Procesando datos... Esto puede tardar unos segundos."):
                try:
                    resultados = process_species_linea(
                        especie=st.session_state.configuracion['especie'],
                        linea_producto=st.session_state.configuracion['linea_producto'],
                        k=k,
                        qmin=qmin_values,
                        qmax=qmax_values
                    )
                    st.session_state.resultados = resultados
                    st.success("✅ Análisis completado exitosamente!")
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ Error al procesar: {str(e)}")
                    st.exception(e)

# TAB 3: Resultados
with tab3:
    st.header("Resultados del Análisis")
    
    if st.session_state.resultados is None:
        st.info("ℹ️ No hay resultados disponibles. Por favor, realice el análisis en la pestaña 'Configuración'.")
    else:
        resultados = st.session_state.resultados
        clusters = resultados['clusters']
        
        # Resumen de configuración
        with st.expander("📋 Configuración del Análisis", expanded=False):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Especie", resultados['especie'])
            with col2:
                st.metric("Línea Producto", resultados['linea_producto'])
            with col3:
                st.metric("Número de Clusters", len(clusters['clusters_summary']))
        
        st.markdown("---")
        
        # Resumen de Clusters
        st.subheader("📊 Resumen de Clusters")
        st.dataframe(clusters['clusters_summary'], use_container_width=True)
        
        st.markdown("---")
        
        # Tolerancias Sugeridas (principal)
        st.subheader("🎯 Tolerancias Sugeridas (por Cluster)")
        st.markdown("*Valores recomendados basados en percentiles ponderados*")
        st.dataframe(clusters['tol_sugeridas'], use_container_width=True)
        
        # Tolerancias Sugeridas Monotónicas
        with st.expander("📈 Tolerancias Sugeridas Monotónicas", expanded=False):
            st.markdown("*Versión con monotonización aplicada para garantizar consistencia*")
            st.dataframe(clusters['tol_sug_mono'], use_container_width=True)
        
        st.markdown("---")
        
        # Tolerancias Críticas y Laxas
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🔴 Tolerancias Críticas")
            st.markdown("*Valores más estrictos por cluster*")
            st.dataframe(clusters['tol_criticos'], use_container_width=True)
            
            with st.expander("📊 Versión Monotónica", expanded=False):
                st.dataframe(clusters['tol_crit_mono'], use_container_width=True)
        
        with col2:
            st.subheader("🟢 Tolerancias Laxas")
            st.markdown("*Valores más permisivos por cluster*")
            st.dataframe(clusters['tol_laxos'], use_container_width=True)
            
            with st.expander("📊 Versión Monotónica", expanded=False):
                st.dataframe(clusters['tol_lax_mono'], use_container_width=True)
        
        st.markdown("---")
        
        # Asignación de Clusters a Mercado-Cliente
        with st.expander("👥 Asignación de Mercados-Clientes a Clusters", expanded=False):
            st.dataframe(clusters['clusters_mc'], use_container_width=True)
        
        st.markdown("---")
        
        # Descarga de Excel
        st.subheader("💾 Descargar Resultados")
        
        @st.cache_data
        def to_excel_bytes(resultados):
            """Convierte resultados a Excel en memoria."""
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # Clusters
                resultados['clusters']['clusters_mc'].to_excel(writer, sheet_name='ClustersMC', index=False)
                resultados['clusters']['clusters_summary'].to_excel(writer, sheet_name='Clusters_Summary', index=False)
                
                # Tolerancias
                resultados['clusters']['tol_criticos'].to_excel(writer, sheet_name='Tol_Criticos', index=False)
                resultados['clusters']['tol_laxos'].to_excel(writer, sheet_name='Tol_Laxos', index=False)
                resultados['clusters']['tol_crit_mono'].to_excel(writer, sheet_name='Tol_Crit_Mono', index=False)
                resultados['clusters']['tol_lax_mono'].to_excel(writer, sheet_name='Tol_Lax_Mono', index=False)
                resultados['clusters']['tol_crit_src'].to_excel(writer, sheet_name='Tol_Crit_Src', index=False)
                resultados['clusters']['tol_lax_src'].to_excel(writer, sheet_name='Tol_Lax_Src', index=False)
                resultados['clusters']['tol_sugeridas'].to_excel(writer, sheet_name='Tol_Sugeridas', index=False)
                resultados['clusters']['tol_sug_mono'].to_excel(writer, sheet_name='Tol_Sug_Mono', index=False)
                
                # Asignación (opcional)
                resultados['asignacion']['detalle'].to_excel(writer, sheet_name='AsignacionDetalle', index=False)
                resultados['asignacion']['resumen_mc'].to_excel(writer, sheet_name='ResumenMC', index=False)
                resultados['asignacion']['resumen_lote'].to_excel(writer, sheet_name='ResumenLote', index=False)
            
            output.seek(0)
            return output.getvalue()
        
        excel_bytes = to_excel_bytes(resultados)
        filename = f"{resultados['especie'].replace(' ', '_')}_{resultados['linea_producto'].replace(' ', '_')}_Clusters.xlsx"
        
        st.download_button(
            label="📥 Descargar Excel Completo",
            data=excel_bytes,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

# TAB 4: Edición
with tab4:
    st.header("✏️ Edición de Tolerancias y Asignaciones")
    
    if st.session_state.resultados is None:
        st.info("ℹ️ No hay resultados disponibles. Por favor, realice el análisis en la pestaña 'Configuración'.")
    else:
        resultados = st.session_state.resultados
        clusters = resultados['clusters']
        
        # Inicializar session state para ediciones si no existen
        if 'ediciones_tol_sug_mono' not in st.session_state:
            st.session_state.ediciones_tol_sug_mono = clusters['tol_sug_mono'].copy()
        
        if 'ediciones_clusters_mc' not in st.session_state:
            st.session_state.ediciones_clusters_mc = clusters['clusters_mc'].copy()
        
        # Inicializar flags de reset
        if 'reset_tol_flag' not in st.session_state:
            st.session_state.reset_tol_flag = False
        if 'reset_mc_flag' not in st.session_state:
            st.session_state.reset_mc_flag = False
        if 'reset_all_flag' not in st.session_state:
            st.session_state.reset_all_flag = False
        
        # Inicializar contadores de reset (fuerzan nuevo editor con key diferente)
        if 'reset_counter_tol' not in st.session_state:
            st.session_state.reset_counter_tol = 0
        if 'reset_counter_mc' not in st.session_state:
            st.session_state.reset_counter_mc = 0
        if 'reset_counter_all' not in st.session_state:
            st.session_state.reset_counter_all = 0
        
        # Procesar resets ANTES de mostrar los editores
        # Usar contadores para cambiar el key del editor y forzar recreación
        if st.session_state.get('reset_tol_flag', False):
            st.session_state.ediciones_tol_sug_mono = clusters['tol_sug_mono'].copy()
            # Incrementar contador para cambiar el key del editor
            st.session_state.reset_counter_tol += 1
            # Limpiar TODOS los keys relacionados con el editor
            keys_to_delete = [k for k in list(st.session_state.keys()) 
                            if 'editor_tol_sug_mono' in str(k)]
            for key in keys_to_delete:
                del st.session_state[key]
            st.session_state.reset_tol_flag = False
            st.rerun()
        
        if st.session_state.get('reset_mc_flag', False):
            st.session_state.ediciones_clusters_mc = clusters['clusters_mc'].copy()
            # Incrementar contador para cambiar el key del editor
            st.session_state.reset_counter_mc += 1
            # Limpiar TODOS los keys relacionados con el editor
            keys_to_delete = [k for k in list(st.session_state.keys()) 
                            if 'editor_clusters_mc' in str(k)]
            for key in keys_to_delete:
                del st.session_state[key]
            st.session_state.reset_mc_flag = False
            st.rerun()
        
        if st.session_state.get('reset_all_flag', False):
            st.session_state.ediciones_tol_sug_mono = clusters['tol_sug_mono'].copy()
            st.session_state.ediciones_clusters_mc = clusters['clusters_mc'].copy()
            # Incrementar contadores
            st.session_state.reset_counter_tol += 1
            st.session_state.reset_counter_mc += 1
            st.session_state.reset_counter_all += 1
            # Limpiar TODOS los keys relacionados
            keys_to_delete_tol = [k for k in list(st.session_state.keys()) 
                                 if 'editor_tol_sug_mono' in str(k)]
            keys_to_delete_mc = [k for k in list(st.session_state.keys()) 
                                if 'editor_clusters_mc' in str(k)]
            for key in keys_to_delete_tol + keys_to_delete_mc:
                del st.session_state[key]
            st.session_state.reset_all_flag = False
            st.rerun()
        
        # Información contextual
        st.info("💡 **Instrucciones:** Edita las tablas directamente haciendo clic en las celdas. Las columnas de identificación (VARIABLE, MERCADO-CLIENTE) no son editables. Usa el botón 'Resetear' para volver a los valores originales.")
        
        st.markdown("---")
        
        # Tabs internos para separar las dos tablas
        tab_tol, tab_clusters = st.tabs(["📊 Tolerancias Sugeridas Monotónicas", "👥 Asignación de Clusters"])
        
        # TAB INTERNO 1: Tolerancias Sugeridas Monotónicas
        with tab_tol:
            st.subheader("Tolerancias Sugeridas Monotónicas")
            st.markdown("Edita los valores de tolerancias por cluster. La columna **VARIABLE** no es editable.")
            
            # Configurar columnas editables (todas excepto VARIABLE)
            column_config = {}
            col_names = st.session_state.ediciones_tol_sug_mono.columns.tolist()
            for col in col_names:
                if col == "VARIABLE":
                    column_config[col] = st.column_config.TextColumn(
                        col,
                        disabled=True,
                        help="Nombre de la variable (no editable)"
                    )
                else:
                    column_config[col] = st.column_config.NumberColumn(
                        col,
                        format="%.2f",
                        help=f"Valor de tolerancia para {col}"
                    )
            
            # Editor de datos con key dinámico (cambia en cada reset para forzar recreación)
            editor_key_tol = f"editor_tol_sug_mono_{st.session_state.reset_counter_tol}"
            edited_tol = st.data_editor(
                st.session_state.ediciones_tol_sug_mono,
                column_config=column_config,
                use_container_width=True,
                num_rows="fixed",
                key=editor_key_tol
            )
            
            # Actualizar session state con ediciones
            st.session_state.ediciones_tol_sug_mono = edited_tol
            
            # Botón de reset para esta tabla
            col_reset1, col_space1 = st.columns([1, 3])
            with col_reset1:
                if st.button("🔄 Resetear Tolerancias", key="reset_tol"):
                    st.session_state.reset_tol_flag = True
                    st.rerun()
        
        # TAB INTERNO 2: Asignación de Clusters
        with tab_clusters:
            st.subheader("Asignación de Mercados-Clientes a Clusters")
            st.markdown("Edita los valores de **KILOS_ASIGNABLE** y **CLUSTER**. La columna **MERCADO-CLIENTE** no es editable.")
            
            # Configurar columnas editables
            column_config_mc = {}
            col_names_mc = st.session_state.ediciones_clusters_mc.columns.tolist()
            max_cluster = len(clusters['clusters_summary'])
            
            for col in col_names_mc:
                if col == "MERCADO-CLIENTE":
                    column_config_mc[col] = st.column_config.TextColumn(
                        col,
                        disabled=True,
                        help="Nombre del mercado-cliente (no editable)"
                    )
                elif col == "KILOS_ASIGNABLE":
                    column_config_mc[col] = st.column_config.NumberColumn(
                        col,
                        format="%.2f",
                        help="Kilos asignables (editable)"
                    )
                elif col == "CLUSTER":
                    column_config_mc[col] = st.column_config.NumberColumn(
                        col,
                        min_value=1,
                        max_value=max_cluster,
                        step=1,
                        help=f"Cluster asignado (1 a {max_cluster})"
                    )
                else:
                    column_config_mc[col] = st.column_config.NumberColumn(
                        col,
                        format="%.2f",
                        help=f"Columna {col}"
                    )
            
            # Editor de datos con key dinámico (cambia en cada reset para forzar recreación)
            editor_key_mc = f"editor_clusters_mc_{st.session_state.reset_counter_mc}"
            edited_mc = st.data_editor(
                st.session_state.ediciones_clusters_mc,
                column_config=column_config_mc,
                use_container_width=True,
                num_rows="fixed",
                key=editor_key_mc
            )
            
            # Actualizar session state con ediciones
            st.session_state.ediciones_clusters_mc = edited_mc
            
            # Botón de reset para esta tabla
            col_reset2, col_space2 = st.columns([1, 3])
            with col_reset2:
                if st.button("🔄 Resetear Asignaciones", key="reset_mc"):
                    st.session_state.reset_mc_flag = True
                    st.rerun()
        
        st.markdown("---")
        
        # Sección de descarga
        st.subheader("💾 Descargar Tablas Editadas")
        
        # Función para generar Excel con tablas editadas
        def to_excel_bytes_edited():
            """Convierte tablas editadas a Excel en memoria."""
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # Tabla 1: Tolerancias Sugeridas Monotónicas Editadas
                st.session_state.ediciones_tol_sug_mono.to_excel(
                    writer, 
                    sheet_name='Tol_Sug_Mono_Editada', 
                    index=False
                )
                
                # Tabla 2: Asignación de Clusters Editada
                st.session_state.ediciones_clusters_mc.to_excel(
                    writer, 
                    sheet_name='ClustersMC_Editada', 
                    index=False
                )
            
            output.seek(0)
            return output.getvalue()
        
        # Botón de descarga
        excel_bytes_edited = to_excel_bytes_edited()
        filename_edited = f"{resultados['especie'].replace(' ', '_')}_{resultados['linea_producto'].replace(' ', '_')}_Editadas.xlsx"
        
        st.download_button(
            label="📥 Descargar Excel con Tablas Editadas",
            data=excel_bytes_edited,
            file_name=filename_edited,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            help="Descarga un archivo Excel con las dos tablas editadas: Tol_Sug_Mono_Editada y ClustersMC_Editada"
        )
        
        # Botón de reset global (opcional)
        st.markdown("---")
        col_reset_global, col_space_global = st.columns([1, 4])
        with col_reset_global:
            if st.button("🔄 Resetear Todo a Valores Originales", type="secondary", key="reset_all"):
                st.session_state.reset_all_flag = True
                st.rerun()

