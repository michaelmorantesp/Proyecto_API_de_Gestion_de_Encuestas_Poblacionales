"""
validators.py — Funciones de validación reutilizables para encuesta-api.

Este módulo separa la lógica de validación de los modelos Pydantic.
Así los modelos en models.py se mantienen limpios: solo llaman a estas
funciones desde los @field_validator.

Esta separación sigue el principio de responsabilidad única (SRP):
cada módulo tiene una sola razón para cambiar.
"""

# Union permite declarar que un parámetro puede ser de varios tipos a la vez
from typing import Union


# ============================================================================
# LISTA DE DEPARTAMENTOS COLOMBIANOS VÁLIDOS
# ============================================================================

# Usamos un 'set' (conjunto) en lugar de una lista porque:
#   - La búsqueda con 'in' es O(1) en sets (tabla hash) vs O(n) en listas
#   - No nos interesa el orden, solo la pertenencia
#   - Garantiza que no haya valores duplicados
#
# Incluimos alias comunes para mejorar la experiencia del usuario de la API:
#   "Bogotá D.C." y "Bogotá" son formas legítimas de referirse al Distrito Capital
DEPARTAMENTOS_COLOMBIANOS = {
    "Amazonas",
    "Antioquia",
    "Arauca",
    "Atlántico",
    "Bolívar",
    "Boyacá",
    "Caldas",
    "Caquetá",
    "Casanare",
    "Cauca",
    "Cesar",
    "Chocó",
    "Córdoba",
    "Cundinamarca",
    "Distrito Capital",         # Nombre oficial
    "Bogotá D.C.",              # Alias oficial usado en documentos gubernamentales
    "Bogotá",                   # Alias coloquial más común
    "Guainía",
    "Guaviare",
    "Huila",
    "La Guajira",
    "Magdalena",
    "Meta",
    "Nariño",
    "Norte de Santander",
    "Putumayo",
    "Quindío",
    "Risaralda",
    "San Andrés y Providencia",
    "Santander",
    "Sucre",
    "Tolima",
    "Valle del Cauca",
    "Vaupés",
    "Vichada"
}


# ============================================================================
# FUNCIONES DE VALIDACIÓN
# ============================================================================

def validar_edad(valor: int) -> int:
    """
    Valida que la edad sea un entero entre 0 y 120.

    El límite de 120 corresponde a la restricción biológica máxima documentada.
    El límite de 0 permite registrar recién nacidos.

    Esta función es llamada desde el @field_validator("edad", mode="after") de Encuestado.
    mode="after" significa que Pydantic ya convirtió el valor al tipo 'int' antes
    de llegar aquí, por lo que recibimos un entero garantizado.

    Retorna el mismo valor si es válido.
    Lanza ValueError si está fuera del rango, lo que Pydantic convierte en ValidationError.
    """

    # isinstance verifica si el valor es exactamente del tipo int
    # (en Python, bool es subclase de int, pero aquí no es un problema
    # porque modo 'after' ya garantiza que Pydantic lo trató como int)
    if not isinstance(valor, int):
        raise ValueError("La edad debe ser un número entero")

    # Verificamos que esté dentro del rango biológico válido
    if valor < 0 or valor > 120:
        raise ValueError("edad must be between 0 and 120")

    # Si pasó todas las validaciones, devolvemos el valor sin cambios
    return valor


def validar_estrato(valor: int) -> int:
    """
    Valida que el estrato socioeconómico sea un entero entre 1 y 6.

    En Colombia, la estratificación define 6 niveles:
      1 = bajo-bajo, 2 = bajo, 3 = medio-bajo,
      4 = medio,     5 = medio-alto, 6 = alto

    Llamada desde @field_validator("estrato", mode="after") de Encuestado.
    """

    # Verificamos el tipo antes de comparar rangos
    if not isinstance(valor, int):
        raise ValueError("El estrato debe ser un número entero")

    # Solo los estratos 1 a 6 son válidos en el sistema colombiano
    if valor < 1 or valor > 6:
        raise ValueError("estrato must be an integer between 1 and 6")

    return valor


def validar_departamento(valor: str) -> str:
    """
    Valida que el departamento esté en la lista oficial de departamentos colombianos.

    Llamada desde @field_validator("departamento", mode="before") de Encuestado.
    mode="before" significa que el validador en models.py ya aplicó .strip()
    al string antes de llamar a esta función, por lo que 'valor' llega limpio.

    El operador 'in' sobre un set tiene complejidad O(1): muy eficiente.
    """

    # Verificamos si el string está en el conjunto de departamentos válidos
    if valor not in DEPARTAMENTOS_COLOMBIANOS:
        # Lanzamos un ValueError descriptivo que incluye el valor rechazado
        raise ValueError(
            f"departamento must be one of the valid Colombian departments. "
            f"Got: {valor}"
        )

    # Si el departamento es válido, lo devolvemos tal cual
    return valor


def validar_respuesta(valor: Union[int, float, str]) -> Union[int, float, str]:
    """
    Valida que la respuesta de encuesta cumpla uno de los tres formatos aceptados:

      1. Escala Likert → entero entre 1 y 5 (ej: preguntas de satisfacción)
      2. Porcentaje    → float entre 0.0 y 100.0 (ej: cobertura educativa)
      3. Texto libre   → cualquier string (ej: preguntas abiertas)

    Llamada desde @field_validator("respuesta", mode="after") de RespuestaEncuesta.
    mode="after" garantiza que Pydantic ya resolvió el tipo del Union antes de llegar aquí.

    El orden de las comprobaciones importa:
    Primero str, luego int, luego float — porque en Python bool es subclase de int
    y float puede tener valores como 4.0 que matemáticamente son enteros.
    """

    # Si es texto, es válido directamente sin restricciones de rango
    if isinstance(valor, str):
        return valor

    # Si es entero, debe estar en la escala Likert (1 a 5)
    if isinstance(valor, int):
        if 1 <= valor <= 5:
            return valor
        else:
            # Informamos exactamente por qué falló la validación
            raise ValueError(
                "If respuesta is an integer, it must be a Likert scale (1-5)"
            )

    # Si es float (número decimal), debe ser un porcentaje entre 0.0 y 100.0
    if isinstance(valor, float):
        if 0.0 <= valor <= 100.0:
            return valor
        else:
            raise ValueError(
                "If respuesta is a float, it must be a percentage (0.0-100.0)"
            )

    # Si llegamos aquí, el tipo no es ninguno de los tres esperados
    raise ValueError(
        "respuesta must be either Likert scale (1-5), percentage (0.0-100.0), or text"
    )
