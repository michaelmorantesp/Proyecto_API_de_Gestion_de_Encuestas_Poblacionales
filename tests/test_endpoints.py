"""
tests/test_endpoints.py — Tests de integración para los endpoints REST.

Los tests de integración verifican el sistema completo: FastAPI + modelos + validadores
trabajando juntos. Usamos TestClient de FastAPI para simular peticiones HTTP
sin necesitar levantar un servidor real.

Para correr estos tests: pytest tests/test_endpoints.py -v
"""

# pytest: framework de testing. Usamos sus fixtures y el decorador @pytest.mark
import pytest

# TestClient simula un cliente HTTP que hace peticiones a la app FastAPI.
# Internamente usa httpx para las peticiones y maneja el ciclo de vida del app.
from fastapi.testclient import TestClient

# Importamos el módulo completo (no solo app y encuestas_storage) porque necesitamos
# modificar la variable global next_survey_id entre tests.
# Si importáramos solo 'from main import next_survey_id', obtendríamos una copia
# del valor en ese momento, no una referencia a la variable original.
import main
from main import app, encuestas_storage


# ============================================================================
# FIXTURES DE PYTEST
# ============================================================================

@pytest.fixture
def client():
    """
    Fixture que crea y devuelve un TestClient para la aplicación.

    Un 'fixture' en pytest es una función que prepara recursos para los tests.
    Al declarar 'client' como parámetro de un test, pytest lo llama automáticamente
    y pasa el resultado al test.

    TestClient envuelve la app FastAPI y permite hacer peticiones HTTP
    en los tests como si fueran llamadas reales, pero sin necesitar servidor.
    """
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_storage():
    """
    Fixture que limpia el estado compartido antes y después de cada test.

    autouse=True hace que este fixture se aplique automáticamente a TODOS
    los tests de este archivo, sin necesidad de declararlo como parámetro.

    PROBLEMA QUE RESUELVE (BUG 5 CORREGIDO):
    encuestas_storage y next_survey_id son variables globales en main.py.
    Si un test crea encuestas, esos datos persisten para el siguiente test
    porque comparten el mismo módulo en memoria durante la sesión de pytest.

    Sin limpiar next_survey_id:
      - Test A crea una encuesta → id=1, next_survey_id queda en 2
      - Test B crea una encuesta → recibe id=2 (esperaba id=1) → TEST FALLA

    Solución: antes de cada test (antes del 'yield') limpiamos el dict
    y reseteamos el contador. Después del 'yield' repetimos la limpieza
    para dejar el estado limpio para el siguiente test.
    """

    # --- Preparación ANTES del test ---
    encuestas_storage.clear()       # Vaciamos el diccionario de encuestas
    main.next_survey_id = 1         # Reseteamos el contador de IDs a 1

    # 'yield' pausa el fixture y ejecuta el test.
    # Todo lo que está antes del yield es "setup", todo lo de después es "teardown".
    yield

    # --- Limpieza DESPUÉS del test ---
    encuestas_storage.clear()       # Limpieza por si el test falló en medio
    main.next_survey_id = 1         # Dejamos el contador en estado inicial


# ============================================================================
# PAYLOAD REUTILIZABLE
# ============================================================================

# Diccionario con datos de encuesta válidos, reutilizado en la mayoría de tests.
# Lo definimos una sola vez aquí para evitar repetición (principio DRY: Don't Repeat Yourself).
# Nota: incluye "id": 0 porque EncuestaCompleta requiere el campo id en el body,
# pero el endpoint sobreescribe ese valor con el ID real generado por el servidor.
valid_survey_data = {
    "id": 0,                            # El servidor ignorará este valor y asignará el suyo
    "encuestado": {
        "nombre": "Test User",
        "edad": 30,
        "estrato": 2,
        "departamento": "Cundinamarca"
    },
    "respuestas": [
        {
            "pregunta": "¿Satisfecho con servicios?",
            "respuesta": 4,             # Escala Likert válida (1-5)
            "comentario": "Buen servicio"
        }
    ]
}


