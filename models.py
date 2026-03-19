"""
models.py — Modelos Pydantic para el proyecto encuesta-api.

Pydantic es una librería de validación de datos que usa las anotaciones de tipo
de Python para definir la estructura y las reglas de los datos.
Cuando se crea una instancia de un modelo, Pydantic valida automáticamente
cada campo y lanza ValidationError si algo no cumple las reglas.

Este módulo define 5 modelos organizados jerárquicamente:
  Encuestado           → datos demográficos del encuestado
  RespuestaEncuesta    → una respuesta individual (anidada en EncuestaCompleta)
  EncuestaCompleta     → contenedor principal: Encuestado + List[RespuestaEncuesta]
  EstadisticasEncuestas → modelo de salida para el endpoint de estadísticas
  ErrorResponse        → modelo de salida para errores de validación HTTP 422
"""

# List: para declarar campos que son listas (ej: List[RespuestaEncuesta])
# Optional: para campos que pueden ser None (ej: Optional[str] = None)
# Union: para campos que aceptan múltiples tipos (ej: Union[int, float, str])
from typing import List, Optional, Union

# BaseModel: clase base de Pydantic. Todos nuestros modelos heredan de ella.
# ConfigDict: permite configurar el comportamiento del modelo (ej: ejemplos JSON)
# field_validator: decorador para definir validaciones personalizadas por campo
from pydantic import BaseModel, ConfigDict, field_validator

# Importamos las funciones de validación definidas en validators.py.
# Separar la lógica de validación en un módulo aparte sigue el principio
# de responsabilidad única: models.py define estructura, validators.py define reglas.
# NOTA: DEPARTAMENTOS_COLOMBIANOS fue removido de este import porque
# no se usa directamente en models.py — solo se usa dentro de validators.py.
from validators import (
    validar_edad,           # Valida que edad esté entre 0 y 120
    validar_estrato,        # Valida que estrato esté entre 1 y 6
    validar_departamento,   # Valida que el departamento sea colombiano válido
    validar_respuesta       # Valida formato de respuesta (Likert, porcentaje o texto)
)


# ============================================================================
# MODELO 1: Encuestado
# ============================================================================

class Encuestado(BaseModel):
    """
    Modelo que representa los datos demográficos de un encuestado.

    Hereda de BaseModel (Pydantic), lo que significa que al instanciar
    esta clase, Pydantic valida automáticamente todos los campos.
    """

    # Campos del modelo con sus tipos declarados (Type Hinting)
    # Pydantic usa estos tipos para hacer coerción y validación automática
    nombre: str         # String requerido (no puede ser None ni omitirse)
    edad: int           # Entero requerido
    estrato: int        # Entero requerido
    departamento: str   # String requerido

    # model_config permite personalizar el comportamiento del modelo.
    # json_schema_extra agrega información adicional al esquema JSON generado,
    # que FastAPI usa para mostrar ejemplos en Swagger UI (/docs) y ReDoc (/redoc).
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "nombre": "Juan Pérez García",
                "edad": 35,
                "estrato": 3,
                "departamento": "Cundinamarca"
            }
        }
    )

    # -----------------------------------------------------------------------
    # VALIDADORES DE CAMPO con @field_validator
    # -----------------------------------------------------------------------
    # @field_validator define una función que Pydantic ejecuta automáticamente
    # al crear o validar el modelo.
    #
    # mode="after": el validador se ejecuta DESPUÉS de que Pydantic convirtió
    # el valor al tipo declarado (int, str, etc.). Útil cuando necesitamos
    # el valor ya tipado para comparar rangos numéricos.
    #
    # mode="before": el validador se ejecuta ANTES de la coerción de tipos,
    # recibiendo el valor crudo tal como llegó del cliente. Útil para
    # normalizar strings (strip) antes de cualquier otra validación.
    #
    # @classmethod es requerido por Pydantic v2 para todos los field_validators.

    @field_validator("edad", mode="after")
    @classmethod
    def validate_edad(cls, v: int) -> int:
        """
        Valida que la edad esté entre 0 y 120 (restricción biológica).
        Se ejecuta después de la coerción de tipos: 'v' ya es un int garantizado.
        Delega la lógica a validar_edad() en validators.py.
        """
        return validar_edad(v)

    @field_validator("estrato", mode="after")
    @classmethod
    def validate_estrato(cls, v: int) -> int:
        """
        Valida que el estrato sea un entero entre 1 y 6 (contexto colombiano).
        Se ejecuta después de la coerción: 'v' ya es int.
        """
        return validar_estrato(v)

    @field_validator("departamento", mode="before")
    @classmethod
    def validate_departamento(cls, v: str) -> str:
        """
        Valida que el departamento esté en la lista oficial colombiana.
        Se ejecuta ANTES de la coerción (mode='before') para poder aplicar
        .strip() al string crudo antes de validarlo.
        Así "  Antioquia  " (con espacios) pasa la validación correctamente.
        """
        if isinstance(v, str):
            v = v.strip()   # Elimina espacios al inicio y al final del string
        return validar_departamento(v)

    @field_validator("nombre", mode="before")
    @classmethod
    def validate_nombre(cls, v: str) -> str:
        """
        Normaliza el nombre eliminando espacios extra al inicio y al final.
        Se ejecuta antes de la coerción para recibir el string crudo.
        """
        if isinstance(v, str):
            v = v.strip()
        return v


