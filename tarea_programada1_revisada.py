from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Tuple
import csv
import os
import pickle
import re

Token = Tuple[str, str]
RegistroBitacora = Tuple[str, str]
ReporteToken = Tuple[str, str, int]


@dataclass
class EstadoAplicacion:
    """Guarda la informacion que el programa necesita mientras esta activo."""
    tokens: List[Token] = field(default_factory=list)
    bitacora: List[RegistroBitacora] = field(default_factory=list)
    ultimoReporte: List[ReporteToken] = field(default_factory=list)
    textoTraducido: str = ""
    rutaSalidaTraduccion: str = ""
    duracionTraduccion: float = 0.0
    totalPalabrasProcesables: int = 0
    totalReemplazos: int = 0
    archivoEntrada: str = ""


def obtenerMarcaTiempo() -> str:
    """Funcionalidad: Obtiene la fecha y hora actual para usarla en la bitacora.
    Entradas: Ninguna.
    Salidas: Una cadena con formato AAAA-MM-DD_hh:mm:ss.
    """
    return datetime.now().strftime("%Y-%m-%d_%H:%M:%S")


def solicitarEntradaNoVacia(mensaje: str) -> str:
    """Funcionalidad: Solicita al usuario un dato y no permite que quede vacio.
    Entradas: Un mensaje para mostrar en pantalla.
    Salidas: Una cadena escrita por el usuario.
    """
    while True:
        valor = input(mensaje).strip()
        if valor != "":
            return valor
        print("El dato no puede estar vacio. Intente nuevamente.")


def registrarEvento(bitacora: List[RegistroBitacora], descripcion: str) -> None:
    """Funcionalidad: Agrega un evento a la bitacora y lo guarda en archivo.
    Entradas: La lista de bitacora y la descripcion del evento.
    Salidas: Ninguna.
    """
    bitacora.append((obtenerMarcaTiempo(), descripcion))
    guardarBitacoraEnArchivo(bitacora)


def construirDiccionarioTokens(tokens: List[Token]) -> Dict[str, str]:
    """Funcionalidad: Convierte una lista de tuplas de tokens en un diccionario.
    Entradas: La lista de tokens cargados en memoria.
    Salidas: Un diccionario con la palabra original como llave.
    """
    diccionario: Dict[str, str] = {}
    for original, reemplazo in tokens:
        diccionario[original] = reemplazo
    return diccionario


def actualizarTokenEnLista(tokens: List[Token], original: str, reemplazo: str) -> bool:
    """Funcionalidad: Agrega un token nuevo o actualiza uno existente.
    Entradas: La lista de tokens, la palabra original y el reemplazo.
    Salidas: True si el token ya existia y fue actualizado, False si fue agregado.
    """
    indice = 0
    while indice < len(tokens):
        palabraActual, valorActual = tokens[indice]
        if palabraActual == original:
            tokens[indice] = (original, reemplazo)
            return True
        indice += 1
    tokens.append((original, reemplazo))
    return False


def validarLineaDeToken(linea: str, separador: str) -> bool:
    """Funcionalidad: Revisa si una linea contiene un par valido original-reemplazo.
    Entradas: Una linea de texto y el separador elegido por el usuario.
    Salidas: True si la linea tiene informacion util, False en caso contrario.
    """
    lineaLimpia = linea.strip()
    if lineaLimpia == "":
        return False
    if separador == "":
        return False
    if separador not in lineaLimpia:
        return False
    partes = lineaLimpia.split(separador)
    if len(partes) < 2:
        return False
    original = partes[0].strip()
    reemplazo = separador.join(partes[1:]).strip()
    return original != "" and reemplazo != ""


def separarParesDesdeTexto(texto: str, separador: str) -> List[Token]:
    """Funcionalidad: Extrae pares original-reemplazo desde un texto completo.
    Entradas: Un texto con varias lineas y el separador usado en el archivo.
    Salidas: Una lista de tuplas con los pares encontrados.
    """
    pares: List[Token] = []
    lineas = texto.splitlines()
    for linea in lineas:
        lineaLimpia = linea.strip()
        if lineaLimpia == "":
            continue
        if lineaLimpia.startswith("#"):
            continue
        if not validarLineaDeToken(lineaLimpia, separador):
            continue
        partes = lineaLimpia.split(separador)
        original = partes[0].strip()
        reemplazo = separador.join(partes[1:]).strip()
        if original != "" and reemplazo != "":
            pares.append((original, reemplazo))
    return pares


