# Métricas de Logística

Proyecto para transformar el export crudo de envíos (descargado del sistema
de gestión) en reportes de métricas: cantidad de envíos, entregas efectivas,
entregas antes de las 21hs, cancelados, y efectividad por chofer y por zona.

## Estructura

```
logistica-metricas/
├── README.md                  → este archivo
├── reglas_de_negocio.md       → definiciones oficiales de cada métrica (fuente de verdad)
├── diccionario_de_datos.md    → qué significa cada columna del archivo crudo
├── datos_crudos/              → los .xls que vas descargando del sistema (uno por corte/fecha)
├── reportes/                  → los .xlsx generados por el script (detalle/auditoría)
├── dashboard/
│   └── dashboard_logistica.html   → dashboard interactivo (ver sección abajo)
└── scripts/
    └── generar_reporte.py     → script que arma el reporte en Excel
```

## Cómo usarlo

1. Descargá el export del sistema de logística y guardalo en `datos_crudos/`
   (el nombre que trae por defecto ya incluye fecha y hora, así que no hace
   falta renombrarlo).
2. Corré el script:

   ```bash
   cd scripts
   python3 generar_reporte.py ../datos_crudos/NOMBRE_DEL_ARCHIVO.xls
   ```

3. El reporte queda guardado en `reportes/reporte_<fecha_de_hoy>.xlsx`, con
   4 hojas:
   - **Resumen** — KPIs generales (total de envíos, % entregas efectivas, %
     antes de las 21hs, % cancelados).
   - **Por Chofer** — ranking de choferes por % de efectividad, con las
       entregas antes de corte y cancelaciones de cada uno. Los choferes con
       menos de 5 envíos en el período quedan marcados (`muestra_chica`) para
       no sacar conclusiones apuradas sobre poca data.
   - **Por Zona** — mismo desglose pero por zona geográfica.
   - **Detalle** — todas las filas originales con las columnas calculadas
     (`es_entrega_efectiva`, `es_antes_de_corte`, `es_cancelado`) para poder
     auditar o cruzar cualquier número contra el dato crudo.

   Si querés elegir vos el nombre/ubicación del archivo de salida:

   ```bash
   python3 generar_reporte.py ../datos_crudos/archivo.xls --salida ../reportes/reporte_semana_36.xlsx
   ```

### Requisitos

- Python 3 con `pandas`, `openpyxl` y (para leer `.xls` viejos) `xlrd`.
- LibreOffice instalado (el script lo usa automáticamente como respaldo si
  el `.xls` viene con el archivo interno corrupto — un problema que ya
  apareció con este sistema de origen y que el script maneja solo).

## Dashboard interactivo (`dashboard/dashboard_logistica.html`)

Esto es lo que gerencia y el equipo van a mirar día a día — no hace falta
correr nada ni saber Python. Es un único archivo HTML que se abre en
cualquier navegador.

**Qué hace:**
- Arrastrás o seleccionás el `.xls` tal cual lo baja LightData y lo procesa
  ahí mismo, en el navegador (no hace falta convertirlo ni tocar nada antes).
- Agrupa los envíos por día automáticamente (usa la columna `Fecha
  MercadoPacks`), así que si subís un archivo que trae varios días juntos,
  igual separa las métricas por fecha correctamente.
- Muestra tarjetas de KPIs (total de envíos, % entregas efectivas, franja
  horaria de entrega, % cancelados), un gráfico de evolución o de entregas
  por hora según el período elegido, el cruce de entregas por franja
  horaria (antes de 21 / 21-22 / 22-23 / después de 23, con semáforo
  verde-amarillo-rojo, desglosado por **todos** los valores de `Estado` del
  archivo — no solo entregados), el desglose por zona (con la cantidad de
  cada segmento de la barra, no solo el total), y el ranking de choferes
  (con Pendientes, la cantidad de entregas en cada una de las 4 franjas
  horarias, buscador y orden por columna).
- Tiene selector de período: Hoy, Ayer, Últimos 7 días, Últimos 30 días, o
  un rango de fechas a elección. Al cargar un archivo, el panel salta solo
  al rango de fechas que trae ese archivo.
- **Es interactivo:** hacer click en una zona, en una franja horaria del
  cruce, o en un chofer del ranking filtra el resto del panel a esa
  selección (con un aviso claro de qué filtro está activo y un botón para
  limpiarlo). Los detalles exactos de qué se puede cruzar con qué están en
  `reglas_de_negocio.md`, sección 9.

**Cómo se comparte con el equipo:** los datos que se cargan quedan guardados
de forma compartida — **cualquier persona que abra este mismo archivo HTML
ve los mismos datos**, no hace falta que cada uno suba el archivo por su
cuenta. Para que gerencia y el equipo lo vean, alcanza con que una persona
lo suba al lugar donde lo van a abrir todos (ver "Cómo publicarlo" abajo) y
que alguien cargue el export del día ahí una vez.

