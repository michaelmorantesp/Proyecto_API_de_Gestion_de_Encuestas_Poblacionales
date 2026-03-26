"""
main.py — Punto de entrada de la aplicación Encuesta API.

Aquí se crean la app FastAPI, el decorador de logging, el manejador de errores
y todos los endpoints (rutas) del sistema.
"""

# ============================================================================
# IMPORTACIONES
# ============================================================================

import logging                          # Módulo estándar de Python para registrar mensajes en consola
from datetime import datetime           # Para obtener la fecha y hora actuales en el decorador
from functools import wraps             # Preserva el nombre y docstring de la función original al decorarla
from typing import List, Optional       # Tipos genéricos para anotaciones: listas y valores opcionales

# FastAPI: framework principal para construir la API REST
from fastapi import FastAPI, HTTPException, Request, status

# RequestValidationError: excepción que lanza FastAPI cuando el body de una petición
# no cumple el esquema Pydantic definido en el endpoint.
# IMPORTANTE: es distinta a pydantic.ValidationError (que Pydantic lanza internamente).
# Esta es la que hay que capturar para personalizar las respuestas HTTP 422.
from fastapi.exceptions import RequestValidationError

# JSONResponse: permite construir manualmente una respuesta HTTP con un JSON y un status code
from fastapi.responses import JSONResponse

# Importamos los modelos que definimos en models.py
from models import (
    EncuestaCompleta,       # Modelo principal con id + encuestado + respuestas
    Encuestado,             # Datos demográficos del encuestado
    RespuestaEncuesta,      # Una respuesta individual de la encuesta
    EstadisticasEncuestas,  # Modelo de salida para el endpoint de estadísticas
    ErrorResponse           # Modelo de salida para errores de validación (HTTP 422)
)

from fastapi.middleware.cors import CORSMiddleware #Para conexión desde la api a html

# ============================================================================
# CONFIGURACIÓN DEL SISTEMA DE LOGGING
# ============================================================================

# basicConfig configura el formato global de los mensajes de log
logging.basicConfig(
    level=logging.INFO,                             # Mostrar mensajes de nivel INFO o superior
    format='%(asctime)s - %(levelname)s - %(message)s'  # Formato: fecha - nivel - mensaje
)

# Creamos el logger específico para este módulo (__name__ = "main")
logger = logging.getLogger(__name__)


# ============================================================================
# ALMACENAMIENTO EN MEMORIA
# ============================================================================

# Diccionario que actúa como base de datos temporal.
# La clave es el ID (int) y el valor es la encuesta completa (EncuestaCompleta).
# Los datos se pierden al reiniciar el servidor (es solo para demostración).
encuestas_storage: dict[int, EncuestaCompleta] = {}

# Contador global que se incrementa con cada encuesta creada.
# Garantiza que cada encuesta recibe un ID único y secuencial (1, 2, 3...).
next_survey_id: int = 1


# ============================================================================
# INSTANCIA DE LA APLICACIÓN FASTAPI
# ============================================================================

# FastAPI() crea la aplicación. Los parámetros configuran la documentación automática
# que se genera en /docs (Swagger UI) y /redoc (ReDoc).
app = FastAPI(
    title="Encuesta API",
    description="REST API para gestionar datos de encuestas poblacionales en Colombia",
    version="1.0.0",
    docs_url="/docs",       # Ruta donde estará disponible Swagger UI
    redoc_url="/redoc"      # Ruta donde estará disponible ReDoc
)

## para que funcione en html
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# DECORADOR PERSONALIZADO: @log_request
# ============================================================================

def log_request(func):
    """
    Decorador que registra en consola cada petición procesada.

    Un decorador es una función que recibe otra función como argumento,
    la envuelve con lógica adicional, y devuelve la función modificada.

    RELACIÓN CON LOS DECORADORES DE FASTAPI:
    Los decoradores de ruta como @app.get() o @app.post() registran los endpoints
    en el sistema de rutas de FastAPI. Nuestro @log_request es diferente: agrega
    funcionalidad transversal (logging) sin modificar el código del endpoint.
    Se apilan así:

        @app.post("/encuestas/")   ← FastAPI registra la ruta
        @log_request               ← Nuestro decorador envuelve la función
        async def crear_encuesta():
            ...

    Cuando llega una petición, FastAPI llama al wrapper, que loguea y luego
    delega al handler original con 'await func(...)'.
    """

    # @wraps(func) copia el nombre, docstring y metadatos de 'func' al wrapper.
    # Sin esto, todos los endpoints aparecerían con el nombre "wrapper" en los logs.
    @wraps(func)

    # El wrapper DEBE ser async def porque FastAPI llama a los endpoints con 'await'.
    # Si fuera 'def' (síncrono), Python devolvería una corrutina sin ejecutar
    # en lugar del resultado real, causando un TypeError en runtime.
    async def wrapper(*args, **kwargs):

        # Capturamos el momento exacto en que llegó la petición
        timestamp = datetime.now().isoformat()

        # Registramos en consola: la hora y el nombre de la función que se va a ejecutar
        logger.info(f"[{timestamp}] Petición a: {func.__name__}")

        # 'await' delega la ejecución al handler original y espera su resultado.
        # Sin 'await', la función async devolvería un objeto corrutina, no el resultado.
        return await func(*args, **kwargs)

    # Devolvemos el wrapper para reemplazar la función original
    return wrapper


