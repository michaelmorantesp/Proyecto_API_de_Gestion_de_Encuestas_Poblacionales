"""
Tests for Pydantic models.

This module contains unit tests for validating:
- Model structure and fields
- Field validators (mode='before' and mode='after')
- Nested model relationships
- JSON schema generation
"""

import pytest
from pydantic import ValidationError

from models import Encuestado, RespuestaEncuesta, EncuestaCompleta, EstadisticasEncuestas


class TestEncuestado:
    """Tests for Encuestado model."""

    def test_encuestado_valido(self):
        """Test creating a valid Encuestado."""
        encuestado = Encuestado(
            nombre="Juan Pérez",
            edad=35,
            estrato=3,
            departamento="Cundinamarca"
        )
        assert encuestado.nombre == "Juan Pérez"
        assert encuestado.edad == 35
        assert encuestado.estrato == 3
        assert encuestado.departamento == "Cundinamarca"

    def test_edad_valida_rango(self):
        """Test that edad validates between 0 and 120."""
        # Valid ages
        Encuestado(nombre="Test", edad=0, estrato=1, departamento="Cundinamarca")
        Encuestado(nombre="Test", edad=120, estrato=1, departamento="Cundinamarca")
        
        # Invalid ages
        with pytest.raises(ValidationError):
            Encuestado(nombre="Test", edad=-1, estrato=1, departamento="Cundinamarca")
        
        with pytest.raises(ValidationError):
            Encuestado(nombre="Test", edad=121, estrato=1, departamento="Cundinamarca")

    def test_estrato_valido_rango(self):
        """Test that estrato validates between 1 and 6."""
        # Valid strata
        for estrato in range(1, 7):
            Encuestado(nombre="Test", edad=25, estrato=estrato, departamento="Cundinamarca")
        
        # Invalid strata
        with pytest.raises(ValidationError):
            Encuestado(nombre="Test", edad=25, estrato=0, departamento="Cundinamarca")
        
        with pytest.raises(ValidationError):
            Encuestado(nombre="Test", edad=25, estrato=7, departamento="Cundinamarca")

    def test_departamento_valido(self):
        """Test that departamento accepts valid Colombian departments."""
        # Valid departments
        Encuestado(nombre="Test", edad=25, estrato=1, departamento="Antioquia")
        Encuestado(nombre="Test", edad=25, estrato=1, departamento="Bogotá")
        
        # Invalid department
        with pytest.raises(ValidationError):
            Encuestado(nombre="Test", edad=25, estrato=1, departamento="InvalidoDepartamento")

    def test_departamento_whitespace_normalization(self):
        """Test that departamento is normalized (whitespace stripped)."""
        encuestado = Encuestado(
            nombre="Test",
            edad=25,
            estrato=1,
            departamento="  Antioquia  "  # With extra whitespace
        )
        assert encuestado.departamento == "Antioquia"

    def test_nombre_whitespace_normalization(self):
        """Test that nombre is normalized (whitespace stripped)."""
        encuestado = Encuestado(
            nombre="  Juan Pérez  ",
            edad=25,
            estrato=1,
            departamento="Cundinamarca"
        )
        assert encuestado.nombre == "Juan Pérez"

    def test_encuestado_json_schema_example(self):
        """Test that JSON schema example is configured."""
        schema = Encuestado.model_json_schema()
        assert "example" in schema
        assert schema["example"]["nombre"] == "Juan Pérez García"