# ============================================================================
# TESTS DE HEALTH CHECK
# ============================================================================

class TestHealthCheck:
    """Tests para el endpoint raíz GET /."""

    def test_raiz_endpoint(self, client):
        """
        Verifica que el endpoint raíz responde con status 200
        y un mensaje de bienvenida que menciona 'Encuesta API'.
        """

        # client.get() simula una petición GET a la ruta "/"
        response = client.get("/")

        # El servidor debe responder con HTTP 200 OK
        assert response.status_code == 200

        # response.json() deserializa el cuerpo de la respuesta de JSON a dict Python
        assert "mensaje" in response.json()

        # Verificamos que el mensaje contiene el nombre de la API
        assert "Encuesta API" in response.json()["mensaje"]


# ============================================================================
# TESTS DE CREACIÓN (POST /encuestas/)
# ============================================================================

class TestCrearEncuesta:
    """Tests para el endpoint POST /encuestas/."""

    def test_crear_encuesta_exitosa(self, client):
        """
        Verifica el flujo completo de creación:
        - La petición POST retorna status 201 Created
        - La respuesta contiene el id asignado por el servidor (1)
        - Los datos del encuestado están correctamente almacenados
        """

        # client.post() simula una petición POST con un body JSON
        response = client.post("/encuestas/", json=valid_survey_data)

        # 201 Created es el status correcto para creación de recursos
        assert response.status_code == 201

        data = response.json()

        # El servidor debe haber asignado id=1 (primer registro)
        assert "id" in data
        assert data["id"] == 1

        # El nombre del encuestado debe aparecer en la respuesta
        assert data["encuestado"]["nombre"] == "Test User"

    def test_crear_encuesta_asigna_id_secuencial(self, client):
        """
        Verifica que las encuestas reciben IDs incrementales (1, 2, 3...).
        Esto confirma que next_survey_id funciona correctamente y que
        el fixture clear_storage lo resetea entre tests.
        """

        # Primera encuesta → debe recibir id=1
        response1 = client.post("/encuestas/", json=valid_survey_data)
        assert response1.json()["id"] == 1

        # Segunda encuesta → debe recibir id=2
        response2 = client.post("/encuestas/", json=valid_survey_data)
        assert response2.json()["id"] == 2

    def test_crear_encuesta_edad_invalida(self, client):
        """
        Verifica que una edad fuera de rango (150) retorna HTTP 422
        con la estructura de error personalizada que definimos en el handler.
        """

        # Creamos una copia del payload y modificamos solo la edad
        # .copy() crea una copia superficial del diccionario para no modificar el original
        survey = valid_survey_data.copy()
        survey["encuestado"] = survey["encuestado"].copy()  # Copia también el diccionario anidado
        survey["encuestado"]["edad"] = 150                  # Valor inválido

        response = client.post("/encuestas/", json=survey)

        # El handler personalizado debe retornar 422 con nuestra estructura JSON
        assert response.status_code == 422

        # Verificamos que el error tiene el campo "error" con valor "ValidationError"
        assert "ValidationError" in response.json()["error"]

        # Verificamos que en los detalles aparece el campo "edad" como el problemático
        # any() retorna True si al menos un elemento de la lista cumple la condición
        assert any("edad" in str(detail["field"])
                   for detail in response.json()["details"])

    def test_crear_encuesta_estrato_invalido(self, client):
        """
        Verifica que un estrato fuera de rango (7) retorna HTTP 422
        y que los detalles del error mencionan el campo 'estrato'.
        """
        survey = valid_survey_data.copy()
        survey["encuestado"] = survey["encuestado"].copy()
        survey["encuestado"]["estrato"] = 7   # Inválido: máximo permitido es 6

        response = client.post("/encuestas/", json=survey)

        assert response.status_code == 422
        assert any("estrato" in str(detail["field"])
                   for detail in response.json()["details"])

    def test_crear_encuesta_departamento_invalido(self, client):
        """
        Verifica que un departamento no colombiano retorna HTTP 422
        y que los detalles mencionan el campo 'departamento'.
        """
        survey = valid_survey_data.copy()
        survey["encuestado"] = survey["encuestado"].copy()
        survey["encuestado"]["departamento"] = "InvalidoDepartamento"  # No existe en Colombia

        response = client.post("/encuestas/", json=survey)

        assert response.status_code == 422
        assert any("departamento" in str(detail["field"])
                   for detail in response.json()["details"])

    def test_crear_encuesta_respuesta_likert_invalida(self, client):
        """
        Verifica que una respuesta Likert fuera de rango (6) retorna HTTP 422.
        El valor 6 es inválido porque la escala Likert solo va de 1 a 5.
        """
        survey = valid_survey_data.copy()
        survey["respuestas"] = [
            {
                "pregunta": "Pregunta",
                "respuesta": 6,         # Inválido: Likert máximo es 5
                "comentario": None
            }
        ]

        response = client.post("/encuestas/", json=survey)
        assert response.status_code == 422

    def test_crear_encuesta_respuesta_texto_valida(self, client):
        """
        Verifica que las respuestas de texto libre son aceptadas sin restricciones.
        El sistema debe ser flexible y permitir respuestas abiertas.
        """
        survey = valid_survey_data.copy()
        survey["respuestas"] = [
            {
                "pregunta": "¿Comentario abierto?",
                "respuesta": "Texto abierto sin restricción",  # String siempre válido
                "comentario": None
            }
        ]

        response = client.post("/encuestas/", json=survey)
        assert response.status_code == 201   # Debe crear exitosamente