# ============================================================================
# MANEJADOR PERSONALIZADO DE ERRORES DE VALIDACIÓN (HTTP 422)
# ============================================================================

# @app.exception_handler registra esta función como el manejador oficial
# para la excepción RequestValidationError en toda la aplicación.
#
# DIFERENCIA CLAVE entre las dos excepciones de validación:
#   - pydantic.ValidationError     → Pydantic la lanza cuando construyes un modelo en código Python
#   - RequestValidationError       → FastAPI la lanza cuando el body de una petición HTTP
#                                    no cumple el esquema del modelo del endpoint
# Debemos capturar RequestValidationError para interceptar los errores que llegan
# desde el cliente y devolver nuestra respuesta JSON personalizada.
@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """
    Manejador personalizado para errores de validación de peticiones HTTP (422).

    Se ejecuta automáticamente cada vez que FastAPI detecta que el body
    de una petición no cumple las reglas de validación de los modelos Pydantic.
    """

    # Lista donde acumularemos el detalle de cada campo inválido
    details = []

    # exc.errors() devuelve una lista de diccionarios, uno por cada campo que falló.
    # Cada diccionario tiene: 'loc' (ubicación del campo), 'msg' (mensaje de error), 'input' (valor recibido)
    for error in exc.errors():

        # 'loc' es una tupla como ('body', 'encuestado', 'edad').
        # Saltamos el primer elemento ('body') para mostrar solo la ruta del campo.
        # ".".join(...) convierte la tupla en un string legible: "encuestado.edad"
        field = ".".join(str(loc) for loc in error["loc"][1:])

        # Construimos el objeto de detalle para este campo inválido
        details.append({
            "field": field,                             # Ruta del campo inválido (ej: "encuestado.edad")
            "value": error.get("input", "N/A"),         # Valor que envió el cliente
            "reason": error.get("msg", "Validation failed")  # Razón del fallo
        })

        # Registramos el error en consola para auditoría
        logger.warning(
            f"Error de validación en '{field}': {error.get('msg')} "
            f"(valor recibido: {error.get('input', 'N/A')})"
        )

    # Construimos la respuesta de error usando nuestro modelo ErrorResponse
    error_response = ErrorResponse(
        error="ValidationError",
        message="Invalid survey data provided",
        details=details
    )

    # Devolvemos una respuesta JSON con status 422 y el cuerpo estructurado.
    # model_dump() convierte el modelo Pydantic a un diccionario Python serializable.
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,   # Código 422
        content=error_response.model_dump()                  # Cuerpo de la respuesta
    )


# ============================================================================
# ENDPOINTS — OPERACIONES CRUD
# ============================================================================

# POST /encuestas/ — Crear una nueva encuesta
# response_model: FastAPI usará EncuestaCompleta para serializar y validar la respuesta
# status_code: 201 Created es el código correcto para recursos recién creados
# summary y description aparecen en Swagger UI (/docs)
@app.post(
    "/encuestas/",
    response_model=EncuestaCompleta,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una nueva encuesta",
    description="Crea una nueva encuesta completa con información del encuestado y respuestas"
)
@log_request  # Aplicamos nuestro decorador para registrar la petición en logs
async def crear_encuesta(encuesta: EncuestaCompleta) -> EncuestaCompleta:
    """
    Crea un nuevo registro de encuesta en el sistema.

    FastAPI inyecta automáticamente el body de la petición en el parámetro 'encuesta',
    lo deserializa como EncuestaCompleta y ejecuta todas las validaciones Pydantic.
    Si alguna validación falla, FastAPI lanza RequestValidationError antes de llegar aquí.
    """

    # 'global' indica que vamos a modificar la variable global next_survey_id,
    # no a crear una variable local con el mismo nombre.
    global next_survey_id

    # Sobreescribimos el id que envió el cliente con el id del servidor.
    # El servidor siempre decide el ID; el cliente no debe controlarlo.
    encuesta.id = next_survey_id

    # Guardamos la encuesta en el diccionario usando su ID como clave
    encuestas_storage[next_survey_id] = encuesta

    # Incrementamos el contador para que la próxima encuesta reciba el siguiente ID
    next_survey_id += 1

    # Registramos en logs la creación exitosa
    logger.info(f"Encuesta creada con ID: {encuesta.id}")

    # Devolvemos la encuesta con su ID asignado. FastAPI la serializa a JSON automáticamente.
    return encuesta