class TestRespuestaEncuesta:
    """Tests for RespuestaEncuesta model."""

    def test_respuesta_likert_valida(self):
        """Test that Likert scale responses (1-5) are valid."""
        for score in range(1, 6):
            respuesta = RespuestaEncuesta(
                pregunta="¿Satisfecho?",
                respuesta=score
            )
            assert respuesta.respuesta == score

    def test_respuesta_likert_invalida(self):
        """Test that invalid Likert scores are rejected."""
        with pytest.raises(ValidationError):
            RespuestaEncuesta(pregunta="¿Satisfecho?", respuesta=0)
        
        with pytest.raises(ValidationError):
            RespuestaEncuesta(pregunta="¿Satisfecho?", respuesta=6)

    def test_respuesta_porcentaje_valida(self):
        """Test that percentage responses (0.0-100.0) are valid."""
        RespuestaEncuesta(pregunta="¿Porcentaje?", respuesta=0.0)
        RespuestaEncuesta(pregunta="¿Porcentaje?", respuesta=50.5)
        RespuestaEncuesta(pregunta="¿Porcentaje?", respuesta=100.0)

    def test_respuesta_porcentaje_invalida(self):
        """Test that invalid percentages are rejected."""
        with pytest.raises(ValidationError):
            RespuestaEncuesta(pregunta="¿Porcentaje?", respuesta=-0.1)
        
        with pytest.raises(ValidationError):
            RespuestaEncuesta(pregunta="¿Porcentaje?", respuesta=100.1)

    def test_respuesta_texto_valida(self):
        """Test that text responses are valid."""
        respuesta = RespuestaEncuesta(
            pregunta="¿Comentario?",
            respuesta="Excelente servicio"
        )
        assert respuesta.respuesta == "Excelente servicio"

    def test_respuesta_comentario_opcional(self):
        """Test that comentario is optional."""
        respuesta = RespuestaEncuesta(
            pregunta="Pregunta",
            respuesta=4
            # comentario not provided
        )
        assert respuesta.comentario is None

    def test_respuesta_con_comentario(self):
        """Test respuesta with comentario."""
        respuesta = RespuestaEncuesta(
            pregunta="Pregunta",
            respuesta=4,
            comentario="Buen servicio"
        )
        assert respuesta.comentario == "Buen servicio"

    def test_pregunta_whitespace_normalization(self):
        """Test that pregunta is normalized (whitespace stripped)."""
        respuesta = RespuestaEncuesta(
            pregunta="  ¿Pregunta?  ",
            respuesta=3
        )
        assert respuesta.pregunta == "¿Pregunta?"


class TestEncuestaCompleta:
    """Tests for EncuestaCompleta model."""

    def test_encuesta_completa_valida(self):
        """Test creating a valid complete survey."""
        encuesta = EncuestaCompleta(
            id=1,
            encuestado=Encuestado(
                nombre="Test",
                edad=30,
                estrato=3,
                departamento="Cundinamarca"
            ),
            respuestas=[
                RespuestaEncuesta(pregunta="Q1", respuesta=4),
                RespuestaEncuesta(pregunta="Q2", respuesta=75.5)
            ]
        )
        assert encuesta.id == 1
        assert encuesta.encuestado.nombre == "Test"
        assert len(encuesta.respuestas) == 2

    def test_encuesta_respuestas_vacia(self):
        """Test survey with empty respuestas list."""
        encuesta = EncuestaCompleta(
            id=1,
            encuestado=Encuestado(
                nombre="Test",
                edad=30,
                estrato=3,
                departamento="Cundinamarca"
            ),
            respuestas=[]
        )
        assert len(encuesta.respuestas) == 0

    def test_encuesta_validacion_anidada(self):
        """Test that nested model validation is enforced."""
        with pytest.raises(ValidationError):
            EncuestaCompleta(
                id=1,
                encuestado=Encuestado(
                    nombre="Test",
                    edad=150,  # Invalid
                    estrato=3,
                    departamento="Cundinamarca"
                ),
                respuestas=[]
            )

    def test_encuesta_respuesta_invalida_en_lista(self):
        """Test that invalid respuestas in list are caught."""
        with pytest.raises(ValidationError):
            EncuestaCompleta(
                id=1,
                encuestado=Encuestado(
                    nombre="Test",
                    edad=30,
                    estrato=3,
                    departamento="Cundinamarca"
                ),
                respuestas=[
                    RespuestaEncuesta(pregunta="Q1", respuesta=4),
                    RespuestaEncuesta(pregunta="Q2", respuesta=500)  # Invalid percentage
                ]
            )

    def test_encuesta_json_schema_example(self):
        """Test that JSON schema example is configured."""
        schema = EncuestaCompleta.model_json_schema()
        assert "example" in schema
        assert schema["example"]["id"] == 1


class TestEstadisticasEncuestas:
    """Tests for EstadisticasEncuestas model."""

    def test_estadisticas_validas(self):
        """Test creating valid statistics model."""
        stats = EstadisticasEncuestas(
            total_encuestas=10,
            edad_promedio=35.5,
            distribucion_por_estrato={"1": 2, "2": 3, "3": 5}
        )
        assert stats.total_encuestas == 10
        assert stats.edad_promedio == 35.5
        assert stats.distribucion_por_estrato["1"] == 2

    def test_estadisticas_cero_encuestas(self):
        """Test statistics with zero surveys."""
        stats = EstadisticasEncuestas(
            total_encuestas=0,
            edad_promedio=0.0,
            distribucion_por_estrato={}
        )
        assert stats.total_encuestas == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
