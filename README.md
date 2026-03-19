# Encuesta API

REST API para gestionar datos de encuestas poblacionales en Colombia.

## Descripción

Encuesta API es una aplicación completa de FastAPI que implementa un sistema de gestión de encuestas con:

- **Modelos Pydantic anidados** con validación robusta
- **Validadores personalizados** para campos específicos del dominio
- **Endpoints REST completos** para operaciones CRUD
- **Manejo de errores personalizado** con respuestas estructuradas
- **Documentación automática** con Swagger/OpenAPI
- **Endpoints asincronos** para mejor rendimiento
- **Almacenamiento en memoria** para demostración

## Arquitectura

La API está construida usando FastAPI y Pydantic para garantizar
validación de datos robusta antes de cualquier análisis estadístico.

## Requisitos

- Python 3.11 o superior
- pip (gestor de paquetes de Python)

## Instalación

### 1. Clonar el repositorio

```bash
git clone <repository-url>
cd encuesta-api
```

### 2. Crear un entorno virtual

**En Windows:**

```bash
python -m venv venv
venv\Scripts\activate
```

**En macOS/Linux:**

```bash
python -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

## Ejecución

### Iniciar el servidor

```bash
python main.py
```

O usando uvicorn directamente:

```bash
uvicorn main:app --reload
```

El servidor estará disponible en: **http://localhost:8000**

### Acceder a la documentación

Una vez iniciado el servidor, accede a:

- **Swagger UI (Docs):** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## Endpoints disponibles

### Crear encuesta

```http
POST /encuestas/
Content-Type: application/json

{
  "id": 0,
  "encuestado": {
    "nombre": "Juan Pérez",
    "edad": 35,
    "estrato": 3,
    "departamento": "Cundinamarca"
  },
  "respuestas": [
    {
      "pregunta": "¿Satisfecho con servicios de salud?",
      "respuesta": 4,
      "comentario": "Buen servicio"
    }
  ]
}
```

**Respuesta (201 Created):**

```json
{
  "id": 1,
  "encuestado": {
    "nombre": "Juan Pérez",
    "edad": 35,
    "estrato": 3,
    "departamento": "Cundinamarca"
  },
  "respuestas": [
    {
      "pregunta": "¿Satisfecho con servicios de salud?",
      "respuesta": 4,
      "comentario": "Buen servicio"
    }
  ]
}
```

### Obtener todas las encuestas

```http
GET /encuestas/
```

**Respuesta (200 OK):**

```json
[
  {
    "id": 1,
    "encuestado": {...},
    "respuestas": [...]
  }
]
```

### Obtener encuesta por ID

```http
GET /encuestas/1
```

**Respuesta (200 OK):**

```json
{
  "id": 1,
  "encuestado": {...},
  "respuestas": [...]
}
```

**Si no existe (404 Not Found):**

```json
{
  "detail": "Encuesta con ID 999 no encontrada"
}
```

### Actualizar encuesta

```http
PUT /encuestas/1
Content-Type: application/json

{
  "id": 1,
  "encuestado": {
    "nombre": "Juan Pérez García",
    "edad": 36,
    "estrato": 2,
    "departamento": "Antioquia"
  },
  "respuestas": [...]
}
```

**Respuesta (200 OK):**

```json
{
  "id": 1,
  "encuestado": {...},
  "respuestas": [...]
}
```

### Eliminar encuesta

```http
DELETE /encuestas/1
```

**Respuesta (204 No Content):** (sin body)

### Obtener estadísticas

```http
GET /encuestas/estadisticas/
```

**Respuesta (200 OK):**

```json
{
  "total_encuestas": 5,
  "edad_promedio": 38.5,
  "distribucion_por_estrato": {
    "1": 1,
    "2": 2,
    "3": 2
  }
}
```

## Validaciones

### Campo `edad`
- Debe ser un entero entre 0 y 120

### Campo `estrato`
- Debe ser un entero entre 1 y 6

### Campo `departamento`
- Debe ser un departamento colombiano válido. Lista completa:
  - Amazonas, Antioquia, Arauca, Atlántico, Bolívar, Boyacá, Caldas, Caquetá, Casanare, Cauca, Cesar, Chocó, Córdoba, Cundinamarca, Distrito Capital, Bogotá D.C., Bogotá, Guainía, Guaviare, Huila, La Guajira, Magdalena, Meta, Nariño, Norte de Santander, Putumayo, Quindío, Risaralda, San Andrés y Providencia, Santander, Sucre, Tolima, Valle del Cauca, Vaupés, Vichada

### Campo `respuesta`
- Escala Likert (integer 1-5)
- Porcentaje (float 0.0-100.0)
- Texto (string)

### Ejemplo de error de validación

```bash
curl -X POST http://localhost:8000/encuestas/ \
  -H "Content-Type: application/json" \
  -d '{
    "id": 0,
    "encuestado": {
      "nombre": "Test",
      "edad": 150,
      "estrato": 7,
      "departamento": "InvalidoDepartamento"
    },
    "respuestas": []
  }'