# ============================================================================
# TESTS DE LISTADO (GET /encuestas/)
# ============================================================================

class TestObtenerEncuestas:
    """Tests para el endpoint GET /encuestas/."""

    def test_obtener_encuestas_vacio(self, client):
        """
        Verifica que cuando no hay encuestas, el endpoint retorna
        una lista vacía (no un error ni null).
        """
        response = client.get("/encuestas/")

        assert response.status_code == 200
        assert response.json() == []    # Lista vacía, no null ni error

    def test_obtener_encuestas_lista(self, client):
        """
        Verifica que después de crear dos encuestas, el listado las retorna ambas
        con los IDs correctos y en orden de creación.
        """
        # Creamos dos encuestas secuencialmente
        client.post("/encuestas/", json=valid_survey_data)
        client.post("/encuestas/", json=valid_survey_data)

        response = client.get("/encuestas/")

        assert response.status_code == 200

        data = response.json()          # Lista de encuestas en formato JSON

        assert len(data) == 2           # Exactamente 2 encuestas
        assert data[0]["id"] == 1       # Primera encuesta tiene id=1
        assert data[1]["id"] == 2       # Segunda encuesta tiene id=2


# ============================================================================
# TESTS DE BÚSQUEDA POR ID (GET /encuestas/{id})
# ============================================================================

