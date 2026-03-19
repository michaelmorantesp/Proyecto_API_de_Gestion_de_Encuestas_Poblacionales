"""
tests/test_models.py — Tests unitarios para los modelos Pydantic.

Los tests unitarios verifican piezas pequeñas del sistema en aislamiento.
Aquí probamos que los modelos Pydantic validan correctamente los datos
sin levantar el servidor FastAPI.

Para correr estos tests: pytest tests/test_models.py -v
"""

# pytest es el framework de testing que usamos.
# 'pytest.raises' captura excepciones esperadas dentro de los tests.
import pytest

# ValidationError es la excepción que lanza Pydantic cuando un modelo
# recibe datos que no cumplen las reglas de validación.
from pydantic import ValidationError

# Importamos los modelos que vamos a probar
from models import Encuestado, RespuestaEncuesta, EncuestaCompleta, EstadisticasEncuestas


# ============================================================================
# TESTS PARA EL MODELO Encuestado
# ============================================================================

class TestEncuestado:
    """
    Agrupa todos los tests relacionados con el modelo Encuestado.
    Agrupar tests en clases organiza el código y facilita correr solo
    un grupo con: pytest tests/test_models.py::TestEncuestado -v
    """

    def test_encuestado_valido(self):
        """
        Verifica que se puede crear un Encuestado con datos completamente válidos.
        Este es el 'happy path': el caso de uso normal y esperado.
        """
        # Creamos un Encuestado con todos los campos dentro de rango
        encuestado = Encuestado(
            nombre="Juan Pérez",
            edad=35,
            estrato=3,
            departamento="Cundinamarca"
        )

        # Verificamos que cada campo fue almacenado correctamente
        assert encuestado.nombre == "Juan Pérez"    # assert falla el test si la condición es False
        assert encuestado.edad == 35
        assert encuestado.estrato == 3
        assert encuestado.departamento == "Cundinamarca"

    def test_edad_valida_rango(self):
        """
        Verifica el rango completo del validador de edad:
        - Los valores límite (0 y 120) deben ser aceptados
        - Los valores fuera de rango (-1 y 121) deben ser rechazados
        Probar los valores límite es una buena práctica en testing (boundary testing).
        """

        # Casos válidos: los extremos del rango permitido deben funcionar
        Encuestado(nombre="Test", edad=0, estrato=1, departamento="Cundinamarca")    # Límite inferior
        Encuestado(nombre="Test", edad=120, estrato=1, departamento="Cundinamarca")  # Límite superior

        # Casos inválidos: esperamos que Pydantic lance ValidationError
        # pytest.raises actúa como un "try/except" para tests:
        # el test PASA si la excepción se lanza, FALLA si no se lanza
        with pytest.raises(ValidationError):
            Encuestado(nombre="Test", edad=-1, estrato=1, departamento="Cundinamarca")

        with pytest.raises(ValidationError):
            Encuestado(nombre="Test", edad=121, estrato=1, departamento="Cundinamarca")

    def test_estrato_valido_rango(self):
        """
        Verifica que el estrato acepta los 6 valores válidos (1-6)
        y rechaza los que están fuera (0 y 7).
        """

        # Probamos los 6 estratos válidos usando un bucle
        for estrato in range(1, 7):  # range(1, 7) genera 1, 2, 3, 4, 5, 6
            Encuestado(nombre="Test", edad=25, estrato=estrato, departamento="Cundinamarca")

        # Verificamos que los extremos inválidos son rechazados
        with pytest.raises(ValidationError):
            Encuestado(nombre="Test", edad=25, estrato=0, departamento="Cundinamarca")  # Debajo del mínimo

        with pytest.raises(ValidationError):
            Encuestado(nombre="Test", edad=25, estrato=7, departamento="Cundinamarca")  # Encima del máximo

    def test_departamento_valido(self):
        """
        Verifica que el validador de departamento acepta valores de la lista oficial
        y rechaza nombres que no existen en Colombia.
        """

        # Probamos dos departamentos válidos de distintas regiones
        Encuestado(nombre="Test", edad=25, estrato=1, departamento="Antioquia")
        Encuestado(nombre="Test", edad=25, estrato=1, departamento="Bogotá")  # Alias que añadimos al fix

        # Un nombre que no es departamento colombiano debe ser rechazado
        with pytest.raises(ValidationError):
            Encuestado(nombre="Test", edad=25, estrato=1, departamento="InvalidoDepartamento")

    def test_departamento_whitespace_normalization(self):
        """
        Verifica que el validador de departamento (mode='before') elimina
        los espacios al inicio y al final del string antes de validar.

        Esto es importante para ser tolerantes con errores tipográficos del usuario.
        """
        encuestado = Encuestado(
            nombre="Test",
            edad=25,
            estrato=1,
            departamento="  Antioquia  "   # Espacios extra intencionales
        )

        # El valor almacenado debe estar limpio, sin espacios
        assert encuestado.departamento == "Antioquia"

    def test_nombre_whitespace_normalization(self):
        """
        Verifica que el validador de nombre (mode='before') también
        elimina espacios extra al principio y al final.
        """
        encuestado = Encuestado(
            nombre="  Juan Pérez  ",    # Espacios extra intencionales
            edad=25,
            estrato=1,
            departamento="Cundinamarca"
        )

        # El nombre debe quedar sin espacios extremos
        assert encuestado.nombre == "Juan Pérez"

    def test_encuestado_json_schema_example(self):
        """
        Verifica que el modelo tiene configurado el ejemplo JSON en el schema.
        Este ejemplo aparece en la documentación Swagger (/docs) y
        en ReDoc (/redoc), ayudando a los consumidores de la API a entender
        qué formato se espera.
        """
        # model_json_schema() genera el esquema JSON completo del modelo
        schema = Encuestado.model_json_schema()

        # Verificamos que existe la clave "example" en el schema
        assert "example" in schema

        # Verificamos que el ejemplo tiene los valores correctos que definimos en models.py
        assert schema["example"]["nombre"] == "Juan Pérez García"


