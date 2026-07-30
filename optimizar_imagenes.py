#!/usr/bin/env python3
"""
optimizar_imagenes.py
----------------------
Redimensiona y comprime las imágenes de la carpeta img/ del sitio VIP Catering.

QUÉ HACE:
1. Recorre recursivamente la carpeta img/ (o la que le indiques).
2. Antes de tocar nada, copia todos los originales a img_originales_backup/
   (por si algo sale mal, siempre puedes volver atrás).
3. Para cada imagen, calcula un ancho objetivo según:
   - Un mapeo específico (ANCHOS_ESPECIFICOS) para las imágenes que ya
     sabemos dónde y a qué tamaño se muestran (hero, carruseles, etc.)
   - Un ancho máximo genérico (ANCHO_MAXIMO_DEFECTO) para todo lo demás,
     que evita que cualquier imagen pase de cierto tamaño sin necesidad.
4. Si la imagen ya es más chica que el objetivo, la deja igual (no la agranda).
5. Guarda todo como WebP con calidad 80 (buen balance calidad/peso).
6. Al final imprime un resumen con el ahorro total en KB/MB.

CÓMO USARLO:
    pip install pillow
    python3 optimizar_imagenes.py ruta/a/tu/carpeta/img

    (si no le pasas ninguna ruta, usa "./img" por defecto)

IMPORTANTE:
- Corre esto ANTES de subir el sitio, sobre tu copia local del proyecto.
- Revisa visualmente algunas imágenes optimizadas antes de reemplazar
  las de producción, sobre todo si alguna se ve borrosa a ese ancho.
- Si una imagen tiene texto o detalles muy finos, considera subirle un
  poco la calidad (línea CALIDAD_WEBP) o el ancho objetivo.
"""

import sys
import shutil
from pathlib import Path
from PIL import Image

# ---------------------------------------------------------------------------
# CONFIGURACIÓN — ajusta esto a tu gusto
# ---------------------------------------------------------------------------

# Ancho máximo (en px) para cualquier imagen que no esté en ANCHOS_ESPECIFICOS.
# 2x el ancho de despliegue más común en el sitio (para pantallas retina).
ANCHO_MAXIMO_DEFECTO = 1600

# Calidad de compresión WebP (0-100). 80 es un buen balance para fotos.
CALIDAD_WEBP = 80

# Anchos específicos para imágenes que sabemos exactamente dónde se usan.
# La clave es el NOMBRE DE ARCHIVO (sin ruta), el valor es el ancho objetivo en px.
# Calculado cruzando cada <img> del index.html con la clase CSS que lo contiene.
# Cuando una misma imagen se usa en más de un lugar (ej: sillas-manteles.webp
# aparece en una card Y en el carrusel), se tomó el ancho del uso más grande.
ANCHOS_ESPECIFICOS = {
    # --- Logos (header y overlay del hero) ---
    "cortado.png": 800,   # .logo, CSS width: 380px desktop
    "central.png": 800,   # .sobre, CSS width: 14-22% viewport

    # --- Hero (#inicio .foto, CSS width: 360px desktop / 270px móvil) ---
    "servicio-catering-empresarial-corporativo.webp": 720,

    # --- Cards de Servicios y Alquileres (.card-img-top, height fijo 250px,
    #     ancho de columna Bootstrap ~350-400px) ---
    "refrigerio-corporativo.webp": 800,
    "tabla-quesos-evento-corporativo.jpg": 800,
    "estacion-cafe-vip-catering.jpg": 800,
    "ceviche.webp": 800,
    "cocteles-servicio-catering.jpg": 800,
    "cristaleria-eventos-corporativos.jpg": 800,
    "vajilla-alquiler-bogota.jpg": 800,

    # --- Especialidades (.centrada / .vista-movil, col-md-4 ~380px,
    #     en móvil fluye a ancho completo de columna) ---
    "paellas-paelleras.jpg": 900,   # también en carrusel Nosotros, se usó el mayor
    "paella-centrada.jpg": 1200,    # versión móvil, ancho de pantalla completo
    "asados-bogota.webp": 800,

    # --- Carrusel galería principal (#galeria, carousel-container max-width 800px) ---
    "buffet-pasabocas.webp": 1600,
    "servicio-tabla-quesos-eventos.jpg": 1600,
    "mesero-servicio-profesional-catering.jpg": 1600,
    "paella.webp": 1600,            # también en carrusel Nosotros, se usó el mayor
    "almuerzo-ejecutivo-empresarial.webp": 1600,
    "almuerzo-ejecutivo-corporativo.webp": 1600,
    "pasabocas-catering.jpg": 1600,
    "pavo-relleno.webp": 1600,
    "lasaña-almuerzo-vip-catering.jpg": 1600,
    "plato-asado-vip-catering.webp": 1600,
    "montaje.webp": 1600,
    "sillas-manteles.webp": 1600,   # también en card-img-top, se usó el mayor
    # equipo-vip-catering-buffet-empresarial.jpg también en carrusel: ver abajo

    # --- Carrusel "Nosotros" (.carrusel-nosotros-frame, max-width 450px) ---
    "servicio-catering-evento-social.webp": 900,
    "flores.webp": 900,
    "mesa.webp": 900,
    "mesa2.webp": 900,
    "pavo1.webp": 900,
    "pavo-navideño-evento-empresarial.webp": 900,  # también en especialidades, se usó el mayor
    "ensalada-rusa.webp": 900,
    "paella-molde.jpg": 900,
    "pasabocas1.webp": 900,
    "pasabocas2.webp": 900,
    "pasabocas3.webp": 900,
    "volovanes.webp": 900,
    "empanadas-pasabocas-catering-empresarial.jpg": 900,
    "almuerzo-gourmet-evento-corporativo.webp": 900,
    "almuerzo-empacado.webp": 900,

    # --- Aparece en card-img-top (800) Y en el carrusel principal (1600) ---
    "equipo-vip-catering-buffet-empresarial.jpg": 1600,
}