class TestObtenerEncuestaPorId:
    """Tests para el endpoint GET /encuestas/{survey_id}."""

    def test_obtener_encuesta_existente(self, client):
        """
        Verifica que una encuesta recién creada puede recuperarse por su ID.
        """
        # Primero creamos una encuesta y capturamos su ID de la respuesta
        created = client.post("/encuestas/", json=valid_survey_data)
        survey_id = created.json()["id"]    # Extraemos el ID asignado por el servidor

        # Luego la buscamos por ese ID
        response = client.get(f"/encuestas/{survey_id}")

        assert response.status_code == 200
        assert response.json()["id"] == survey_id   # Debe ser la misma encuesta

    def test_obtener_encuesta_no_existe(self, client):
        """
        Verifica que buscar un ID que no existe retorna HTTP 404 Not Found
        con el mensaje de error correcto.
        """
        # El ID 999 no existe porque el storage está vacío (limpiado por el fixture)
        response = client.get("/encuestas/999")

        assert response.status_code == 404

        # Verificamos que el mensaje de error menciona "no encontrada"
        assert "no encontrada" in response.json()["detail"]

    def test_obtener_encuesta_multiples(self, client):
        """
        Verifica que con múltiples encuestas, cada ID retorna los datos correctos.
        Confirma que no hay confusión entre registros.
        """
        # Creamos dos encuestas con nombres diferentes para poder distinguirlas
        survey1 = valid_survey_data.copy()
        survey1["encuestado"] = survey1["encuestado"].copy()
        survey1["encuestado"]["nombre"] = "Usuario 1"

        survey2 = valid_survey_data.copy()
        survey2["encuestado"] = survey2["encuestado"].copy()
        survey2["encuestado"]["nombre"] = "Usuario 2"

        # Las creamos y guardamos sus IDs
        resp1 = client.post("/encuestas/", json=survey1)
        resp2 = client.post("/encuestas/", json=survey2)

        id1 = resp1.json()["id"]    # id=1
        id2 = resp2.json()["id"]    # id=2

        # Buscamos cada una por su ID y verificamos el nombre
        get1 = client.get(f"/encuestas/{id1}")
        get2 = client.get(f"/encuestas/{id2}")

        assert get1.json()["encuestado"]["nombre"] == "Usuario 1"
        assert get2.json()["encuestado"]["nombre"] == "Usuario 2"


# ============================================================================
# TESTS DE ACTUALIZACIÓN (PUT /encuestas/{id})
# ============================================================================

class TestActualizarEncuesta:
    """Tests para el endpoint PUT /encuestas/{survey_id}."""

    def test_actualizar_encuesta_exitosa(self, client):
        """
        Verifica el flujo completo de actualización:
        - Crear una encuesta
        - Modificar su nombre
        - Confirmar que el cambio se guardó
        """
        # Paso 1: Crear la encuesta original
        created = client.post("/encuestas/", json=valid_survey_data)
        survey_id = created.json()["id"]

        # Paso 2: Preparar los datos actualizados con el nuevo nombre
        updated_data = valid_survey_data.copy()
        updated_data["encuestado"] = updated_data["encuestado"].copy()
        updated_data["encuestado"]["nombre"] = "Nombre Actualizado"
        updated_data["id"] = survey_id  # Incluimos el ID en el body también

        # Paso 3: Enviar la actualización con PUT
        response = client.put(f"/encuestas/{survey_id}", json=updated_data)

        assert response.status_code == 200

        # Paso 4: Verificar que el nombre cambió en la respuesta
        assert response.json()["encuestado"]["nombre"] == "Nombre Actualizado"

    def test_actualizar_encuesta_no_existe(self, client):
        """
        Verifica que intentar actualizar una encuesta inexistente retorna 404.
        """
        # El ID 999 no existe en el storage vacío
        response = client.put("/encuestas/999", json=valid_survey_data)
        assert response.status_code == 404

    def test_actualizar_encuesta_validacion(self, client):
        """
        Verifica que los datos del body también son validados en el PUT.
        Una actualización con datos inválidos debe retornar 422.
        """
        # Creamos una encuesta válida primero
        created = client.post("/encuestas/", json=valid_survey_data)
        survey_id = created.json()["id"]

        # Intentamos actualizarla con una edad inválida
        invalid_data = valid_survey_data.copy()
        invalid_data["encuestado"] = invalid_data["encuestado"].copy()
        invalid_data["encuestado"]["edad"] = 150    # Inválido
        invalid_data["id"] = survey_id

        response = client.put(f"/encuestas/{survey_id}", json=invalid_data)

        # Los datos inválidos deben ser rechazados incluso en actualizaciones
        assert response.status_code == 422


# ============================================================================
# TESTS DE ELIMINACIÓN (DELETE /encuestas/{id})
# ============================================================================

