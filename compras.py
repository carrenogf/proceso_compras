import streamlit as st
import pandas as pd
import geopandas
import matplotlib.pyplot as plt
from geodatasets import get_path
import requests
import numpy as np
import squarify
import matplotlib.pyplot as plt
pd.options.display.float_format = '{:,.2f}'.format

st.set_page_config(layout="wide")

st.write("""
# Programación en las Ciencias Económicas

## Caso Práctico

### Objetivo:
Procesar una planilla de compras y obtener un informe detallado.

### Pasos a seguir:
1. Importar origen de datos en formato xlsx.
2. Preparar la base para trabajar.
3. Calcular en pesos Neto, IVA y total.
4. Reporte resumen por tipo de comprobante en pesos y dolares.
5. Graficar resumen por tipo de comprobante Neto_pesos e iva_pesos.
6. Reporte resumen 10 proveedores con montos mayores con total y ponderación.
7. Grafico de Cajas por ponderación de proveedores.
8. Obtener información fiscal de cada proveedor.
9. Asignar provincia según el domicilio fiscal de cada proveedor a cada comprobante.
10. Reporte resumen neto_pesos por provincia.
11. Grafico mapa de compras por provincia con latitud y longitud geográfica.
""")



path = st.file_uploader(label="Planilla de compras")
tc = st.number_input(label="Tipo de Cambio")
if path and tc:
  df = pd.read_excel(path,header=None)
  df. columns = df.iloc[1]
  df = df.drop([0,1],axis=0)
  df = df.reset_index()
  df['neto_pesos'] = df["Imp. Neto Gravado"] * df["Tipo Cambio"]
  df['no_gravado_pesos'] = df["Imp. Neto No Gravado"] * df["Tipo Cambio"]
  df['iva_pesos'] = df["IVA"] * df["Tipo Cambio"]
  df = df.fillna(0)
  df = df.round(0)

  st.write(df.style.format(subset=['neto_pesos', 'no_gravado_pesos',"iva_pesos","Imp. Total","IVA","Imp. Neto Gravado","Tipo Cambio"],formatter="{:,.2f}"))
  
  resumen_comp = df.pivot_table(index=["Tipo"],values=["neto_pesos","iva_pesos"],fill_value=0).round(2) # resumen por tipo de comprobante

  resumen_comp.columns = ["iva_pesos","neto_pesos"] 

  resumen_comp_dol = resumen_comp /tc # calcula los valores con el tipo de cambio
  resumen_comp_dol.columns = ["iva_dol","neto_dol"] # renombra las columnas

   # muestra el resumen en dolares

  st.write("## Resumen por comprobante")
  with st.container():
    col1, col2 = st.columns(2)
    with col1:
      st.pyplot(resumen_comp.plot(kind="bar",figsize=(5,5)).figure,use_container_width=True)
    with col2:
        st.write("## Resumen por comprobante pesos")
        st.write(resumen_comp.style.format(subset=['neto_pesos',"iva_pesos"],formatter="{:,.2f}"))
        st.write("## Resumen por comprobante dolares")
        st.write(resumen_comp_dol.style.format(subset=["iva_dol","neto_dol"],formatter="{:,.2f}"))

  st.write("# Resumen por proveedor")
  tabla_proveedores = df.pivot_table(values="neto_pesos",index="Denominación Emisor").sort_values(by="neto_pesos",ascending=False)[:10] #resumen top 10 proveedores con mayor neto
  tabla_proveedores["pond"] = tabla_proveedores["neto_pesos"]/sum(tabla_proveedores['neto_pesos'])*100
  st.write("### Top 10 proveedores con más neto_pesos")
  st.write(tabla_proveedores.style.format(subset=['neto_pesos',"pond"],formatter="{:,.2f}")) # muestra la tabla

  
  plt.figure(figsize=(22,6)) # prepara la figura para el gráfico
  plt.title("Compras por proveedor") # Título del gráfico
  etiquetas = tabla_proveedores.index.str.cat(tabla_proveedores["pond"].round(2).astype(str),sep="\n% ") # Crea las etiquetas compuesta por el nombre y la ponderación
  cuadrados = squarify.plot(sizes=tabla_proveedores["pond"],ec="black",label=etiquetas) # grafica con las etiquetas

  st.pyplot(cuadrados.figure)

  # datos de proveedores

  def get_data(cuit): # función para obtener los datos del proveedor, recibe como parametro un cuit
    url = "https://afip.tangofactura.com/Rest/GetContribuyenteFull" # url de consulta
    q = {'cuit':cuit} # parametro de la url
    headers = {'Cache-Control':'no-Cache'}
    response = requests.request("GET",url,headers=headers,params=q)
    r = response.json()
    result = {
        'idPersona':r['Contribuyente']['idPersona'],
        'nombre':r['Contribuyente']['nombre'],
        'ListaActividades':r['Contribuyente']['ListaActividades'],
        'EsRI':r['Contribuyente']['EsRI'],
        'EsMonotributo':r['Contribuyente']['EsMonotributo'],
        'EsExento':r['Contribuyente']['EsExento'],
        'EsConsumidorFinal':r['Contribuyente']['EsConsumidorFinal'],
        'tipoPersona':r['Contribuyente']['tipoPersona'],
        'estadoClave':r['Contribuyente']['estadoClave'],
        'domicilioFiscal':r['Contribuyente']['domicilioFiscal'],
    }
    return result
  cuits = df["Nro. Doc. Emisor"].unique() # lista de cuits únicos
  datos_proveedores = [get_data(int(cuit)) for cuit in cuits] # aplica la función a cada cuit de la lista
  df_proveedores = pd.DataFrame(datos_proveedores) # convierte en dataframe
  st.write("Información de Proveedores")
  df_proveedores =df_proveedores.drop(["ListaActividades"],axis=1) # muestra la tabla de los proveedores
  df_proveedores
  provincias = [prov["nombreProvincia"] for prov in df_proveedores["domicilioFiscal"]]
  columna_provincias = []
  for index, fila in df.iterrows():

      prov = df_proveedores[df_proveedores['idPersona']==int(fila["Nro. Doc. Emisor"])]["domicilioFiscal"].values[0]["nombreProvincia"]
      columna_provincias.append(prov)

  df["provincia"] = columna_provincias
  df["provincia"] = df["provincia"].replace("CIUDAD AUTONOMA BUENOS AIRES","BUENOS AIRES")
  st.write("# Compras con columna Provincia")
  st.write(df.style.format(subset=['neto_pesos', 'no_gravado_pesos',"iva_pesos","Imp. Total","IVA","Imp. Neto Gravado","Tipo Cambio"],formatter="{:,.2f}"))

  resumen_provincia = df.pivot_table(values="neto_pesos",index=["provincia"],aggfunc=np.sum).reset_index()
  res_prov = resumen_provincia.round(2).copy()
  geojson = "https://infra.datos.gob.ar/catalog/modernizacion/dataset/7/distribution/7.12/download/provincias.geojson"
  d = requests.get(geojson).json()
  provincias = pd.DataFrame([[p["properties"]["iso_nombre"].upper(),p["geometry"]["coordinates"][0],p["geometry"]["coordinates"][1]] for p in d["features"]],columns=["provincia","Longitude","Latitude"])
  letras = {"Á":"A","É":"E","Í":"I","Ó":"O","Ú":"U"}

  for letra in letras:
      provincias["provincia"] = provincias["provincia"].str.replace(letra,letras[letra])

  latitudes = [provincias.loc[provincias["provincia"]==prov,"Latitude"] for prov in resumen_provincia["provincia"]]
  longitudes = [provincias.loc[provincias["provincia"]==prov,"Longitude"] for prov in resumen_provincia["provincia"]]
  resumen_provincia["Latitude"] = latitudes
  resumen_provincia["Longitude"] = longitudes
  gdf = geopandas.GeoDataFrame(resumen_provincia, geometry=geopandas.points_from_xy(resumen_provincia["Longitude"], resumen_provincia["Latitude"]), crs="EPSG:4326")
  world = geopandas.read_file(geopandas.datasets.get_path('naturalearth_lowres'))

  fig, ax = plt.subplots(figsize=(20,10))
  world[world.name == 'Argentina'].plot(ax=ax,
      color='white', edgecolor='blue',label=True)

  texts = [ax.text(row["Longitude"],row["Latitude"]+1,s=row["provincia"].capitalize()+"\n"+str(round(row["neto_pesos"],2)), horizontalalignment='center') for index, row in resumen_provincia.iterrows()]

  mapa = gdf.plot(ax=ax, color="red",label=df.provincia)

  
  st.write("## Compras por Provincia")
  with st.container():
    col1, col2 = st.columns(2)
    with col1:
      st.pyplot(mapa.figure)
    with col2:
        st.write("## Neto_pesos por Provincias")
        st.write(res_prov.sort_values(by="neto_pesos",ascending=False).style.format(subset=["neto_pesos"],formatter="{:,.2f}"))

  st.write("Desarrollado por Francisco Carreño")