# ============================================================================
# MODELO 2: RespuestaEncuesta
# ============================================================================

class RespuestaEncuesta(BaseModel):
    """
    Modelo que representa una respuesta individual a una pregunta de la encuesta.

    El campo 'respuesta' usa Union[int, float, str] para soportar tres formatos:
      - int   → escala Likert (1-5) para preguntas de satisfacción
      - float → porcentaje (0.0-100.0) para preguntas de cobertura
      - str   → texto libre para preguntas abiertas
    """

    pregunta: str                       # Texto de la pregunta (requerido)
    respuesta: Union[int, float, str]   # Respuesta polimórfica (requerido)

    # Optional[str] = None significa que el campo puede ser:
    #   - Un string si el encuestado quiere agregar comentario
    #   - None si no agrega comentario (valor por defecto)
    comentario: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "pregunta": "¿Qué tan satisfecho está con los servicios de salud?",
                "respuesta": 4,
                "comentario": "Buen servicio pero largas esperas"
            }
        }
    )

    @field_validator("respuesta", mode="after")
    @classmethod
    def validate_respuesta(cls, v: Union[int, float, str]) -> Union[int, float, str]:
        """
        Valida el formato de la respuesta según su tipo resuelto por Pydantic.
        mode='after' garantiza que el tipo ya fue determinado dentro del Union
        antes de que este validador se ejecute.
        """
        return validar_respuesta(v)

    @field_validator("pregunta", mode="before")
    @classmethod
    def validate_pregunta(cls, v: str) -> str:
        """
        Normaliza el texto de la pregunta eliminando espacios extra.
        mode='before' para limpiar el string crudo antes de validarlo.
        """
        if isinstance(v, str):
            v = v.strip()
        return v


# ============================================================================
# MODELO 3: EncuestaCompleta
# ============================================================================

class EncuestaCompleta(BaseModel):
    """
    Modelo contenedor que representa una encuesta completa.

    Es el modelo principal de la API: agrupa el encuestado con todas
    sus respuestas bajo un ID único asignado por el servidor.

    MODELOS ANIDADOS:
    Pydantic soporta modelos anidados directamente como tipos de campo.
    Al validar EncuestaCompleta, Pydantic valida recursivamente Encuestado
    y cada RespuestaEncuesta dentro de la lista.

    List[RespuestaEncuesta]: lista tipada — todos los elementos deben ser
    instancias válidas de RespuestaEncuesta.
    """

    id: int                                 # ID asignado por el servidor (int requerido)
    encuestado: Encuestado                  # Modelo anidado: datos del encuestado
    respuestas: List[RespuestaEncuesta]     # Lista de modelos anidados: respuestas

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "encuestado": {
                    "nombre": "María López",
                    "edad": 42,
                    "estrato": 2,
                    "departamento": "Antioquia"
                },
                "respuestas": [
                    {
                        "pregunta": "¿Acceso a servicios de salud?",
                        "respuesta": 5,
                        "comentario": "Excelente cobertura"
                    },
                    {
                        "pregunta": "¿Nivel de educación completada? (0-100%)",
                        "respuesta": 85.5,
                        "comentario": None
                    }
                ]
            }
        }
    )


# ============================================================================
# MODELO 4: EstadisticasEncuestas
# ============================================================================

class EstadisticasEncuestas(BaseModel):
    """
    Modelo de salida para el endpoint GET /encuestas/estadisticas/.

    Solo se usa como modelo de respuesta (output), nunca como entrada.
    Define la estructura del JSON que el servidor devuelve al cliente.
    """

    total_encuestas: int            # Cantidad total de encuestas registradas
    edad_promedio: float            # Promedio de edad de todos los encuestados
    distribucion_por_estrato: dict  # Diccionario {estrato: cantidad} ej: {"1": 2, "3": 5}

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_encuestas": 5,
                "edad_promedio": 38.5,
                "distribucion_por_estrato": {
                    "1": 1,
                    "2": 2,
                    "3": 2
                }
            }
        }
    )


# ============================================================================
# MODELO 5: ErrorResponse
# ============================================================================

class ErrorResponse(BaseModel):
    """
    Modelo de salida para las respuestas de error de validación (HTTP 422).

    Se usa en el manejador personalizado de RequestValidationError en main.py
    para estructurar el JSON que recibe el cliente cuando envía datos inválidos.

    Tener un modelo para los errores garantiza que la estructura sea consistente
    en toda la API y que Pydantic valide también las respuestas de error.
    """

    error: str          # Tipo de error (ej: "ValidationError")
    message: str        # Mensaje general legible para el consumidor de la API
    details: List[dict] # Lista de errores por campo: [{field, value, reason}, ...]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "ValidationError",
                "message": "Invalid survey data provided",
                "details": [
                    {
                        "field": "edad",
                        "value": 150,
                        "reason": "edad must be between 0 and 120"
                    }
                ]
            }
        }
    )