class TestEliminarEncuesta:
    """Tests para el endpoint DELETE /encuestas/{survey_id}."""

    def test_eliminar_encuesta_exitosa(self, client):
        """
        Verifica el flujo completo de eliminación:
        - Crear una encuesta
        - Eliminarla (debe retornar 204 No Content)
        - Intentar recuperarla (debe retornar 404)
        """
        # Paso 1: Crear la encuesta
        created = client.post("/encuestas/", json=valid_survey_data)
        survey_id = created.json()["id"]

        # Paso 2: Eliminarla
        response = client.delete(f"/encuestas/{survey_id}")

        # 204 No Content: operación exitosa, sin cuerpo en la respuesta
        assert response.status_code == 204

        # Paso 3: Verificar que ya no existe — debe retornar 404
        get_response = client.get(f"/encuestas/{survey_id}")
        assert get_response.status_code == 404

    def test_eliminar_encuesta_no_existe(self, client):
        """
        Verifica que intentar eliminar una encuesta que no existe retorna 404.
        No debe lanzar una excepción interna del servidor.
        """
        response = client.delete("/encuestas/999")
        assert response.status_code == 404

    def test_eliminar_no_afecta_otros(self, client):
        """
        Verifica que eliminar una encuesta no afecta a las demás.
        El sistema debe mantener la integridad de los datos restantes.
        """
        # Creamos dos encuestas: id=1 e id=2
        client.post("/encuestas/", json=valid_survey_data)
        client.post("/encuestas/", json=valid_survey_data)

        # Eliminamos solo la primera
        client.delete("/encuestas/1")

        # La segunda encuesta debe seguir existiendo sin cambios
        response = client.get("/encuestas/2")
        assert response.status_code == 200


# ============================================================================
# TESTS DE ESTADÍSTICAS (GET /encuestas/estadisticas/)
# ============================================================================

class TestEstadisticas:
    """Tests para el endpoint asíncrono GET /encuestas/estadisticas/."""

    def test_estadisticas_vacio(self, client):
        """
        Verifica que con el storage vacío, las estadísticas retornan
        valores en cero en lugar de un error (ej: división por cero).
        """
        response = client.get("/encuestas/estadisticas/")

        assert response.status_code == 200

        data = response.json()
        assert data["total_encuestas"] == 0
        assert data["edad_promedio"] == 0.0
        assert data["distribucion_por_estrato"] == {}   # Diccionario vacío

    def test_estadisticas_una_encuesta(self, client):
        """
        Verifica que con una sola encuesta, el promedio de edad coincide
        exactamente con la edad de ese encuestado.
        """
        # Creamos una encuesta con edad=30 y estrato=2
        survey = valid_survey_data.copy()
        survey["encuestado"] = survey["encuestado"].copy()
        survey["encuestado"]["edad"] = 30
        survey["encuestado"]["estrato"] = 2

        client.post("/encuestas/", json=survey)

        response = client.get("/encuestas/estadisticas/")
        assert response.status_code == 200

        data = response.json()
        assert data["total_encuestas"] == 1
        assert data["edad_promedio"] == 30.0            # Promedio de una sola edad
        assert data["distribucion_por_estrato"]["2"] == 1   # Un encuestado en estrato 2

    def test_estadisticas_multiples_encuestas(self, client):
        """
        Verifica el cálculo correcto con dos encuestas:
        - Promedio de edades: (30 + 40) / 2 = 35.0
        - Distribución: 1 en estrato 2, 1 en estrato 3
        """
        # Primera encuesta: edad=30, estrato=2
        survey1 = valid_survey_data.copy()
        survey1["encuestado"] = survey1["encuestado"].copy()
        survey1["encuestado"]["edad"] = 30
        survey1["encuestado"]["estrato"] = 2

        # Segunda encuesta: edad=40, estrato=3
        survey2 = valid_survey_data.copy()
        survey2["encuestado"] = survey2["encuestado"].copy()
        survey2["encuestado"]["edad"] = 40
        survey2["encuestado"]["estrato"] = 3

        client.post("/encuestas/", json=survey1)
        client.post("/encuestas/", json=survey2)

        response = client.get("/encuestas/estadisticas/")
        data = response.json()

        assert data["total_encuestas"] == 2
        assert data["edad_promedio"] == 35.0            # (30 + 40) / 2 = 35
        assert data["distribucion_por_estrato"]["2"] == 1
        assert data["distribucion_por_estrato"]["3"] == 1

    def test_estadisticas_distribucion_estrato(self, client):
        """
        Verifica que la distribución por estrato cuenta correctamente
        cuando múltiples encuestados pertenecen al mismo estrato.
        """
        # Creamos 5 encuestas: 2 en estrato 1, 3 en estrato 2
        for estrato in [1, 1, 2, 2, 2]:
            survey = valid_survey_data.copy()
            survey["encuestado"] = survey["encuestado"].copy()
            survey["encuestado"]["estrato"] = estrato
            client.post("/encuestas/", json=survey)

        response = client.get("/encuestas/estadisticas/")
        data = response.json()

        # Verificamos los conteos: 2 encuestados en estrato 1, 3 en estrato 2
        assert data["distribucion_por_estrato"]["1"] == 2
        assert data["distribucion_por_estrato"]["2"] == 3

    @pytest.mark.asyncio
    def test_estadisticas_endpoint_async(self, client):
        """
        Verifica que el endpoint asíncrono funciona correctamente.
        TestClient de FastAPI maneja transparentemente los endpoints async def,
        por lo que no necesitamos hacer nada especial para probarlo.
        El @pytest.mark.asyncio indica que el test está relacionado con código async.
        """
        response = client.get("/encuestas/estadisticas/")
        assert response.status_code == 200