# GET /encuestas/ — Listar todas las encuestas
@app.get(
    "/encuestas/",
    response_model=List[EncuestaCompleta],   # La respuesta es una lista de encuestas
    status_code=status.HTTP_200_OK,
    summary="Obtener todas las encuestas",
    description="Retorna la lista de todas las encuestas registradas en el sistema"
)
@log_request
async def obtener_todas_encuestas() -> List[EncuestaCompleta]:
    """
    Retorna todas las encuestas almacenadas en memoria.
    """

    logger.info(f"Se retornan {len(encuestas_storage)} encuestas")

    # .values() devuelve todos los valores del diccionario (las encuestas).
    # list() los convierte a una lista para que FastAPI pueda serializarla.
    return list(encuestas_storage.values())


# GET /encuestas/estadisticas/ — Estadísticas agregadas
#
# IMPORTANTE: esta ruta DEBE registrarse ANTES que /encuestas/{survey_id}.
# FastAPI evalúa las rutas en el orden en que se registran con los decoradores.
# Si /{survey_id} se registrara primero, una petición a /encuestas/estadisticas/
# haría que FastAPI intente convertir el string "estadisticas" al tipo int
# declarado en survey_id: int → falla con HTTP 422.
# Regla: rutas con segmentos literales van siempre antes que rutas con parámetros.
@app.get(
    "/encuestas/estadisticas/",
    response_model=EstadisticasEncuestas,
    status_code=status.HTTP_200_OK,
    summary="Obtener estadísticas de encuestas",
    description="Retorna estadísticas calculadas de todas las encuestas: "
                "total de encuestas, edad promedio y distribución por estrato"
)
async def obtener_estadisticas() -> EstadisticasEncuestas:
    """
    Calcula y retorna estadísticas agregadas de todas las encuestas.

    Este endpoint es 'async def' (asíncrono).

    DIFERENCIA ENTRE def Y async def EN FASTAPI:
    - 'def': función síncrona. El servidor espera (bloquea) hasta que termina.
    - 'async def': función asíncrona. Puede pausarse en puntos 'await' y ceder
      el control al event loop para atender otras peticiones mientras espera.

    CUÁNDO ES INDISPENSABLE USAR async/await:
    En producción, este endpoint consultaría una base de datos real. Con un driver
    asíncrono (asyncpg, motor), la consulta sería 'await db.fetch(...)'.
    Sin async, el servidor bloquearía el hilo durante cada consulta a BD,
    reduciendo drásticamente la capacidad de atender peticiones concurrentes.

    RELACIÓN CON ASGI:
    FastAPI corre sobre ASGI (Asynchronous Server Gateway Interface), que gestiona
    un event loop capaz de manejar miles de conexiones con un solo proceso.
    Los endpoints 'async def' se integran nativamente con ese event loop.
    Los endpoints 'def' corren en un thread pool para no bloquear el loop.
    ASGI es la base que hace posible la concurrencia de FastAPI.
    """

    # Si no hay encuestas, devolvemos estadísticas en cero para evitar división por cero
    if not encuestas_storage:
        return EstadisticasEncuestas(
            total_encuestas=0,
            edad_promedio=0.0,
            distribucion_por_estrato={}
        )

    # Convertimos el diccionario a lista para poder iterar
    surveys = list(encuestas_storage.values())

    # Contamos el total de encuestas
    total = len(surveys)

    # Extraemos la edad de cada encuestado con una lista por comprensión
    edades = [s.encuestado.edad for s in surveys]

    # Calculamos el promedio: suma de edades / cantidad de encuestas
    edad_promedio = sum(edades) / len(edades) if edades else 0.0

    # Calculamos cuántas encuestas hay por cada estrato
    distribucion = {}
    for survey in surveys:
        # Convertimos el estrato a string para usarlo como clave del diccionario
        estrato_str = str(survey.encuestado.estrato)
        # .get(clave, 0) retorna 0 si la clave no existe aún, evitando KeyError
        distribucion[estrato_str] = distribucion.get(estrato_str, 0) + 1

    logger.info(
        f"Estadísticas calculadas: {total} encuestas, "
        f"edad promedio {edad_promedio:.2f}, distribución {distribucion}"
    )

    # Construimos y devolvemos el modelo de estadísticas
    return EstadisticasEncuestas(
        total_encuestas=total,
        edad_promedio=edad_promedio,
        distribucion_por_estrato=distribucion
    )