# ============================================================================
# TESTS PARA EL MODELO RespuestaEncuesta
# ============================================================================

class TestRespuestaEncuesta:
    """Tests para el modelo de respuesta individual de encuesta."""

    def test_respuesta_likert_valida(self):
        """
        Verifica que todos los valores válidos de escala Likert (1 al 5) son aceptados.
        Probamos los 5 valores, no solo uno, para máxima cobertura.
        """
        for score in range(1, 6):   # Genera 1, 2, 3, 4, 5
            respuesta = RespuestaEncuesta(
                pregunta="¿Satisfecho?",
                respuesta=score     # Cada iteración usa un valor diferente
            )
            # Verificamos que el valor se almacenó tal cual (sin modificaciones)
            assert respuesta.respuesta == score

    def test_respuesta_likert_invalida(self):
        """
        Verifica que los valores fuera del rango Likert (0 y 6) son rechazados.
        0 es demasiado bajo, 6 es demasiado alto.
        """
        with pytest.raises(ValidationError):
            RespuestaEncuesta(pregunta="¿Satisfecho?", respuesta=0)  # Demasiado bajo

        with pytest.raises(ValidationError):
            RespuestaEncuesta(pregunta="¿Satisfecho?", respuesta=6)  # Demasiado alto

    def test_respuesta_porcentaje_valida(self):
        """
        Verifica que los floats entre 0.0 y 100.0 son aceptados como porcentajes.
        Probamos el límite inferior, un valor medio y el límite superior.
        """
        RespuestaEncuesta(pregunta="¿Porcentaje?", respuesta=0.0)    # Límite inferior
        RespuestaEncuesta(pregunta="¿Porcentaje?", respuesta=50.5)   # Valor intermedio
        RespuestaEncuesta(pregunta="¿Porcentaje?", respuesta=100.0)  # Límite superior

    def test_respuesta_porcentaje_invalida(self):
        """
        Verifica que los porcentajes fuera de rango son rechazados.
        -0.1 está debajo de 0, 100.1 está encima de 100.
        """
        with pytest.raises(ValidationError):
            RespuestaEncuesta(pregunta="¿Porcentaje?", respuesta=-0.1)

        with pytest.raises(ValidationError):
            RespuestaEncuesta(pregunta="¿Porcentaje?", respuesta=100.1)

    def test_respuesta_texto_valida(self):
        """
        Verifica que las respuestas de texto libre siempre son aceptadas.
        Los strings no tienen restricciones de rango.
        """
        respuesta = RespuestaEncuesta(
            pregunta="¿Comentario?",
            respuesta="Excelente servicio"
        )
        # Verificamos que el texto se almacenó exactamente como se envió
        assert respuesta.respuesta == "Excelente servicio"

    def test_respuesta_comentario_opcional(self):
        """
        Verifica que el campo 'comentario' es opcional (Optional[str]).
        Cuando no se proporciona, debe almacenarse como None.
        """
        respuesta = RespuestaEncuesta(
            pregunta="Pregunta",
            respuesta=4
            # Intencionalmente omitimos 'comentario' para probar que es opcional
        )

        # Si comentario es Optional[str] = None, debe ser None cuando no se pasa
        assert respuesta.comentario is None

    def test_respuesta_con_comentario(self):
        """
        Verifica que el comentario se almacena correctamente cuando sí se proporciona.
        """
        respuesta = RespuestaEncuesta(
            pregunta="Pregunta",
            respuesta=4,
            comentario="Buen servicio"
        )
        assert respuesta.comentario == "Buen servicio"

    def test_pregunta_whitespace_normalization(self):
        """
        Verifica que el validador de pregunta (mode='before') limpia espacios extra.
        """
        respuesta = RespuestaEncuesta(
            pregunta="  ¿Pregunta?  ",  # Espacios extra
            respuesta=3
        )
        # La pregunta debe estar sin espacios al inicio ni al final
        assert respuesta.pregunta == "¿Pregunta?"