# ============================================================================
# TESTS DE MANEJO DE ERRORES
# ============================================================================

class TestErrorHandling:
    """Tests para el manejador personalizado de errores de validación."""

    def test_validation_error_estructura(self, client):
        """
        Verifica que cuando hay múltiples campos inválidos, la respuesta 422
        tiene la estructura JSON correcta con todos los detalles.

        Esto prueba que nuestro handler personalizado (RequestValidationError)
        se está ejecutando en lugar del handler genérico de FastAPI.
        """
        # Payload con 3 campos inválidos simultáneos
        invalid_data = {
            "id": 0,
            "encuestado": {
                "nombre": "Test",
                "edad": 150,                        # Inválido: mayor a 120
                "estrato": 7,                       # Inválido: mayor a 6
                "departamento": "InvalidoDepartamento"  # Inválido: no existe en Colombia
            },
            "respuestas": []
        }

        response = client.post("/encuestas/", json=invalid_data)

        # El servidor debe responder con 422 Unprocessable Entity
        assert response.status_code == 422

        data = response.json()

        # Verificamos que la respuesta tiene nuestra estructura personalizada
        assert "error" in data          # Campo "error" con tipo de error
        assert "message" in data        # Campo "message" con descripción legible
        assert "details" in data        # Campo "details" con lista de errores por campo

        # Debe haber al menos un error en la lista de detalles
        assert len(data["details"]) > 0

        # Cada detalle debe tener los tres campos que definimos en ErrorResponse
        for detail in data["details"]:
            assert "field" in detail    # Nombre del campo inválido
            assert "value" in detail    # Valor que envió el cliente
            assert "reason" in detail   # Razón del fallo de validación

    def test_falta_campo_requerido(self, client):
        """
        Verifica que omitir campos requeridos también retorna 422.
        Pydantic requiere todos los campos sin valor por defecto.
        """
        # Payload incompleto: falta 'estrato' y 'departamento'
        incomplete_data = {
            "id": 0,
            "encuestado": {
                "nombre": "Test",
                "edad": 30
                # Falta: estrato (requerido)
                # Falta: departamento (requerido)
            },
            "respuestas": []
        }

        response = client.post("/encuestas/", json=incomplete_data)

        # Campos requeridos faltantes deben retornar 422
        assert response.status_code == 422


# ============================================================================
# EJECUCIÓN DIRECTA (opcional)
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
