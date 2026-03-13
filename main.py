"""
FastAPI application for managing population survey data (encuesta-api).

This module implements a REST API for CRUD operations on surveys with:
- Custom validation error handling
- Asynchronous endpoints
- Logging decorator
- In-memory survey storage
"""

import logging
from datetime import datetime
from functools import wraps
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from models import (
    EncuestaCompleta,
    Encuestado,
    RespuestaEncuesta,
    EstadisticasEncuestas,
    ErrorResponse
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# In-memory survey storage
encuestas_storage: dict[int, EncuestaCompleta] = {}
next_survey_id: int = 1

# FastAPI application instance
app = FastAPI(
    title="Encuesta API",
    description="REST API para gestionar datos de encuestas poblacionales en Colombia",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


# ============================================================================
# CUSTOM DECORATOR: @log_request
# ============================================================================

def log_request(func):
    """
    Custom decorator that logs HTTP requests.
    
    HOW IT RELATES TO FASTAPI ROUTE DECORATORS:
    
    Route decorators like @app.get(), @app.post() are used by FastAPI to register
    endpoints and map HTTP methods to handler functions. This @log_request decorator
    is a function wrapper that adds cross-cutting functionality (logging) to the
    route handler without modifying the original function's code.
    
    In FastAPI, decorators are stacked:
        @app.get("/path")           # FastAPI's decorator: registers the route
        @log_request                # Our decorator: wraps the function to add logging
        def my_endpoint():
    
    When a request arrives, FastAPI processes it and calls our wrapper function,
    which logs the request details, then calls the original handler function.
    This is an example of the Decorator design pattern.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        timestamp = datetime.now().isoformat()
        # Log the request details
        logger.info(f"[{timestamp}] Request to {func.__name__}")
        return func(*args, **kwargs)
    return wrapper


# ============================================================================
# CUSTOM ERROR HANDLER
# ============================================================================

@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    """
    Custom error handler for Pydantic validation errors.
    
    This handler:
    - Returns structured JSON with error details
    - Lists invalid fields with reasons
    - Includes human-readable messages
    - Logs validation attempts to console
    """
    details = []
    
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"][1:])
        details.append({
            "field": field,
            "value": error.get("input", "N/A"),
            "reason": error.get("msg", "Validation failed")
        })
        logger.warning(
            f"Validation error in field '{field}': {error.get('msg')} "
            f"(value: {error.get('input', 'N/A')})"
        )
    
    error_response = ErrorResponse(
        error="ValidationError",
        message="Invalid survey data provided",
        details=details
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump()
    )


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.post(
    "/encuestas/",
    response_model=EncuestaCompleta,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una nueva encuesta",
    description="Crea una nueva encuesta completa con información del encuestado y respuestas"
)
@log_request
def crear_encuesta(encuesta: EncuestaCompleta) -> EncuestaCompleta:
    """
    Create a new survey record.
    
    The survey will be assigned a unique ID and stored in the in-memory database.
    
    Returns:
        EncuestaCompleta: The created survey with assigned ID
    """
    global next_survey_id
    
    encuesta.id = next_survey_id
    encuestas_storage[next_survey_id] = encuesta
    next_survey_id += 1
    
    logger.info(f"Survey created with ID: {encuesta.id}")
    return encuesta


@app.get(
    "/encuestas/",
    response_model=List[EncuestaCompleta],
    status_code=status.HTTP_200_OK,
    summary="Obtener todas las encuestas",
    description="Retorna la lista de todas las encuestas registradas en el sistema"
)
@log_request
def obtener_todas_encuestas() -> List[EncuestaCompleta]:
    """
    Retrieve all surveys.
    
    Returns:
        List[EncuestaCompleta]: List of all surveys in the system
    """
    logger.info(f"Retrieved all {len(encuestas_storage)} surveys")
    return list(encuestas_storage.values())


@app.get(
    "/encuestas/{survey_id}",
    response_model=EncuestaCompleta,
    status_code=status.HTTP_200_OK,
    summary="Obtener una encuesta por ID",
    description="Retorna los detalles de una encuesta específica por su ID"
)
@log_request
def obtener_encuesta_por_id(survey_id: int) -> EncuestaCompleta:
    """
    Retrieve a specific survey by ID.
    
    Args:
        survey_id: The ID of the survey to retrieve
        
    Returns:
        EncuestaCompleta: The requested survey
        
    Raises:
        HTTPException: If survey not found (404)
    """
    if survey_id not in encuestas_storage:
        logger.warning(f"Survey not found with ID: {survey_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Encuesta con ID {survey_id} no encontrada"
        )
    
    logger.info(f"Retrieved survey with ID: {survey_id}")
    return encuestas_storage[survey_id]


@app.put(
    "/encuestas/{survey_id}",
    response_model=EncuestaCompleta,
    status_code=status.HTTP_200_OK,
    summary="Actualizar una encuesta",
    description="Actualiza los datos de una encuesta existente"
)
@log_request
def actualizar_encuesta(survey_id: int, encuesta_actualizada: EncuestaCompleta) -> EncuestaCompleta:
    """
    Update an existing survey.
    
    Args:
        survey_id: The ID of the survey to update
        encuesta_actualizada: The updated survey data
        
    Returns:
        EncuestaCompleta: The updated survey
        
    Raises:
        HTTPException: If survey not found (404)
    """
    if survey_id not in encuestas_storage:
        logger.warning(f"Cannot update: Survey not found with ID: {survey_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Encuesta con ID {survey_id} no encontrada"
        )
    
    encuesta_actualizada.id = survey_id
    encuestas_storage[survey_id] = encuesta_actualizada
    
    logger.info(f"Survey updated with ID: {survey_id}")
    return encuesta_actualizada


@app.delete(
    "/encuestas/{survey_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar una encuesta",
    description="Elimina una encuesta del sistema"
)
@log_request
def eliminar_encuesta(survey_id: int) -> None:
    """
    Delete a survey.
    
    Args:
        survey_id: The ID of the survey to delete
        
    Raises:
        HTTPException: If survey not found (404)
    """
    if survey_id not in encuestas_storage:
        logger.warning(f"Cannot delete: Survey not found with ID: {survey_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Encuesta con ID {survey_id} no encontrada"
        )
    
    del encuestas_storage[survey_id]
    logger.info(f"Survey deleted with ID: {survey_id}")


# ============================================================================
# ASYNCHRONOUS ENDPOINT (RF5)
# ============================================================================

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
    Retrieve survey statistics asynchronously.
    
    ASYNC/AWAIT IN FASTAPI:
    
    This endpoint uses 'async def' instead of regular 'def'. Here's what that means:
    
    1. DIFFERENCE BETWEEN def AND async def:
       - 'def': Synchronous function that blocks until complete
       - 'async def': Asynchronous function that can be paused and resumed,
         allowing other tasks to run while waiting for I/O operations
    
    2. WHAT async/await MEANS:
       - 'async': Declares that a function can be awaited and may contain
         'await' expressions
       - 'await': Pauses the function, releases control to the event loop,
         and resumes when the awaited operation completes
       - This is useful for I/O-bound operations (database queries, API calls, etc.)
    
    3. RELATIONSHIP WITH ASGI:
       - FastAPI runs on ASGI (Asynchronous Server Gateway Interface)
       - ASGI handles multiple requests concurrently using an event loop
       - When an async endpoint is awaited, it yields control back to the event loop
       - The event loop can then process other requests while the first one waits
       - This dramatically improves server throughput under high concurrency
    
    WHEN TO USE ASYNC:
    - For I/O operations: database calls, HTTP requests, file operations
    - NOT needed for pure CPU-intensive calculations
    
    In this case, we use 'async' for consistency and because in a real application,
    these statistics would come from a database query, which would be async.
    """
    if not encuestas_storage:
        return EstadisticasEncuestas(
            total_encuestas=0,
            edad_promedio=0.0,
            distribucion_por_estrato={}
        )
    
    surveys = list(encuestas_storage.values())
    total = len(surveys)
    
    # Calculate average age
    edades = [s.encuestado.edad for s in surveys]
    edad_promedio = sum(edades) / len(edades) if edades else 0.0
    
    # Calculate distribution by stratum
    distribucion = {}
    for survey in surveys:
        estrato_str = str(survey.encuestado.estrato)
        distribucion[estrato_str] = distribucion.get(estrato_str, 0) + 1
    
    logger.info(
        f"Statistics retrieved: {total} surveys, avg age: {edad_promedio:.2f}, "
        f"strata distribution: {distribucion}"
    )
    
    return EstadisticasEncuestas(
        total_encuestas=total,
        edad_promedio=edad_promedio,
        distribucion_por_estrato=distribucion
    )


@app.get(
    "/",
    summary="Health check",
    description="Endpoint para verificar que la API está en funcionamiento"
)
@log_request
def raiz():
    """
    Health check endpoint.
    
    Returns:
        dict: A simple message indicating the API is running
    """
    return {
        "mensaje": "Bienvenido a Encuesta API",
        "documentacion": "Accede a /docs para ver la documentación completa"
    }


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting Encuesta API server...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
