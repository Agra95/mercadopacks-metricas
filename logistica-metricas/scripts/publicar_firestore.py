#!/usr/bin/env python3
"""
publicar_firestore.py
----------------------
Toma un export crudo de LightData (.xls/.xlsx), calcula el snapshot diario
que consume el dashboard (mismo formato que antes armaba `procesarArchivo`
en el navegador, función que ya no existe — el dashboard es hoy un lector
puro de Firestore) y lo publica en Firestore.

Las reglas de negocio (qué es una entrega efectiva, qué es un cancelado, el
corte horario, a qué día pertenece cada envío) son las mismas que usan
generar_reporte.py, el dashboard y reglas_de_negocio.md. Si una regla
cambia, hay que actualizar los cuatro lugares — están comentados para que
sea fácil encontrarlos.

Uso:
    FIREBASE_SERVICE_ACCOUNT='{"type": "service_account", ...}' \
    python3 publicar_firestore.py ../datos_crudos/listado_envios_XXXX.xls
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generar_reporte import cargar_export, procesar  # noqa: E402


# ============================================================================
# Franjas horarias — deben coincidir con reglas_de_negocio.md sección 8 y
# con BUCKETS/bucketDeHora en dashboard_logistica.html.
# ============================================================================

def bucket_de_hora(hora: int) -> str:
    if hora < 21:
        return "antes21"
    if hora == 21:
        return "e21_22"
    if hora == 22:
        return "e22_23"
    return "despues23"


def nuevos_buckets() -> dict:
    return {"antes21": 0, "e21_22": 0, "e22_23": 0, "despues23": 0}


def sumar_bucket(destino: dict, clave: str):
    destino[clave] = destino.get(clave, 0) + 1


def fecha_operativa(fila: pd.Series):
    """
    A qué día pertenece el envío — reglas_de_negocio.md sección 5: se usa
    'Fecha MercadoPacks' (día de ingreso al sistema); si falta, se cae a
    'Fecha estado' como respaldo. Misma lógica que parseFechaSolo() en el
    dashboard.
    """
    for columna in ("Fecha MercadoPacks", "Fecha estado"):
        valor = fila.get(columna)
        if valor and str(valor).strip():
            try:
                solo_fecha = str(valor).strip().split(" ")[0]
                return datetime.strptime(solo_fecha, "%d/%m/%Y").strftime("%Y-%m-%d")
            except ValueError:
                continue
    return None


def calcular_snapshots(df: pd.DataFrame) -> dict:
    """
    df ya pasó por procesar() de generar_reporte.py, así que trae
    Estado/Cadete/Zona limpios y _fecha_estado_dt / es_entrega_efectiva /
    es_cancelado calculados.
    """
    snapshots: dict = {}

    for _, fila in df.iterrows():
        fecha = fecha_operativa(fila)
        if not fecha:
            continue

        snap = snapshots.setdefault(fecha, {
            "fecha": fecha,
            "cargadoEn": datetime.now(timezone.utc).isoformat(),
            "total": 0, "efectivas": 0, "cancelados": 0, "sinChofer": 0, "aRetirar": 0,
            "buckets": nuevos_buckets(),
            "porEstadoHora": {},
            "porHora": [0] * 24,
            "porChofer": {},
            "porZona": {},
        })

        estado = str(fila["Estado"])
        cadete = str(fila["Cadete"])
        zona = str(fila["Zona"])
        es_efectiva = bool(fila["es_entrega_efectiva"])
        es_cancel = bool(fila["es_cancelado"])
        # "A retirar" = todavía no llegó al depósito, no corresponde
        # contarlo en el universo de entregas para el % de efectividad
        # (reglas_de_negocio.md, regla #1).
        es_a_retirar = estado == "A retirar"

        dt = fila.get("_fecha_estado_dt")
        hora = dt.hour if dt is not None and not pd.isna(dt) else None
        hora_bucket = bucket_de_hora(hora) if hora is not None else None
        # Los buckets "oficiales" (globales/zona/chofer) son solo sobre
        # entregas efectivas (regla de negocio #8); porEstadoHora es la
        # excepción y desglosa TODOS los estados (ver reglas_de_negocio.md).
        bucket = hora_bucket if es_efectiva else None

        snap["total"] += 1
        if es_efectiva:
            snap["efectivas"] += 1
            if hora is not None:
                snap["porHora"][hora] += 1
            if bucket:
                sumar_bucket(snap["buckets"], bucket)
        if es_cancel:
            snap["cancelados"] += 1
        if es_a_retirar:
            snap["aRetirar"] += 1

        if hora_bucket:
            eb = snap["porEstadoHora"].setdefault(estado, nuevos_buckets())
            sumar_bucket(eb, hora_bucket)

        if not cadete:
            snap["sinChofer"] += 1
        else:
            pc = snap["porChofer"].setdefault(cadete, {
                "total": 0, "efectivas": 0, "cancelados": 0, "aRetirar": 0,
                "buckets": nuevos_buckets(), "porZona": {},
            })
            pc["total"] += 1
            if es_efectiva:
                pc["efectivas"] += 1
            if es_cancel:
                pc["cancelados"] += 1
            if es_a_retirar:
                pc["aRetirar"] += 1
            if bucket:
                sumar_bucket(pc["buckets"], bucket)
            pc["porZona"][zona] = pc["porZona"].get(zona, 0) + 1

        pz = snap["porZona"].setdefault(zona, {
            "total": 0, "efectivas": 0, "cancelados": 0, "aRetirar": 0, "buckets": nuevos_buckets(),
        })
        pz["total"] += 1
        if es_efectiva:
            pz["efectivas"] += 1
        if es_cancel:
            pz["cancelados"] += 1
        if es_a_retirar:
            pz["aRetirar"] += 1
        if bucket:
            sumar_bucket(pz["buckets"], bucket)

    return snapshots


def publicar(snapshots: dict, sa_json: str):
    """
    Escribe cada snapshot en envios_daily/<fecha> y agrega esa fecha al
    índice (envios_index/index) sin pisar fechas que ya estaban cargadas por
    otra corrida — nunca se asume que el índice está vacío ni se sobrescribe
    sin fusionar primero.
    """
    cred = credentials.Certificate(json.loads(sa_json))
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    db = firestore.client()

    index_ref = db.collection("envios_index").document("index")
    existente = index_ref.get()
    fechas = set(existente.to_dict().get("dates", [])) if existente.exists else set()

    for fecha, snap in snapshots.items():
        db.collection("envios_daily").document(fecha).set(snap)
        fechas.add(fecha)

    index_ref.set({"dates": sorted(fechas)})


def main():
    if len(sys.argv) < 2:
        sys.exit("Uso: publicar_firestore.py <archivo_crudo.xls>")

    ruta = Path(sys.argv[1])
    if not ruta.exists():
        sys.exit(f"No se encontró el archivo: {ruta}")

    sa_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
    if not sa_json:
        sys.exit("Falta la variable de entorno FIREBASE_SERVICE_ACCOUNT (JSON de la service account).")

    print(f"Leyendo {ruta} ...")
    df = procesar(cargar_export(ruta))
    snapshots = calcular_snapshots(df)
    print(f"  {len(snapshots)} día(s) encontrados: {', '.join(sorted(snapshots))}")

    publicar(snapshots, sa_json)
    print("Publicado en Firestore correctamente.")


if __name__ == "__main__":
    main()