def cargarTokensDesdeArchivo(estado: EstadoAplicacion) -> None:
    """Funcionalidad: Lee un archivo de tokens y los agrega a la memoria.
    Entradas: El estado general de la aplicacion.
    Salidas: Ninguna.
    """
    ruta = solicitarEntradaNoVacia("Nombre del archivo de tokens: ")
    separador = solicitarEntradaNoVacia("Separador usado en el archivo: ")

    if not os.path.exists(ruta):
        print("El archivo indicado no existe.")
        registrarEvento(estado.bitacora, f"Intento fallido de carga de tokens: {ruta}")
        return

    with open(ruta, "r", encoding="utf-8") as archivo:
        contenido = archivo.read()

    pares = separarParesDesdeTexto(contenido, separador)
    if len(pares) == 0:
        print("No se encontraron equivalencias validas en el archivo.")
        registrarEvento(estado.bitacora, f"Archivo de tokens sin equivalencias validas: {ruta}")
        return

    for original, reemplazo in pares:
        existiaAntes = actualizarTokenEnLista(estado.tokens, original, reemplazo)
        if existiaAntes:
            print(f"Se reescribio el token '{original}' con el valor '{reemplazo}'.")
            registrarEvento(estado.bitacora, f"Token reescrito desde archivo: {original} -> {reemplazo}")
        else:
            print(f"Se cargo el token '{original}' con el valor '{reemplazo}'.")
            registrarEvento(estado.bitacora, f"Token cargado desde archivo: {original} -> {reemplazo}")

    print(f"Se cargaron {len(pares)} equivalencias desde el archivo.")
    registrarEvento(estado.bitacora, f"Carga completa de tokens desde archivo: {ruta}")


def validarTokensCargados(tokens: List[Token]) -> bool:
    """Funcionalidad: Verifica si hay tokens disponibles para mostrar.
    Entradas: La lista de tokens actual.
    Salidas: True si la lista tiene datos, False si esta vacia.
    """
    return len(tokens) > 0


def formatearTokensParaPantalla(tokens: List[Token]) -> List[str]:
    """Funcionalidad: Prepara los tokens para mostrarlos de forma ordenada.
    Entradas: La lista de tokens cargados.
    Salidas: Una lista de lineas ya listas para imprimirse.
    """
    lineas: List[str] = []
    indice = 1
    for original, reemplazo in tokens:
        lineas.append(f"{indice:03d}. {original} -> {reemplazo}")
        indice += 1
    return lineas


def mostrarTokensCargados(estado: EstadoAplicacion) -> None:
    """Funcionalidad: Muestra en pantalla los tokens que existen en memoria.
    Entradas: El estado general de la aplicacion.
    Salidas: Ninguna.
    """
    if not validarTokensCargados(estado.tokens):
        print("No hay tokens cargados en memoria.")
        registrarEvento(estado.bitacora, "Consulta de tokens: sin datos en memoria")
        return

    print("\nTOKENS CARGADOS")
    print("-" * 60)
    lineas = formatearTokensParaPantalla(estado.tokens)
    for linea in lineas:
        print(linea)
    print("-" * 60)
    registrarEvento(estado.bitacora, "Consulta de tokens cargados")


def validarTextoManual(texto: str, separador: str) -> bool:
    """Funcionalidad: Comprueba si el texto manual puede convertirse en tokens.
    Entradas: El texto digitado por el usuario y el separador elegido.
    Salidas: True si el texto permite extraer pares validos.
    """
    if texto.strip() == "":
        return False
    return separador in texto


