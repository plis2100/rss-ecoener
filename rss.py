import json
import urllib.request
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import urljoin

WEB_URL = "https://www.ecoener.es/noticias"
BASE_URL = "https://www.ecoener.es"
OUTPUT_FILE = Path("ecoener.xml")


def descargar_noticias():
    solicitud = urllib.request.Request(
        WEB_URL,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/124 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,*/*;q=0.8"
            ),
            "Accept-Language": "es-ES,es;q=0.9",
            "Cache-Control": "no-cache",
        },
    )

    with urllib.request.urlopen(solicitud, timeout=60) as respuesta:
        contenido = respuesta.read()

    soup = BeautifulSoup(contenido, "html.parser")
    datos_elemento = soup.find("script", id="__NEXT_DATA__")

    if not datos_elemento:
        raise RuntimeError(
            "No se encontraron los datos internos de Ecoener"
        )

    datos = json.loads(datos_elemento.string)
    pagina = datos.get("props", {}).get("pageProps", {})
    noticias_originales = pagina.get("noticias", [])

    noticias = []
    enlaces_encontrados = set()

    for noticia in noticias_originales:
        atributos = noticia.get("attributes", {})

        titulo = atributos.get("titular", "").strip()
        identificador = atributos.get(
            "identificador",
            "",
        ).strip()
        fecha = atributos.get("fechaPublicacion", "").strip()

        if not titulo or not identificador:
            continue

        enlace = urljoin(
            BASE_URL,
            f"/noticias/{identificador}",
        )

        if enlace in enlaces_encontrados:
            continue

        categoria = ""

        categoria_datos = (
            atributos.get("categoria", {})
            .get("data")
        )

        if categoria_datos:
            categoria = (
                categoria_datos.get("attributes", {})
                .get("nombre", "")
                .strip()
            )

        imagen = ""

        imagen_datos = (
            atributos.get("imagen", {})
            .get("data")
        )

        if imagen_datos:
            imagen = (
                imagen_datos.get("attributes", {})
                .get("url", "")
                .strip()
            )

        enlaces_encontrados.add(enlace)

        noticias.append(
            {
                "titulo": titulo,
                "enlace": enlace,
                "fecha": fecha,
                "categoria": categoria,
                "imagen": imagen,
            }
        )

    noticias.sort(
        key=lambda elemento: elemento["fecha"],
        reverse=True,
    )

    return noticias[:100]


def crear_rss(noticias):
    rss = ET.Element(
        "rss",
        {
            "version": "2.0",
            "xmlns:atom": "http://www.w3.org/2005/Atom",
            "xmlns:media": "http://search.yahoo.com/mrss/",
        },
    )

    canal = ET.SubElement(rss, "channel")

    ET.SubElement(canal, "title").text = (
        "Noticias de Ecoener"
    )
    ET.SubElement(canal, "link").text = WEB_URL
    ET.SubElement(canal, "description").text = (
        "Últimas noticias corporativas, financieras "
        "y de proyectos de Ecoener"
    )
    ET.SubElement(canal, "language").text = "es"
    ET.SubElement(canal, "lastBuildDate").text = format_datetime(
        datetime.now(timezone.utc)
    )

    enlace_atom = ET.SubElement(
        canal,
        "{http://www.w3.org/2005/Atom}link",
    )
    enlace_atom.set("href", WEB_URL)
    enlace_atom.set("rel", "self")
    enlace_atom.set("type", "application/rss+xml")

    for noticia in noticias:
        elemento = ET.SubElement(canal, "item")

        ET.SubElement(
            elemento,
            "title",
        ).text = noticia["titulo"]

        ET.SubElement(
            elemento,
            "link",
        ).text = noticia["enlace"]

        ET.SubElement(
            elemento,
            "description",
        ).text = noticia["titulo"]

        identificador = ET.SubElement(elemento, "guid")
        identificador.set("isPermaLink", "true")
        identificador.text = noticia["enlace"]

        if noticia["categoria"]:
            ET.SubElement(
                elemento,
                "category",
            ).text = noticia["categoria"]

        if noticia["imagen"]:
            imagen = ET.SubElement(
                elemento,
                "{http://search.yahoo.com/mrss/}content",
            )
            imagen.set("url", noticia["imagen"])
            imagen.set("medium", "image")

        if noticia["fecha"]:
            try:
                fecha_publicacion = datetime.strptime(
                    noticia["fecha"],
                    "%Y-%m-%d",
                ).replace(tzinfo=timezone.utc)

                ET.SubElement(
                    elemento,
                    "pubDate",
                ).text = format_datetime(fecha_publicacion)
            except ValueError:
                pass

    ET.indent(rss, space="  ")

    ET.ElementTree(rss).write(
        OUTPUT_FILE,
        encoding="utf-8",
        xml_declaration=True,
    )


def main():
    noticias = descargar_noticias()

    if not noticias:
        raise RuntimeError(
            "No se encontraron noticias de Ecoener"
        )

    crear_rss(noticias)

    print(
        f"RSS creada correctamente con "
        f"{len(noticias)} noticias"
    )


if __name__ == "__main__":
    main()
