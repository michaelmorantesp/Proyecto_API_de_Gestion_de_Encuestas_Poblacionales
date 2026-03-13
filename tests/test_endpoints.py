"""
Tests for FastAPI endpoints.

This module contains integration tests for:
- CRUD operation endpoints
- Status codes (201, 200, 204, 404)
- Error handling for invalid data
- Statistics endpoint
"""

import pytest
from fastapi.testclient import TestClient

from main import app, encuestas_storage


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_storage():
    """Clear the in-memory storage before each test."""
    encuestas_storage.clear()
    yield
    encuestas_storage.clear()


valid_survey_data = {
    "id": 0,
    "encuestado": {
        "nombre": "Test User",
        "edad": 30,
        "estrato": 2,
        "departamento": "Cundinamarca"
    },
    "respuestas": [
        {
            "pregunta": "¿Satisfecho con servicios?",
            "respuesta": 4,
            "comentario": "Buen servicio"
        }
    ]
}


class TestHealthCheck:
    """Tests for health check endpoint."""

    def test_raiz_endpoint(self, client):
        """Test that root endpoint returns health check."""
        response = client.get("/")
        assert response.status_code == 200
        assert "mensaje" in response.json()
        assert "Encuesta API" in response.json()["mensaje"]


class TestCrearEncuesta:
    """Tests for POST /encuestas/ endpoint."""

    def test_crear_encuesta_exitosa(self, client):
        """Test creating a survey returns 201 and assigns ID."""
        response = client.post("/encuestas/", json=valid_survey_data)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["id"] == 1
        assert data["encuestado"]["nombre"] == "Test User"

    def test_crear_encuesta_asigna_id_secuencial(self, client):
        """Test that surveys get sequential IDs."""
        response1 = client.post("/encuestas/", json=valid_survey_data)
        assert response1.json()["id"] == 1

        response2 = client.post("/encuestas/", json=valid_survey_data)
        assert response2.json()["id"] == 2

    def test_crear_encuesta_edad_invalida(self, client):
        """Test that invalid edad returns 422."""
        survey = valid_survey_data.copy()
        survey["encuestado"] = survey["encuestado"].copy()
        survey["encuestado"]["edad"] = 150
        
        response = client.post("/encuestas/", json=survey)
        assert response.status_code == 422
        assert "ValidationError" in response.json()["error"]
        assert any("edad" in str(detail["field"]) 
                   for detail in response.json()["details"])

    def test_crear_encuesta_estrato_invalido(self, client):
        """Test that invalid estrato returns 422."""
        survey = valid_survey_data.copy()
        survey["encuestado"] = survey["encuestado"].copy()
        survey["encuestado"]["estrato"] = 7
        
        response = client.post("/encuestas/", json=survey)
        assert response.status_code == 422
        assert any("estrato" in str(detail["field"]) 
                   for detail in response.json()["details"])

    def test_crear_encuesta_departamento_invalido(self, client):
        """Test that invalid departamento returns 422."""
        survey = valid_survey_data.copy()
        survey["encuestado"] = survey["encuestado"].copy()
        survey["encuestado"]["departamento"] = "InvalidoDepartamento"
        
        response = client.post("/encuestas/", json=survey)
        assert response.status_code == 422
        assert any("departamento" in str(detail["field"]) 
                   for detail in response.json()["details"])

    def test_crear_encuesta_respuesta_likert_invalida(self, client):
        """Test that invalid Likert response returns 422."""
        survey = valid_survey_data.copy()
        survey["respuestas"] = [
            {
                "pregunta": "Pregunta",
                "respuesta": 6,  # Invalid, must be 1-5
                "comentario": None
            }
        ]
        
        response = client.post("/encuestas/", json=survey)
        assert response.status_code == 422

    def test_crear_encuesta_respuesta_texto_valida(self, client):
        """Test that text responses are accepted."""
        survey = valid_survey_data.copy()
        survey["respuestas"] = [
            {
                "pregunta": "¿Comentario abierto?",
                "respuesta": "Texto abierto sin restricción",
                "comentario": None
            }
        ]
        
        response = client.post("/encuestas/", json=survey)
        assert response.status_code == 201


