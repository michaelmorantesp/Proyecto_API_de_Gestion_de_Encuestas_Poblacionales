"""
Pydantic models for the encuesta-api project.

This module defines the data structures for managing population survey data
with proper type hints and configuration for JSON schema examples.
"""

from typing import List, Optional, Union
from pydantic import BaseModel, ConfigDict, field_validator
from validators import (
    validar_edad,
    validar_estrato,
    validar_departamento,
    validar_respuesta,
    DEPARTAMENTOS_COLOMBIANOS
)


class Encuestado(BaseModel):
    """
    Model representing a survey respondent (encuestado).
    
    Attributes:
        nombre: Full name of the respondent
        edad: Age (must be between 0 and 120)
        estrato: Socioeconomic stratum (must be between 1 and 6)
        departamento: Colombian department where respondent lives
    """
    nombre: str
    edad: int
    estrato: int
    departamento: str

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

    @field_validator("edad", mode="after")
    @classmethod
    def validate_edad(cls, v: int) -> int:
        """
        Validate that edad is between 0 and 120.
        Uses mode='after' to validate after type coercion.
        """
        return validar_edad(v)

    @field_validator("estrato", mode="after")
    @classmethod
    def validate_estrato(cls, v: int) -> int:
        """
        Validate that estrato is between 1 and 6.
        Uses mode='after' to validate after type coercion.
        """
        return validar_estrato(v)

    @field_validator("departamento", mode="before")
    @classmethod
    def validate_departamento(cls, v: str) -> str:
        """
        Validate that departamento is in the valid Colombian departments list.
        Uses mode='before' to validate and potentially transform raw input.
        This allows the validator to strip whitespace from user input.
        """
        if isinstance(v, str):
            v = v.strip()
        return validar_departamento(v)

    @field_validator("nombre", mode="before")
    @classmethod
    def validate_nombre(cls, v: str) -> str:
        """
        Validate and clean the nombre field.
        Uses mode='before' to normalize the input by stripping whitespace.
        """
        if isinstance(v, str):
            v = v.strip()
        return v


class RespuestaEncuesta(BaseModel):
    """
    Model representing a single survey response (answer).
    
    Attributes:
        pregunta: The survey question
        respuesta: The answer (either Likert scale 1-5, percentage 0-100, or text)
        comentario: Optional comment or additional notes
    """
    pregunta: str
    respuesta: Union[int, float, str]
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
        Validate that respuesta follows the allowed formats:
        - Likert scale (int 1-5)
        - Percentage (float 0.0-100.0)
        - Text (str)
        Uses mode='after' to validate after type coercion.
        """
        return validar_respuesta(v)

    @field_validator("pregunta", mode="before")
    @classmethod
    def validate_pregunta(cls, v: str) -> str:
        """
        Validate and clean the pregunta field.
        Uses mode='before' to normalize by stripping whitespace.
        """
        if isinstance(v, str):
            v = v.strip()
        return v


class EncuestaCompleta(BaseModel):
    """
    Model representing a complete survey with respondent and all responses.
    
    Attributes:
        id: Unique survey identifier
        encuestado: The respondent information (nested Encuestado model)
        respuestas: List of survey responses (nested RespuestaEncuesta models)
    """
    id: int
    encuestado: Encuestado
    respuestas: List[RespuestaEncuesta]

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


class EstadisticasEncuestas(BaseModel):
    """
    Model for survey statistics response.
    
    Attributes:
        total_encuestas: Total number of surveys
        edad_promedio: Average age of respondents
        distribucion_por_estrato: Dictionary mapping strata to survey counts
    """
    total_encuestas: int
    edad_promedio: float
    distribucion_por_estrato: dict

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


class ErrorResponse(BaseModel):
    """
    Model for structured error responses.
    
    Attributes:
        error: Error type or code
        message: Human-readable error message
        details: List of detailed error information
    """
    error: str
    message: str
    details: List[dict]

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