# GET /encuestas/{survey_id} — Obtener una encuesta por ID
# {survey_id} es un parámetro de ruta: FastAPI lo extrae de la URL y lo convierte a int
@app.get(
    "/encuestas/{survey_id}",
    response_model=EncuestaCompleta,
    status_code=status.HTTP_200_OK,
    summary="Obtener una encuesta por ID",
    description="Retorna los detalles de una encuesta específica por su ID"
)
@log_request
async def obtener_encuesta_por_id(survey_id: int) -> EncuestaCompleta:
    """
    Busca y retorna una encuesta específica usando su ID.
    Si no existe, retorna HTTP 404.
    """

    # Verificamos si el ID existe como clave en el diccionario
    if survey_id not in encuestas_storage:
        logger.warning(f"Encuesta no encontrada con ID: {survey_id}")

        # HTTPException interrumpe el endpoint y devuelve una respuesta de error.
        # status_code=404 indica "recurso no encontrado".
        # 'detail' es el mensaje que recibirá el cliente en el campo "detail" del JSON.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Encuesta con ID {survey_id} no encontrada"
        )

    logger.info(f"Encuesta recuperada con ID: {survey_id}")

    # Accedemos directamente al diccionario con el ID como clave
    return encuestas_storage[survey_id]


# PUT /encuestas/{survey_id} — Actualizar una encuesta existente
# PUT reemplaza el recurso completo (a diferencia de PATCH que solo actualiza campos específicos)
@app.put(
    "/encuestas/{survey_id}",
    response_model=EncuestaCompleta,
    status_code=status.HTTP_200_OK,
    summary="Actualizar una encuesta",
    description="Actualiza los datos de una encuesta existente"
)
@log_request
async def actualizar_encuesta(survey_id: int, encuesta_actualizada: EncuestaCompleta) -> EncuestaCompleta:
    """
    Reemplaza los datos de una encuesta existente con los nuevos datos del body.
    Si no existe, retorna HTTP 404.
    """

    # Verificamos que la encuesta a actualizar existe antes de modificarla
    if survey_id not in encuestas_storage:
        logger.warning(f"No se puede actualizar: ID {survey_id} no encontrado")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Encuesta con ID {survey_id} no encontrada"
        )

    # Forzamos que el ID de la encuesta sea el de la URL, ignorando el que envió el cliente.
    # Esto evita inconsistencias si el cliente envía un ID diferente en el body.
    encuesta_actualizada.id = survey_id

    # Sobreescribimos la encuesta en el diccionario con los nuevos datos
    encuestas_storage[survey_id] = encuesta_actualizada

    logger.info(f"Encuesta actualizada con ID: {survey_id}")

    return encuesta_actualizada


# DELETE /encuestas/{survey_id} — Eliminar una encuesta
# 204 No Content: la operación fue exitosa pero no hay cuerpo en la respuesta
@app.delete(
    "/encuestas/{survey_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar una encuesta",
    description="Elimina una encuesta del sistema"
)
@log_request
async def eliminar_encuesta(survey_id: int) -> None:
    """
    Elimina permanentemente una encuesta del almacenamiento en memoria.
    Si no existe, retorna HTTP 404.
    """

    # Verificamos que existe antes de intentar eliminarla
    if survey_id not in encuestas_storage:
        logger.warning(f"No se puede eliminar: ID {survey_id} no encontrado")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Encuesta con ID {survey_id} no encontrada"
        )

    # 'del' elimina la clave y su valor del diccionario
    del encuestas_storage[survey_id]

    logger.info(f"Encuesta eliminada con ID: {survey_id}")

    # No retornamos nada (None) porque el status 204 No Content no lleva body


# GET / — Health check (verificación de que la API está viva)
@app.get(
    "/",
    summary="Health check",
    description="Endpoint para verificar que la API está en funcionamiento"
)
@log_request
async def raiz():
    """
    Retorna un mensaje de bienvenida y la ruta de la documentación.
    Útil para verificar rápidamente que el servidor está corriendo.
    """
    return {
        "mensaje": "Bienvenido a Encuesta API",
        "documentacion": "Accede a /docs para ver la documentación completa"
    }


# ============================================================================
# PUNTO DE ENTRADA PARA EJECUTAR EL SERVIDOR DIRECTAMENTE
# ================git status============================================================

# Este bloque solo se ejecuta si corremos el archivo directamente con: python main.py
# Si el archivo es importado por otro módulo (como pytest), este bloque se omite.
if __name__ == "__main__":
    import uvicorn  # Servidor ASGI que sirve la aplicación FastAPI

    logger.info("Iniciando servidor Encuesta API...")

    # uvicorn.run inicia el servidor web ASGI.
    # 'app': la instancia de FastAPI que debe servir
    # 'host': "0.0.0.0" acepta conexiones desde cualquier dirección de red
    # 'port': puerto 8000 (la API estará en http://localhost:8000)
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
