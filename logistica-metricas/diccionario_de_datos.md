# Diccionario de Datos — Export de Envíos

Documenta el archivo crudo que se descarga del sistema de gestión logística
(export tipo "MercadoPacks/Mercado Libre última milla"). Se actualiza cada vez
que aparece una columna nueva o cambia el significado de una existente.

## Estructura del archivo

- Formato de descarga: `.xls` (formato antiguo de Excel, generado por el
  sistema "LightData").
- Las primeras filas **no son datos**: contienen los filtros aplicados en el
  momento de la descarga (ej. rango de fechas, estado filtrado). El header
  real de la tabla aparece después de esas filas — el script lo detecta
  automáticamente buscando la fila que contiene `ID (Interno)`, así que no
  importa si el número de filas de filtros cambia.
- La última fila del archivo suele venir completamente vacía (fila basura al
  final del export) — el script la descarta.

## Columnas

| Columna | Tipo | Significado | Notas |
|---|---|---|---|
| `ID (Interno)` | numérico | ID interno del envío en el sistema de logística | Clave primaria de facto |
| `Número Tracking` | texto | Número de seguimiento del envío | En envíos de Mercado Libre suele ser numérico largo; en otros orígenes puede ser alfanumérico corto |
| `ID venta ML` | texto | ID de la venta en Mercado Libre | Vacío si el origen no es ML |
| `Usuario ML ID` | texto | ID del vendedor/cuenta de ML | |
| `Fecha Venta` | fecha (dd/mm/aaaa) | Fecha en que se generó la venta | |
| `Fecha Colecta` | fecha y hora | Fecha/hora en que el paquete fue retirado del depósito/vendedor | Puede estar vacía si el paquete no pasó por colecta (ej. ya estaba en planta) |
| `Fecha MercadoPacks` | fecha y hora | Fecha/hora de ingreso del envío al sistema de logística | |
| `Método de envío` | categórico | Modalidad de envío: `Prioritario a domicilio`, `Express a domicilio`, `Estándar a domicilio`, `Prioritario` | |
| `Cod.Cliente` | texto | Código interno del cliente/cuenta que genera el envío | |
| `Razon Social` / `Nombre Fantasia` / `Nombre cuenta` | texto | Identificación del cliente/cuenta comercial | |
| `Nombre Destinatario` | texto | Nombre de quien recibe el envío | Dato personal — tratar con cuidado en reportes |
| `Tel. Destinatario` / `Email Destinatario` | texto | Contacto del destinatario | Dato personal |
| `Comentario Destino` | texto | Comentarios/indicaciones de entrega | |
| `Tipo direccion` | categórico | Tipo de dirección de destino | |
| `Dirección` / `CP` / `Localidad` / `Provincia` | texto | Domicilio de entrega | |
| `Latitud` / `Longitud` | numérico | Coordenadas geográficas del destino | |
| **`Estado`** | categórico | **Estado actual del envío.** Ver tabla de estados abajo | Columna clave para casi todas las métricas |
| **`Fecha estado`** | fecha y hora (dd/mm/aaaa HH:MM) | Fecha/hora en que se registró el estado actual | **Se usa como "hora de entrega real"** cuando `Estado` = entrega efectiva (definido en `reglas_de_negocio.md`) |
| `Quien estado` | texto | Usuario/chofer que actualizó el estado | Muchas veces vacío aunque el envío sí tenga chofer asignado — no usar como reemplazo de `Cadete` |
| `Zona` | categórico | Zona geográfica de reparto: `CABA`, `ZONA 1`, `ZONA 2`, `ZONA 3` | ~9% de las filas vienen sin zona asignada |
| `Zona precio` | categórico | Zona usada para tarifar (puede diferir de `Zona`) | |
| `Precio` | numérico | Costo del envío | Puede venir vacío |
| **`Cadete`** | texto | **Chofer/repartidor asignado al envío** | Viene vacío quando el envío no requiere reparto (ej. `A retirar` en sucursal) o cuando aún no fue asignado. Ver notas en reglas de negocio antes de rankear choferes |
| `Fecha de asignación` | fecha y hora | Momento en que el envío fue asignado a un chofer | |
| `Origen` | categórico | Canal de origen del envío: `ML`, `Directo`, `TNube`, `ML TURBO` | |
| `Observaciones` | texto | Notas libres cargadas por el operador | |
| `URl Tracking` | texto | Link de seguimiento público del envío | |
| `Total a cobrar` | numérico | Monto a cobrar contra entrega (contra-reembolso) | Casi siempre vacío en la muestra revisada |
| `Logistica Inversa` | texto libre | Indicaciones de devolución/cambio de producto | Sin estandarizar (valores como `SI`, `si`, `CAMBIO`, texto libre) — no usar para métricas cuantitativas sin normalizar antes |

## Valores observados de `Estado`

| Estado | Significado | Categoría (ver reglas de negocio) |
|---|---|---|
| `Entregado` | Entrega exitosa en destino | Entrega efectiva |
| `Entregado 2DA visita` | Entrega exitosa en un segundo intento | Entrega efectiva |
| `Cancelado` | Envío cancelado | Cancelado |
| `Rechazado por el comprador` | El destinatario rechazó el paquete | Cancelado |
| `En planta de procesamiento` | Aún en depósito, sin salir a reparto | En curso |
| `A retirar` | Envío que todavía no llegó al depósito (no entró al circuito de reparto) | En curso — excluido también del *denominador* del % de efectividad, no solo del numerador (ver reglas_de_negocio.md, regla #1) |
| `En camino al destinatario` | En reparto | En curso |
| `En camino reprogramado` | En reparto, pero con entrega reprogramada | En curso |
| `reprogramado por meli` | Reprogramado por decisión de Mercado Libre | En curso |
| `Retirado` | Retirado en sucursal por el destinatario | *(a definir — ver reglas de negocio)* |
| `Nadie` | Repartidor fue pero no había quien reciba | *(a definir)* |
| `Nadie 2DA visita` | Ídem, en segundo intento | *(a definir)* |

## Preguntas abiertas / pendientes de definir

- **Corrección 2026-09-04:** la descripción de `A retirar` decía antes
  "pendiente de retiro en sucursal por el destinatario" — se corrigió a
  "todavía no llegó al depósito" a partir de la aclaración del equipo, que
  también definió que debe excluirse del denominador del % de efectividad
  (ver reglas_de_negocio.md, regla #1).
- `Retirado`, `Nadie` y `Nadie 2DA visita` todavía no están clasificados en
  ninguna categoría de negocio — no se usan en las métricas actuales del
  script hasta que se definan (quedan en la categoría genérica "otros / en
  curso"). Definir en `reglas_de_negocio.md` cuando haya casos suficientes
  para decidir.
- `Logistica Inversa` no tiene valores estandarizados — si en algún momento
  se necesita medir volumen de cambios/devoluciones, primero hay que acordar
  una lista cerrada de valores válidos con el sistema de origen.