def procesarTokensManuales(estado: EstadoAplicacion, texto: str, separador: str) -> None:
    """Funcionalidad: Convierte una entrada manual en tokens y la integra al sistema.
    Entradas: El estado de la aplicacion, el texto ingresado y el separador.
    Salidas: Ninguna.
    """
    pares = separarParesDesdeTexto(texto, separador)
    if len(pares) == 0:
        print("No se detectaron pares validos con el separador indicado.")
        registrarEvento(estado.bitacora, "Agregado o modificacion manual sin pares validos")
        return

    for original, reemplazo in pares:
        existiaAntes = actualizarTokenEnLista(estado.tokens, original, reemplazo)
        if existiaAntes:
            print(f"Actualizacion: '{original}' ahora vale '{reemplazo}'.")
            registrarEvento(estado.bitacora, f"Token actualizado manualmente: {original} -> {reemplazo}")
        else:
            print(f"Se agrego el token '{original}' con valor '{reemplazo}'.")
            registrarEvento(estado.bitacora, f"Token agregado manualmente: {original} -> {reemplazo}")

    print("Operacion finalizada correctamente.")
    registrarEvento(estado.bitacora, f"Agregado o modificacion manual completado con {len(pares)} pares")


def agregarOModificarTokens(estado: EstadoAplicacion) -> None:
    """Funcionalidad: Permite escribir tokens nuevos o actualizar los que ya existen.
    Entradas: El estado general de la aplicacion.
    Salidas: Ninguna.
    """
    print("Escriba un token por linea. Deje una linea vacia para terminar.")
    print("Escriba CANCELAR en la primera linea para anular la operacion.")
    separador = solicitarEntradaNoVacia("Separador usado en los datos: ")

    lineas: List[str] = []
    primeraLinea = input("> ").rstrip("\n")


    if primeraLinea.strip().upper() == "CANCELAR":
        print("Operacion cancelada.")
        registrarEvento(estado.bitacora, "Cancelacion de agregado o modificacion manual de tokens")
        return

    if primeraLinea.strip() != "":
        lineas.append(primeraLinea)

    while True:
        linea = input("> ").rstrip("\n")

        if linea.strip() == "":
            break
        lineas.append(linea)

    if len(lineas) == 0:
        print("No se ingresaron datos.")
        registrarEvento(estado.bitacora, "Intento de agregado o modificacion manual sin datos")
        return

    texto = "\n".join(lineas)
    if not validarTextoManual(texto, separador):
        print("El texto no contiene el separador solicitado.")
        registrarEvento(estado.bitacora, "Agregado o modificacion manual sin separador util")
        return

    procesarTokensManuales(estado, texto, separador)


def validarTokensParaGuardar(tokens: List[Token]) -> bool:
    """Funcionalidad: Revisa si la lista tiene tokens antes de guardarlos.
    Entradas: La lista actual de tokens.
    Salidas: True si hay contenido, False si no hay nada que guardar.
    """
    return len(tokens) > 0


def escribirTokensEnArchivo(tokens: List[Token], ruta: str, separador: str) -> None:
    """Funcionalidad: Escribe los tokens en un archivo de texto.
    Entradas: La lista de tokens, la ruta destino y el separador de salida.
    Salidas: Ninguna.
    """
    with open(ruta, "w", encoding="utf-8") as archivo:
        for original, reemplazo in tokens:
            archivo.write(f"{original}{separador}{reemplazo}\n")


def guardarTokensEnArchivo(estado: EstadoAplicacion) -> None:
    """Funcionalidad: Guarda en archivo los tokens que estan en memoria.
    Entradas: El estado general de la aplicacion.
    Salidas: Ninguna.
    """
    if not validarTokensParaGuardar(estado.tokens):
        print("No hay tokens para guardar.")
        registrarEvento(estado.bitacora, "Intento de guardar tokens sin datos")
        return

    ruta = solicitarEntradaNoVacia("Nombre del archivo destino: ")
    separador = solicitarEntradaNoVacia("Separador para guardar: ")
    escribirTokensEnArchivo(estado.tokens, ruta, separador)

    print(f"Tokens guardados en {ruta}.")
    registrarEvento(estado.bitacora, f"Tokens guardados en archivo: {ruta}")


def clasificarFragmento(fragmento: str) -> str:
    """Funcionalidad: Clasifica un fragmento para saber si se puede reemplazar.
    Entradas: Un fragmento de texto.
    Salidas: Una cadena que indica el tipo de fragmento.
    """
    if fragmento.isspace():
        return "espacio"
    if re.fullmatch(r"\d+(?:\.\d+)?", fragmento) is not None:
        return "numero"
    if re.fullmatch(r"[A-Za-z_]\w*", fragmento) is not None:
        return "identificador"
    if re.fullmatch(r"\".*?\"|'.*?'", fragmento, flags=re.DOTALL) is not None:
        return "cadena"
    return "simbolo"