# Extensiones de imagen que el script va a procesar.
EXTENSIONES_VALIDAS = {".webp", ".jpg", ".jpeg", ".png"}

# ---------------------------------------------------------------------------
# LÓGICA DEL SCRIPT — normalmente no necesitas tocar nada de aquí para abajo
# ---------------------------------------------------------------------------


def obtener_ancho_objetivo(nombre_archivo: str) -> int:
    """Devuelve el ancho objetivo para un archivo dado."""
    return ANCHOS_ESPECIFICOS.get(nombre_archivo, ANCHO_MAXIMO_DEFECTO)


def procesar_imagen(ruta: Path, ancho_objetivo: int) -> tuple[int, int]:
    """
    Redimensiona y comprime una imagen in-place (mismo nombre, mismo formato).
    Devuelve (peso_original_bytes, peso_final_bytes).
    """
    peso_original = ruta.stat().st_size

    with Image.open(ruta) as img:
        ancho_actual, alto_actual = img.size

        # Si la imagen tiene transparencia, la preservamos (modo RGBA).
        # Si no, usamos RGB para evitar archivos más pesados de lo necesario.
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA" if "A" in img.mode else "RGB")

        # Solo reducimos, nunca agrandamos una imagen que ya es más chica.
        if ancho_actual > ancho_objetivo:
            ratio = ancho_objetivo / ancho_actual
            nuevo_tamaño = (ancho_objetivo, round(alto_actual * ratio))
            img = img.resize(nuevo_tamaño, Image.LANCZOS)

        # Guardamos siempre como WebP, sin importar el formato original,
        # porque es el que ya usa la mayoría del sitio y es el más liviano.
        ruta_salida = ruta.with_suffix(".webp")
        img.save(ruta_salida, "WEBP", quality=CALIDAD_WEBP, method=6)

        # Si el formato cambió (ej: .jpg -> .webp), borramos el archivo viejo
        # para no dejar duplicados. OJO: esto significa que si tenías un
        # .jpg referenciado en el HTML, tendrás que actualizar esa referencia
        # a .webp manualmente.
        if ruta_salida != ruta:
            ruta.unlink()

    peso_final = ruta_salida.stat().st_size
    return peso_original, peso_final


def main():
    carpeta_img = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("./img")

    if not carpeta_img.exists():
        print(f"❌ No encontré la carpeta: {carpeta_img}")
        print("   Uso: python3 optimizar_imagenes.py ruta/a/tu/carpeta/img")
        sys.exit(1)

    # --- Paso 1: backup de seguridad ---
    carpeta_backup = carpeta_img.parent / f"{carpeta_img.name}_originales_backup"
    if carpeta_backup.exists():
        print(f"⚠️  Ya existe un backup en {carpeta_backup}, no lo voy a sobrescribir.")
        print("   Si quieres rehacer el backup, borra esa carpeta primero.")
    else:
        print(f"📦 Copiando originales a {carpeta_backup} ...")
        shutil.copytree(carpeta_img, carpeta_backup)
        print("   Backup listo.\n")

    # --- Paso 2: procesar todas las imágenes ---
    archivos = [
        p for p in carpeta_img.rglob("*")
        if p.is_file() and p.suffix.lower() in EXTENSIONES_VALIDAS
    ]

    if not archivos:
        print(f"No encontré imágenes en {carpeta_img}")
        sys.exit(0)

    print(f"🔍 Encontré {len(archivos)} imágenes. Procesando...\n")

    total_original = 0
    total_final = 0
    formatos_cambiados = []

    for ruta in archivos:
        ancho_objetivo = obtener_ancho_objetivo(ruta.name)
        try:
            peso_original, peso_final = procesar_imagen(ruta, ancho_objetivo)
        except Exception as e:
            print(f"  ⚠️  Error procesando {ruta.name}: {e}")
            continue

        total_original += peso_original
        total_final += peso_final

        if ruta.suffix.lower() != ".webp":
            formatos_cambiados.append(ruta.name)

        ahorro_pct = (1 - peso_final / peso_original) * 100 if peso_original else 0
        print(
            f"  {ruta.name:<55} "
            f"{peso_original/1024:>7.0f} KB -> {peso_final/1024:>7.0f} KB "
            f"({ahorro_pct:>5.1f}% menos)"
        )

    # --- Resumen final ---
    print("\n" + "=" * 70)
    print(f"Total original: {total_original/1024/1024:.2f} MB")
    print(f"Total final:    {total_final/1024/1024:.2f} MB")
    ahorro_total_pct = (1 - total_final / total_original) * 100 if total_original else 0
    ahorro_mb = (total_original - total_final) / 1024 / 1024
    print(f"Ahorro total:   {ahorro_mb:.2f} MB ({ahorro_total_pct:.0f}%)")
    print("=" * 70)

    if formatos_cambiados:
        print(
            f"\n⚠️  {len(formatos_cambiados)} archivo(s) cambiaron de formato a .webp:"
        )
        for nombre in formatos_cambiados:
            nuevo_nombre = Path(nombre).with_suffix(".webp").name
            print(f"   {nombre} -> {nuevo_nombre}")
        print(
            "\n   Tendrás que actualizar esas referencias en tu index.html "
            "(buscar el nombre viejo y reemplazarlo por el .webp)."
        )

    print(f"\n✅ Listo. Tus originales están a salvo en: {carpeta_backup}")


if __name__ == "__main__":
    main()