# ============================================================================
# TESTS PARA EL MODELO EncuestaCompleta
# ============================================================================

class TestEncuestaCompleta:
    """Tests para el modelo contenedor que anida Encuestado y lista de respuestas."""

    def test_encuesta_completa_valida(self):
        """
        Verifica que se puede construir una encuesta completa con
        datos válidos en todos sus niveles anidados.
        """
        # Creamos el modelo anidado completo: EncuestaCompleta contiene
        # un Encuestado y una lista de RespuestaEncuesta
        encuesta = EncuestaCompleta(
            id=1,
            encuestado=Encuestado(
                nombre="Test",
                edad=30,
                estrato=3,
                departamento="Cundinamarca"
            ),
            respuestas=[
                RespuestaEncuesta(pregunta="Q1", respuesta=4),   # Likert
                RespuestaEncuesta(pregunta="Q2", respuesta=75.5) # Porcentaje
            ]
        )

        # Verificamos el ID, el campo anidado y la cantidad de respuestas
        assert encuesta.id == 1
        assert encuesta.encuestado.nombre == "Test"  # Acceso a campo de modelo anidado
        assert len(encuesta.respuestas) == 2          # Lista tiene 2 elementos

    def test_encuesta_respuestas_vacia(self):
        """
        Verifica que una encuesta con lista de respuestas vacía es válida.
        El sistema debe aceptar encuestas sin respuestas (List[] puede estar vacía).
        """
        encuesta = EncuestaCompleta(
            id=1,
            encuestado=Encuestado(
                nombre="Test",
                edad=30,
                estrato=3,
                departamento="Cundinamarca"
            ),
            respuestas=[]   # Lista vacía — debe ser válido
        )
        assert len(encuesta.respuestas) == 0

    def test_encuesta_validacion_anidada(self):
        """
        Verifica que la validación se propaga en los modelos anidados.
        Si el Encuestado tiene una edad inválida, toda la EncuestaCompleta
        debe fallar la validación (Pydantic valida recursivamente).
        """
        with pytest.raises(ValidationError):
            EncuestaCompleta(
                id=1,
                encuestado=Encuestado(
                    nombre="Test",
                    edad=150,           # Inválido: mayor que 120
                    estrato=3,
                    departamento="Cundinamarca"
                ),
                respuestas=[]
            )

    def test_encuesta_respuesta_invalida_en_lista(self):
        """
        Verifica que si una respuesta dentro de la lista es inválida,
        toda la encuesta es rechazada por Pydantic.
        """
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
                    RespuestaEncuesta(pregunta="Q1", respuesta=4),       # Válida
                    RespuestaEncuesta(pregunta="Q2", respuesta=500)      # Inválida: no es Likert ni porcentaje
                ]
            )

    def test_encuesta_json_schema_example(self):
        """
        Verifica que EncuestaCompleta tiene ejemplo JSON configurado en el schema.
        Importante para que Swagger muestre payloads de ejemplo al probar la API.
        """
        schema = EncuestaCompleta.model_json_schema()
        assert "example" in schema
        assert schema["example"]["id"] == 1


# ============================================================================
# TESTS PARA EL MODELO EstadisticasEncuestas
# ============================================================================

class TestEstadisticasEncuestas:
    """Tests para el modelo de respuesta de estadísticas."""

    def test_estadisticas_validas(self):
        """
        Verifica que se puede construir el modelo de estadísticas
        con datos completos y que los valores se almacenan correctamente.
        """
        stats = EstadisticasEncuestas(
            total_encuestas=10,
            edad_promedio=35.5,
            distribucion_por_estrato={"1": 2, "2": 3, "3": 5}  # dict con conteos por estrato
        )

        assert stats.total_encuestas == 10
        assert stats.edad_promedio == 35.5
        # Accedemos al dict con la clave "1" (string, no int)
        assert stats.distribucion_por_estrato["1"] == 2

    def test_estadisticas_cero_encuestas(self):
        """
        Verifica que el modelo acepta valores en cero cuando no hay encuestas.
        Caso borde importante para evitar errores al llamar /estadisticas/
        con el almacenamiento vacío.
        """
        stats = EstadisticasEncuestas(
            total_encuestas=0,
            edad_promedio=0.0,
            distribucion_por_estrato={}  # Diccionario vacío
        )
        assert stats.total_encuestas == 0


# ============================================================================
# EJECUCIÓN DIRECTA (opcional)
# ============================================================================

# Permite correr este archivo directamente con: python tests/test_models.py
# En lugar de usar el comando pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