def tokenizarLinea(linea: str) -> List[str]:
    """Funcionalidad: Divide una linea conservando espacios, signos y cadenas.
    Entradas: Una linea de codigo.
    Salidas: Una lista de fragmentos.
    """
    patron = re.compile(r"(\".*?\"|\'.*?\'|\b[A-Za-z_]\w*\b|\b\d+(?:\.\d+)?\b|\s+|.)", re.DOTALL)
    return patron.findall(linea)


def contarReemplazosPorToken(reporte: List[ReporteToken]) -> int:
    """Funcionalidad: Suma la cantidad total de reemplazos del reporte.
    Entradas: La lista de resultados de la traduccion.
    Salidas: Un numero entero con el total de reemplazos.
    """
    total = 0
    for _, _, cantidad in reporte:
        total += cantidad
    return total


def traducirCodigo(estado: EstadoAplicacion) -> None:
    """Funcionalidad: Lee un archivo fuente y genera una version traducida.
    Entradas: El estado general de la aplicacion.
    Salidas: Ninguna.
    """
    if len(estado.tokens) == 0:
        print("Primero debe cargar tokens.")
        registrarEvento(estado.bitacora, "Intento de traduccion sin tokens cargados")
        return

    rutaEntrada = solicitarEntradaNoVacia("Archivo de codigo a traducir: ")
    if not os.path.exists(rutaEntrada):
        print("El archivo indicado no existe.")
        registrarEvento(estado.bitacora, f"Intento fallido de traduccion. Archivo inexistente: {rutaEntrada}")
        return

    rutaSalida = solicitarEntradaNoVacia("Nombre del archivo de salida: ")
    diccionario = construirDiccionarioTokens(estado.tokens)
    conteos: Dict[str, int] = {}
    for original, _ in estado.tokens:
        conteos[original] = 0

    inicio = datetime.now()
    lineasSalida: List[str] = []
    totalFragmentosProcesables = 0
    totalReemplazos = 0

    with open(rutaEntrada, "r", encoding="utf-8") as archivoEntrada:
        for numeroLinea, linea in enumerate(archivoEntrada, start=1):
            fragmentos = tokenizarLinea(linea)
            fragmentosTraducidos: List[str] = []

            for fragmento in fragmentos:
                categoria = clasificarFragmento(fragmento)

                if categoria == "identificador" or categoria == "cadena":
                    totalFragmentosProcesables += 1
                    if fragmento in diccionario:
                        reemplazo = diccionario[fragmento]
                        fragmentosTraducidos.append(reemplazo)
                        conteos[fragmento] += 1
                        totalReemplazos += 1
                        registrarEvento(estado.bitacora, f"Reemplazo de traduccion: '{fragmento}' por '{reemplazo}' en linea {numeroLinea}")
                    else:
                        fragmentosTraducidos.append(fragmento)
                else:
                    fragmentosTraducidos.append(fragmento)

            lineasSalida.append("".join(fragmentosTraducidos))

    textoTraducido = "".join(lineasSalida)
    with open(rutaSalida, "w", encoding="utf-8") as archivoSalida:
        archivoSalida.write(textoTraducido)

    fin = datetime.now()
    duracion = (fin - inicio).total_seconds()

    reporte: List[ReporteToken] = []
    for original, reemplazo in estado.tokens:
        reporte.append((original, reemplazo, conteos[original]))

    estado.ultimoReporte = reporte
    estado.textoTraducido = textoTraducido
    estado.rutaSalidaTraduccion = rutaSalida
    estado.duracionTraduccion = duracion
    estado.totalPalabrasProcesables = totalFragmentosProcesables
    estado.totalReemplazos = totalReemplazos
    estado.archivoEntrada = rutaEntrada

    porcentaje = 0.0
    if totalFragmentosProcesables > 0:
        porcentaje = (totalReemplazos / totalFragmentosProcesables) * 100

    print(f"Traduccion completada en {duracion:.2f} segundos.")
    print(f"Reemplazos realizados: {totalReemplazos}")
    print(f"Porcentaje de palabras reemplazadas: {porcentaje:.2f}%")
    print(f"Archivo guardado en: {rutaSalida}")
    registrarEvento(estado.bitacora, f"Traduccion completada: {rutaEntrada} -> {rutaSalida}")


