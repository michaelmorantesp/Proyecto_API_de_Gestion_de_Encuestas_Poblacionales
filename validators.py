"""
Validators and validation utilities for the encuesta-api project.

This module contains:
- List of valid Colombian departments
- Helper validation functions
- Custom field validators using Pydantic's @field_validator decorator
"""

from typing import Union

# List of all valid Colombian departments
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
    "Distrito Capital",
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
    "Santander",
    "Sucre",
    "Tolima",
    "Valle del Cauca",
    "Vaupés",
    "Vichada"
}


def validar_edad(valor: int) -> int:
    """
    Validate that age is between 0 and 120.
    
    Args:
        valor: The age value to validate
        
    Returns:
        int: The validated age value
        
    Raises:
        ValueError: If age is not between 0 and 120
    """
    if not isinstance(valor, int):
        raise ValueError("edad must be an integer")
    if valor < 0 or valor > 120:
        raise ValueError("edad must be between 0 and 120")
    return valor


def validar_estrato(valor: int) -> int:
    """
    Validate that stratum is an integer between 1 and 6.
    
    Args:
        valor: The stratum value to validate
        
    Returns:
        int: The validated stratum value
        
    Raises:
        ValueError: If stratum is not between 1 and 6
    """
    if not isinstance(valor, int):
        raise ValueError("estrato must be an integer")
    if valor < 1 or valor > 6:
        raise ValueError("estrato must be an integer between 1 and 6")
    return valor


def validar_departamento(valor: str) -> str:
    """
    Validate that department is in the list of valid Colombian departments.
    
    Args:
        valor: The department name to validate
        
    Returns:
        str: The validated department name
        
    Raises:
        ValueError: If department is not valid
    """
    if valor not in DEPARTAMENTOS_COLOMBIANOS:
        raise ValueError(
            f"departamento must be one of the valid Colombian departments. "
            f"Got: {valor}"
        )
    return valor


def validar_respuesta(valor: Union[int, float, str]) -> Union[int, float, str]:
    """
    Validate that survey response is either:
    - Likert scale (int 1-5)
    - Percentage (float 0.0-100.0)
    - Text (str)
    
    Args:
        valor: The response value to validate
        
    Returns:
        Union[int, float, str]: The validated response value
        
    Raises:
        ValueError: If response format is invalid
    """
    # If it's a string, it's always valid (open-ended response)
    if isinstance(valor, str):
        return valor
    
    # If it's an integer, check if it's a valid Likert scale (1-5)
    if isinstance(valor, int):
        if 1 <= valor <= 5:
            return valor
        else:
            raise ValueError(
                "If respuesta is an integer, it must be a Likert scale (1-5)"
            )
    
    # If it's a float, check if it's a valid percentage (0.0-100.0)
    if isinstance(valor, float):
        if 0.0 <= valor <= 100.0:
            return valor
        else:
            raise ValueError(
                "If respuesta is a float, it must be a percentage (0.0-100.0)"
            )
    
    raise ValueError(
        "respuesta must be either Likert scale (1-5), percentage (0.0-100.0), or text"
    )