class TestObtenerEncuestas:
    """Tests for GET /encuestas/ endpoint."""

    def test_obtener_encuestas_vacio(self, client):
        """Test getting surveys when list is empty."""
        response = client.get("/encuestas/")
        assert response.status_code == 200
        assert response.json() == []

    def test_obtener_encuestas_lista(self, client):
        """Test getting all surveys."""
        # Create two surveys
        client.post("/encuestas/", json=valid_survey_data)
        client.post("/encuestas/", json=valid_survey_data)
        
        response = client.get("/encuestas/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == 1
        assert data[1]["id"] == 2


class TestObtenerEncuestaPorId:
    """Tests for GET /encuestas/{id} endpoint."""

    def test_obtener_encuesta_existente(self, client):
        """Test getting a specific survey."""
        created = client.post("/encuestas/", json=valid_survey_data)
        survey_id = created.json()["id"]
        
        response = client.get(f"/encuestas/{survey_id}")
        assert response.status_code == 200
        assert response.json()["id"] == survey_id

    def test_obtener_encuesta_no_existe(self, client):
        """Test getting non-existent survey returns 404."""
        response = client.get("/encuestas/999")
        assert response.status_code == 404
        assert "no encontrada" in response.json()["detail"]

    def test_obtener_encuesta_multiples(self, client):
        """Test getting different surveys."""
        survey1 = valid_survey_data.copy()
        survey1["encuestado"] = survey1["encuestado"].copy()
        survey1["encuestado"]["nombre"] = "Usuario 1"
        
        survey2 = valid_survey_data.copy()
        survey2["encuestado"] = survey2["encuestado"].copy()
        survey2["encuestado"]["nombre"] = "Usuario 2"
        
        resp1 = client.post("/encuestas/", json=survey1)
        resp2 = client.post("/encuestas/", json=survey2)
        
        id1 = resp1.json()["id"]
        id2 = resp2.json()["id"]
        
        get1 = client.get(f"/encuestas/{id1}")
        get2 = client.get(f"/encuestas/{id2}")
        
        assert get1.json()["encuestado"]["nombre"] == "Usuario 1"
        assert get2.json()["encuestado"]["nombre"] == "Usuario 2"


class TestActualizarEncuesta:
    """Tests for PUT /encuestas/{id} endpoint."""

    def test_actualizar_encuesta_exitosa(self, client):
        """Test updating a survey."""
        created = client.post("/encuestas/", json=valid_survey_data)
        survey_id = created.json()["id"]
        
        updated_data = valid_survey_data.copy()
        updated_data["encuestado"] = updated_data["encuestado"].copy()
        updated_data["encuestado"]["nombre"] = "Nombre Actualizado"
        updated_data["id"] = survey_id
        
        response = client.put(f"/encuestas/{survey_id}", json=updated_data)
        assert response.status_code == 200
        assert response.json()["encuestado"]["nombre"] == "Nombre Actualizado"

    def test_actualizar_encuesta_no_existe(self, client):
        """Test updating non-existent survey returns 404."""
        response = client.put("/encuestas/999", json=valid_survey_data)
        assert response.status_code == 404

    def test_actualizar_encuesta_validacion(self, client):
        """Test that updated data is validated."""
        created = client.post("/encuestas/", json=valid_survey_data)
        survey_id = created.json()["id"]
        
        invalid_data = valid_survey_data.copy()
        invalid_data["encuestado"] = invalid_data["encuestado"].copy()
        invalid_data["encuestado"]["edad"] = 150  # Invalid
        invalid_data["id"] = survey_id
        
        response = client.put(f"/encuestas/{survey_id}", json=invalid_data)
        assert response.status_code == 422


class TestEliminarEncuesta:
    """Tests for DELETE /encuestas/{id} endpoint."""

    def test_eliminar_encuesta_exitosa(self, client):
        """Test deleting a survey."""
        created = client.post("/encuestas/", json=valid_survey_data)
        survey_id = created.json()["id"]
        
        response = client.delete(f"/encuestas/{survey_id}")
        assert response.status_code == 204
        
        # Verify it's deleted
        get_response = client.get(f"/encuestas/{survey_id}")
        assert get_response.status_code == 404

    def test_eliminar_encuesta_no_existe(self, client):
        """Test deleting non-existent survey returns 404."""
        response = client.delete("/encuestas/999")
        assert response.status_code == 404

    def test_eliminar_no_afecta_otros(self, client):
        """Test that deleting one survey doesn't affect others."""
        client.post("/encuestas/", json=valid_survey_data)
        client.post("/encuestas/", json=valid_survey_data)
        
        # Delete first survey
        client.delete("/encuestas/1")
        
        # Second survey should still exist
        response = client.get("/encuestas/2")
        assert response.status_code == 200


class TestEstadisticas:
    """Tests for GET /encuestas/estadisticas/ endpoint."""

    def test_estadisticas_vacio(self, client):
        """Test statistics with no surveys."""
        response = client.get("/encuestas/estadisticas/")
        assert response.status_code == 200
        data = response.json()
        assert data["total_encuestas"] == 0
        assert data["edad_promedio"] == 0.0
        assert data["distribucion_por_estrato"] == {}

    def test_estadisticas_una_encuesta(self, client):
        """Test statistics with one survey."""
        survey = valid_survey_data.copy()
        survey["encuestado"] = survey["encuestado"].copy()
        survey["encuestado"]["edad"] = 30
        survey["encuestado"]["estrato"] = 2
        
        client.post("/encuestas/", json=survey)
        
        response = client.get("/encuestas/estadisticas/")
        assert response.status_code == 200
        data = response.json()
        assert data["total_encuestas"] == 1
        assert data["edad_promedio"] == 30.0
        assert data["distribucion_por_estrato"]["2"] == 1

    def test_estadisticas_multiples_encuestas(self, client):
        """Test statistics with multiple surveys."""
        # Survey 1: age 30, stratum 2
        survey1 = valid_survey_data.copy()
        survey1["encuestado"] = survey1["encuestado"].copy()
        survey1["encuestado"]["edad"] = 30
        survey1["encuestado"]["estrato"] = 2
        
        # Survey 2: age 40, stratum 3
        survey2 = valid_survey_data.copy()
        survey2["encuestado"] = survey2["encuestado"].copy()
        survey2["encuestado"]["edad"] = 40
        survey2["encuestado"]["estrato"] = 3
        
        client.post("/encuestas/", json=survey1)
        client.post("/encuestas/", json=survey2)
        
        response = client.get("/encuestas/estadisticas/")
        assert response.status_code == 200
        data = response.json()
        assert data["total_encuestas"] == 2
        assert data["edad_promedio"] == 35.0
        assert data["distribucion_por_estrato"]["2"] == 1
        assert data["distribucion_por_estrato"]["3"] == 1

    def test_estadisticas_distribucion_estrato(self, client):
        """Test stratum distribution calculation."""
        # Create 5 surveys with different strata
        for estrato in [1, 1, 2, 2, 2]:
            survey = valid_survey_data.copy()
            survey["encuestado"] = survey["encuestado"].copy()
            survey["encuestado"]["estrato"] = estrato
            client.post("/encuestas/", json=survey)
        
        response = client.get("/encuestas/estadisticas/")
        data = response.json()
        assert data["distribucion_por_estrato"]["1"] == 2
        assert data["distribucion_por_estrato"]["2"] == 3

    @pytest.mark.asyncio
    def test_estadisticas_endpoint_async(self, client):
        """Test that estadisticas endpoint is async (response is correct)."""
        response = client.get("/encuestas/estadisticas/")
        assert response.status_code == 200
        # The endpoint is async def, but TestClient handles it properly


class TestErrorHandling:
    """Tests for error handling."""

    def test_validation_error_estructura(self, client):
        """Test that validation errors have proper structure."""
        invalid_data = {
            "id": 0,
            "encuestado": {
                "nombre": "Test",
                "edad": 150,
                "estrato": 7,
                "departamento": "InvalidoDepartamento"
            },
            "respuestas": []
        }
        
        response = client.post("/encuestas/", json=invalid_data)
        assert response.status_code == 422
        
        data = response.json()
        assert "error" in data
        assert "message" in data
        assert "details" in data
        assert len(data["details"]) > 0
        
        # Check detail structure
        for detail in data["details"]:
            assert "field" in detail
            assert "value" in detail
            assert "reason" in detail

    def test_falta_campo_requerido(self, client):
        """Test that missing required fields are caught."""
        incomplete_data = {
            "id": 0,
            "encuestado": {
                "nombre": "Test",
                "edad": 30
                # Missing estrato and departamento
            },
            "respuestas": []
        }
        
        response = client.post("/encuestas/", json=incomplete_data)
        assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