def escribirReporteCsv(reporte: List[ReporteToken], ruta: str) -> None:
    """Funcionalidad: Guarda el reporte de traduccion en un archivo CSV.
    Entradas: La lista de resultados y la ruta destino.
    Salidas: Ninguna.
    """
    with open(ruta, "w", newline="", encoding="utf-8") as archivoCsv:
        escritor = csv.writer(archivoCsv)
        escritor.writerow(["Palabra original", "Token de reemplazo", "Cantidad de reemplazos"])
        for original, reemplazo, cantidad in reporte:
            escritor.writerow([original, reemplazo, cantidad])


def generarReporteCsv(estado: EstadoAplicacion) -> None:
    """Funcionalidad: Genera un archivo CSV usando los datos de la ultima traduccion.
    Entradas: El estado general de la aplicacion.
    Salidas: Ninguna.
    """
    if len(estado.ultimoReporte) == 0:
        print("Primero debe realizar una traduccion para generar el CSV.")
        registrarEvento(estado.bitacora, "Intento de generacion CSV sin reporte previo")
        return

    ruta = solicitarEntradaNoVacia("Nombre del archivo CSV a generar: ")
    escribirReporteCsv(estado.ultimoReporte, ruta)
    print(f"Reporte CSV generado en {ruta}.")
    registrarEvento(estado.bitacora, f"Reporte CSV generado: {ruta}")


def crearContenidoHtml(estado: EstadoAplicacion, tituloReporte: str) -> str:
    """Funcionalidad: Construye el contenido HTML del reporte de traduccion.
    Entradas: El estado de la aplicacion y el titulo del reporte.
    Salidas: Una cadena con el documento HTML completo.
    """
    fechaHora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    porcentaje = 0.0
    if estado.totalPalabrasProcesables > 0:
        porcentaje = (estado.totalReemplazos / estado.totalPalabrasProcesables) * 100

    filas = []
    indice = 0
    for original, reemplazo, cantidad in estado.ultimoReporte:
        clase = "par" if indice % 2 == 0 else "impar"
        fila = f"<tr class='{clase}'><td>{original}</td><td>{reemplazo}</td><td>{cantidad}</td></tr>"
        filas.append(fila)
        indice += 1

    cuerpoFilas = "".join(filas)

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>{tituloReporte}</title>
  <style>
    body {{
      font-family: Arial, sans-serif;
      margin: 24px;
    }}
    table {{
      border-collapse: collapse;
      width: 100%;
      margin-top: 16px;
    }}
    th, td {{
      border: 1px solid #444;
      padding: 8px;
      text-align: center;
    }}
    tr.par {{
      background-color: #f2f2f2;
    }}
    tr.impar {{
      background-color: #ffffff;
    }}
  </style>
</head>
<body>
  <h1>Reporte de Traduccion</h1>
  <h2>Fecha y hora de generacion: {fechaHora}</h2>
  <p>Duracion total del procesamiento: {estado.duracionTraduccion:.2f} segundos</p>
  <p>Cantidad total de reemplazos: {estado.totalReemplazos}</p>
  <p>Porcentaje de palabras reemplazadas: {porcentaje:.2f}%</p>
  <table>
    <thead>
      <tr>
        <th>Palabra original</th>
        <th>Reemplazo</th>
        <th>Cantidad de reemplazos</th>
      </tr>
    </thead>
    <tbody>
      {cuerpoFilas}
    </tbody>
  </table>