**Qué NO hace (para que no haya sorpresas):**
- No se conecta solo al sistema de LightData — alguien tiene que descargar
  el `.xls` y arrastrarlo al dashboard. Si querés que eso también sea
  automático, hace falta que el sistema de logística tenga una forma de
  exportar por API o por URL fija (ver backlog más abajo).
- No es "tiempo real" en el sentido de que empuje cambios al instante:
  cuando alguien carga un archivo nuevo, el panel se refresca solo cada
  ~45 segundos para el resto de las personas que lo tengan abierto (o
  pueden tocar "Actualizar" para forzarlo ya mismo). Para una métrica diaria
  esto es más que suficiente.
- Las definiciones de negocio están duplicadas a propósito en este archivo
  y en `scripts/generar_reporte.py` (JavaScript y Python no comparten
  código). Si cambiás una regla, hay que actualizarla en `reglas_de_negocio.md`
  y después replicarla en los dos lugares — está comentado en el código de
  ambos para que sea fácil de encontrar.

**Cómo publicarlo para que lo vea todo el equipo:** las opciones más simples,
de más a menos esfuerzo:
1. Subir el `.html` a una carpeta compartida (Drive, SharePoint, etc.) y que
   cada uno lo abra desde ahí con doble click — funciona, pero cada persona
   lo tiene que volver a abrir para ver actualizaciones.
2. Subirlo a un hosting simple (Netlify, Vercel, GitHub Pages, o un
   servidor interno) para que todos entren por una misma URL — mejor
   experiencia, requiere que alguien lo despliegue una vez.
3. Si lo tenés abierto como artifact en Claude.ai, usar el botón "Share" /
   "Publicar" del panel del artifact — genera un link público que cualquiera
   puede abrir sin cuenta de Claude, sin necesidad de hosting propio. (En
   planes Team/Enterprise, un administrador de la organización puede tener
   que habilitar antes el uso de links públicos.)

## Dónde están las definiciones

Cualquier duda de "¿esto cuenta como entregado?" o "¿por qué el corte es a
las 21 y no a las 20?" se responde en **`reglas_de_negocio.md`**, no en el
código. El script lee esas mismas reglas desde su sección `CONFIG` al
principio del archivo — si una definición cambia, se edita ahí y en el
`.md` al mismo tiempo.

## Cómo seguir escalando esto

Ideas para las próximas iteraciones, en orden sugerido:

1. **Cerrar las reglas pendientes** que quedaron abiertas en
   `reglas_de_negocio.md` (sección 5) a medida que haga falta decidir sobre
   ellas para un reporte real.
2. **Histórico comparable:** guardar cada reporte generado y armar una hoja
   o script aparte que compare período contra período (esta semana vs. la
   anterior, este mes vs. el pasado).
3. **Automatizar la descarga:** si el sistema de logística tiene una forma
   de exportar por API o por URL fija, se puede automatizar para que no
   haga falta descargar el archivo a mano cada vez.
4. **Alertas:** un chequeo simple que avise si algún chofer cae por debajo
   de cierto % de efectividad, o si el % de cancelados de la semana se
   dispara respecto del promedio.
5. **Dashboard:** una vez que el histórico tenga varios períodos cargados,
   pasar de archivos `.xlsx` sueltos a una vista tipo dashboard.

## Historial de cambios del proyecto

| Fecha | Cambio |
|---|---|
| 2026-09-01 | Versión inicial: estructura de carpetas, diccionario de datos, reglas de negocio (entrega efectiva, corte 21hs, cancelados, efectividad por chofer) y script `generar_reporte.py`. |
| 2026-09-01 | Dashboard interactivo (`dashboard/dashboard_logistica.html`) con carga de archivo en el navegador, período, gráficos y ranking. |
| 2026-09-02 | Corrección de bug crítico de datos que desaparecían por fallos transitorios de lectura; gráficos reescritos en SVG nativo (sin dependencia de Chart.js). |
| 2026-09-02 | Franjas horarias de entrega (4 tramos), filtros interactivos por zona/franja/chofer, columna Pendientes, y rediseño con la paleta de marca. |
| 2026-09-02 | Ajustes de UX: al cargar un archivo el panel se posiciona solo en el rango de fechas de ese archivo; se sacó el mensaje de carga con el detalle de cantidad/fechas de la pantalla; se corrigieron los labels de la leyenda en "Evolución diaria" que se salían del margen; el cruce por hora de entrega ahora incluye todos los estados (no solo entregado); el gráfico por zona muestra la cantidad de cada segmento de la barra; el ranking de choferes muestra la cantidad de entregas en cada una de las 4 franjas horarias. |
| 2026-09-02 | Rebranding: el dashboard pasó a llamarse "Seguimiento de envíos - Mercadopacks" (antes "Torre de Control · Envíos") y el logo autogenerado (SVG con las letras "MP") se reemplazó por el isotipo real de la empresa (`dashboard/assets/logo-mp.png`, embebido en el HTML como base64 para mantener el archivo autocontenido). |