```

**Respuesta (422 Unprocessable Entity):**

```json
{
  "error": "ValidationError",
  "message": "Invalid survey data provided",
  "details": [
    {
      "field": "encuestado.edad",
      "value": 150,
      "reason": "edad must be between 0 and 120"
    },
    {
      "field": "encuestado.estrato",
      "value": 7,
      "reason": "estrato must be an integer between 1 and 6"
    },
    {
      "field": "encuestado.departamento",
      "value": "InvalidoDepartamento",
      "reason": "departamento must be one of the valid Colombian departments..."
    }
  ]
}
```

## Ejecutar tests

```bash
pytest tests/
```

Para ver el output detallado:

```bash
pytest tests/ -v
```

Para ver cobertura:

```bash
pytest tests/ --cov=.
```

## Estructura del proyecto

```
encuesta-api/
├── main.py                 # Aplicación FastAPI, rutas y decoradores
├── models.py              # Modelos Pydantic con validadores
├── validators.py          # Funciones validadoras personalizadas
├── requirements.txt       # Dependencias del proyecto
├── README.md             # Este archivo
├── .gitignore            # Archivos a ignorar en git
└── tests/
    ├── test_models.py    # Tests para modelos
    └── test_endpoints.py # Tests para endpoints
```

## Tecnologías utilizadas

- **FastAPI 0.104+**: Framework web moderno y rápido para APIs REST
- **Pydantic 2.5+**: Validación de datos y serialización
- **Uvicorn 0.24+**: Servidor ASGI de alto rendimiento
- **Pytest 7.4+**: Framework para testing
- **Python 3.11+**: Lenguaje de programación

## Características destacadas

### 1. Modelos Pydantic anidados
- `Encuestado`: Información del respondiente
- `RespuestaEncuesta`: Respuesta individual
- `EncuestaCompleta`: Encuesta completa con estructura anidada

### 2. Validadores personalizados
- Uso de `mode="before"` para normalizar entrada
- Uso de `mode="after"` para validar después de coerción de tipo
- Validaciones complexas domain-específicas

### 3. Endpoints asincronos
- Endpoint `/encuestas/estadisticas/` implementado como `async`
- Demuestra cómo trabajar con concurrencia en FastAPI
- Documentado con explicación detallada de async/await y ASGI

### 4. Manejo de errores personalizado
- Handler custom para `RequestValidationError` (excepción de FastAPI para errores HTTP 422)
- Respuestas estructuradas con detalles de validación por campo
- Logging de intentos de validación fallida

### 5. Decorador personalizado
- `@log_request`: Registra timestamp, método HTTP y ruta
- Demuestra patrones de metaprogramación en Python
- Explicación de relación con decoradores de FastAPI

## Ejemplos de uso

### Crear una encuesta válida

```bash
curl -X POST http://localhost:8000/encuestas/ \
  -H "Content-Type: application/json" \
  -d '{
    "id": 0,
    "encuestado": {
      "nombre": "María López",
      "edad": 42,
      "estrato": 2,
      "departamento": "Antioquia"
    },
    "respuestas": [
      {
        "pregunta": "Acceso a servicios de salud?",
        "respuesta": 5,
        "comentario": "Excelente cobertura"
      },
      {
        "pregunta": "Educación completada (%)?",
        "respuesta": 85.5,
        "comentario": null
      }
    ]
  }'
```

### Obtener estadísticas

```bash
curl http://localhost:8000/encuestas/estadisticas/
```

## Desarrollo

Para contribuir al proyecto:

1. Crea un branch para tu feature
2. Realiza tus cambios
3. Ejecuta los tests
4. Haz un commit con mensaje descriptivo
5. Abre un Pull Request

## Notas de implementación

- El almacenamiento es en memoria, por lo que los datos se pierden al reiniciar
- Para producción, usar una base de datos real (PostgreSQL, MongoDB, etc.)
- Considerar agregar autenticación y autorización
- Agregar rate limiting o throttling

## Licencia

Este proyecto está bajo licencia MIT.

## Autor

Proyecto de API REST con FastAPI

---

**Última actualización:** 2026-03-18