</body>
</html>"""


def escribirReporteHtml(estado: EstadoAplicacion, tituloReporte: str, rutaHtml: str) -> None:
    """Funcionalidad: Escribe en disco el archivo HTML de la ultima traduccion.
    Entradas: El estado de la aplicacion, el titulo del reporte y la ruta de salida.
    Salidas: Ninguna.
    """
    contenido = crearContenidoHtml(estado, tituloReporte)
    with open(rutaHtml, "w", encoding="utf-8") as archivoHtml:
        archivoHtml.write(contenido)


def generarReporteHtml(estado: EstadoAplicacion) -> None:
    """Funcionalidad: Crea el reporte HTML a partir de la ultima traduccion realizada.
    Entradas: El estado general de la aplicacion.
    Salidas: Ninguna.
    """
    if len(estado.ultimoReporte) == 0:
        print("Primero debe realizar una traduccion para generar el HTML.")
        registrarEvento(estado.bitacora, "Intento de generacion HTML sin reporte previo")
        return

    titulo = solicitarEntradaNoVacia("Titulo del reporte HTML: ")
    nombreSeguro = f"reporteHTML_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.html"
    escribirReporteHtml(estado, titulo, nombreSeguro)
    print(f"Reporte HTML generado en {nombreSeguro}.")
    registrarEvento(estado.bitacora, f"Reporte HTML generado: {nombreSeguro}")


def guardarBitacoraEnArchivo(bitacora: List[RegistroBitacora], ruta: str = "bitacora.txt") -> None:
    """Funcionalidad: Guarda la bitacora completa en un archivo binario.
    Entradas: La lista de registros y la ruta destino.
    Salidas: Ninguna.
    """
    with open(ruta, "wb") as archivo:
        pickle.dump(bitacora, archivo)


def cargarBitacoraDesdeArchivo(ruta: str = "bitacora.txt") -> List[RegistroBitacora]:
    """Funcionalidad: Carga la bitacora guardada anteriormente, si existe.
    Entradas: La ruta del archivo binario.
    Salidas: Una lista de tuplas con los registros validos.
    """
    if not os.path.exists(ruta):
        return []

    try:
        with open(ruta, "rb") as archivo:
            contenido = pickle.load(archivo)
    except Exception:
        return []

    if not isinstance(contenido, list):
        return []

    bitacoraValida: List[RegistroBitacora] = []
    for elemento in contenido:
        if isinstance(elemento, tuple) and len(elemento) == 2:
            if isinstance(elemento[0], str) and isinstance(elemento[1], str):
                bitacoraValida.append(elemento)
    return bitacoraValida


def validarFechaBusqueda(fecha: str) -> bool:
    """Funcionalidad: Verifica si una fecha tiene el formato esperado para buscar.
    Entradas: Una cadena con la fecha a evaluar.
    Salidas: True si la fecha sigue el formato AAAA-MM-DD.
    """
    partes = fecha.strip().split("-")
    if len(partes) != 3:
        return False
    anio, mes, dia = partes
    if len(anio) != 4 or len(mes) != 2 or len(dia) != 2:
        return False
    if not anio.isdigit() or not mes.isdigit() or not dia.isdigit():
        return False
    return True


def filtrarBitacoraPorDia(bitacora: List[RegistroBitacora], fecha: str) -> List[RegistroBitacora]:
    """Funcionalidad: Obtiene los registros cuya fecha coincide con la buscada.
    Entradas: La bitacora y la fecha escrita por el usuario.
    Salidas: Una lista con los registros encontrados.
    """
    resultados: List[RegistroBitacora] = []
    prefijo = fecha.strip()
    for registro in bitacora:
        if registro[0].startswith(prefijo):
            resultados.append(registro)
    return resultados


def filtrarBitacoraPorPalabra(bitacora: List[RegistroBitacora], palabra: str) -> List[RegistroBitacora]:
    """Funcionalidad: Busca registros que contengan una palabra en la descripcion.
    Entradas: La bitacora y la palabra clave.
    Salidas: Una lista con los registros encontrados.
    """
    resultados: List[RegistroBitacora] = []
    palabraMin = palabra.strip().lower()
    for registro in bitacora:
        if palabraMin in registro[1].lower():
            resultados.append(registro)
    return resultados


def submenuBitacora(estado: EstadoAplicacion) -> None:
    """Funcionalidad: Permite consultar la bitacora por fecha o por palabra clave.
    Entradas: El estado general de la aplicacion.
    Salidas: Ninguna.
    """
    while True:
        print("\nSUBMENU DE BITACORA")
        print("A) Acciones por dia escogido")
        print("B) Acciones con algunas palabras clave")
        print("C) Salir del submenu")

        opcion = input("Seleccione una opcion: ").strip().upper()

        if opcion == "A":
            fecha = solicitarEntradaNoVacia("Digite la fecha en formato AAAA-MM-DD: ")
            if not validarFechaBusqueda(fecha):
                print("La fecha debe tener el formato AAAA-MM-DD.")
                registrarEvento(estado.bitacora, f"Consulta de bitacora con fecha invalida: {fecha}")
                continue

            resultados = filtrarBitacoraPorDia(estado.bitacora, fecha)
            print(f"\nResultados para la fecha {fecha}:")
            if len(resultados) == 0:
                print("No se encontraron registros.")
            else:
                for marca, descripcion in resultados:
                    print(f"{marca} | {descripcion}")
            registrarEvento(estado.bitacora, f"Consulta de bitacora por fecha: {fecha}")

        elif opcion == "B":
            palabra = solicitarEntradaNoVacia("Digite la palabra clave a buscar: ")
            resultados = filtrarBitacoraPorPalabra(estado.bitacora, palabra)
            print(f"\nResultados para la palabra clave '{palabra}':")
            if len(resultados) == 0:
                print("No se encontraron registros.")
            else:
                for marca, descripcion in resultados:
                    print(f"{marca} | {descripcion}")
            registrarEvento(estado.bitacora, f"Consulta de bitacora por palabra clave: {palabra}")

        elif opcion == "C":
            registrarEvento(estado.bitacora, "Salida del submenu de bitacora")
            break
        else:
            print("Opcion invalida en el submenu de bitacora.")


def mostrarMenu() -> None:
    """Funcionalidad: Imprime en pantalla el menu principal del programa.
    Entradas: Ninguna.
    Salidas: Ninguna.
    """
    print("\nMENU PRINCIPAL")
    print("1. Cargar tokens")
    print("2. Mostrar tokens")
    print("3. Agregar o modificar token")
    print("4. Guardar tokens")
    print("5. Traducir codigo")
    print("6. Generar CSV")
    print("7. Generar HTML")
    print("8. Submenu de bitacora del sistema")
    print("9. Salir")


def ejecutarMenu() -> None:
    """Funcionalidad: Controla el flujo principal del programa en consola.
    Entradas: Ninguna.
    Salidas: Ninguna.
    """
    estado = EstadoAplicacion()
    estado.bitacora = cargarBitacoraDesdeArchivo()
    registrarEvento(estado.bitacora, "Inicio del programa")

    while True:
        mostrarMenu()
        opcion = input("Seleccione una opcion: ").strip()

        if opcion == "1":
            registrarEvento(estado.bitacora, "Uso de la opcion 1: cargar tokens")
            cargarTokensDesdeArchivo(estado)
        elif opcion == "2":
            registrarEvento(estado.bitacora, "Uso de la opcion 2: mostrar tokens")
            mostrarTokensCargados(estado)
        elif opcion == "3":
            registrarEvento(estado.bitacora, "Uso de la opcion 3: agregar o modificar token")
            agregarOModificarTokens(estado)
        elif opcion == "4":
            registrarEvento(estado.bitacora, "Uso de la opcion 4: guardar tokens")
            guardarTokensEnArchivo(estado)
        elif opcion == "5":
            registrarEvento(estado.bitacora, "Uso de la opcion 5: traducir codigo")
            traducirCodigo(estado)
        elif opcion == "6":
            registrarEvento(estado.bitacora, "Uso de la opcion 6: generar CSV")
            generarReporteCsv(estado)
        elif opcion == "7":
            registrarEvento(estado.bitacora, "Uso de la opcion 7: generar HTML")
            generarReporteHtml(estado)
        elif opcion == "8":
            registrarEvento(estado.bitacora, "Uso de la opcion 8: submenu de bitacora")
            submenuBitacora(estado)
        elif opcion == "9":
            registrarEvento(estado.bitacora, "Salida del programa")
            print("Programa finalizado.")
            break
        else:
            print("Opcion invalida. Intente de nuevo.")


if __name__ == "__main__":
    ejecutarMenu()