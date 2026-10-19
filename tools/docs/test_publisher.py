"""Pruebas automatizadas para el conversor, cliente Confluence y publicador.

Valida:
1. Autenticación HTTP Basic con API Token personal en ambos modos:
   - Sin ámbitos (unscoped): contra https://{site}/wiki/api/v2
   - Con ámbitos (scoped): contra https://api.atlassian.com/ex/confluence/{cloudId}/wiki/api/v2
   - Verificación estricta de cabecera 'Basic base64(email:token)' (NUNCA Bearer)
   - Redacción de secretos y credenciales en excepciones y mensajes de error
2. Falla temprana y explícita ante Markdown no soportado o malformado:
   - Bloques de código no cerrados
   - Tablas malformadas (separador inválido o número de columnas inconsistente)
   - HTML embebido (<div...>, <script...>)
   - Listas de tareas (- [ ])
   - Fórmulas matemáticas ($ / $$)
   - Comillas invertidas de código en línea sin cerrar
3. Flujo del publicador, control de estado local, idempotencia y seguridad documental.
"""

from __future__ import annotations

import base64
import io
import json
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import MagicMock, patch

from confluence_client import ConfluenceAPIError, ConfluenceClient
from markdown_to_storage import markdown_to_storage, validate_storage_xml
from publisher import calculate_hash, load_state, save_state


class FakeResponse:
    def __init__(self, data_dict: dict):
        self._data = json.dumps(data_dict).encode("utf-8")

    def read(self) -> bytes:
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class TestAuthenticationModesAndSecurity(unittest.TestCase):
    """Comprueba que ambos modos de API Token personal utilicen HTTP Basic y la URL adecuada."""

    def test_unscoped_personal_api_token_uses_basic_and_site_url(self):
        """Verifica que el modo unscoped use HTTP Basic con correo y la URL directa del sitio."""
        email = "investigador@unitru.edu.pe"
        token = "token_unscoped_secreto_123"
        client = ConfluenceClient(
            site_domain="unitru-team-hpj93f6y.atlassian.net",
            email=email,
            api_token=token,
            token_type="unscoped",
        )

        self.assertEqual(
            client.base_url,
            "https://unitru-team-hpj93f6y.atlassian.net/wiki/api/v2",
        )

        expected_b64 = base64.b64encode(f"{email}:{token}".encode("utf-8")).decode("ascii")
        expected_auth_header = f"Basic {expected_b64}"

        captured_requests = []

        def fake_urlopen(req, timeout=15):
            captured_requests.append(req)
            return FakeResponse({"id": "2097153", "title": "Raiz", "spaceId": "54321"})

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            res = client.get_page("2097153")

        self.assertEqual(len(captured_requests), 1)
        sent_req = captured_requests[0]
        self.assertEqual(
            sent_req.full_url,
            "https://unitru-team-hpj93f6y.atlassian.net/wiki/api/v2/pages/2097153?body-format=storage",
        )
        auth_header = sent_req.headers.get("Authorization")
        self.assertEqual(auth_header, expected_auth_header)
        self.assertFalse(auth_header.startswith("Bearer"))

    def test_scoped_personal_api_token_uses_basic_and_atlassian_api_url(self):
        """Verifica que el modo scoped use HTTP Basic con correo y la URL oficial api.atlassian.com/ex/confluence/{cloudId}."""
        email = "investigador@unitru.edu.pe"
        token = "token_scoped_secreto_456"
        cloud_id = "11c5602c-78c2-4910-b6ad-b839e136bcaa"

        client = ConfluenceClient(
            site_domain="unitru-team-hpj93f6y.atlassian.net",
            email=email,
            api_token=token,
            token_type="scoped",
            cloud_id=cloud_id,
        )

        self.assertEqual(
            client.base_url,
            f"https://api.atlassian.com/ex/confluence/{cloud_id}/wiki/api/v2",
        )

        expected_b64 = base64.b64encode(f"{email}:{token}".encode("utf-8")).decode("ascii")
        expected_auth_header = f"Basic {expected_b64}"

        captured_requests = []

        def fake_urlopen(req, timeout=15):
            captured_requests.append(req)
            return FakeResponse({"id": "2097153", "title": "Raiz", "spaceId": "54321"})

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            res = client.get_page("2097153")

        self.assertEqual(len(captured_requests), 1)
        sent_req = captured_requests[0]
        self.assertEqual(
            sent_req.full_url,
            f"https://api.atlassian.com/ex/confluence/{cloud_id}/wiki/api/v2/pages/2097153?body-format=storage",
        )
        auth_header = sent_req.headers.get("Authorization")
        self.assertEqual(auth_header, expected_auth_header)
        self.assertFalse(auth_header.startswith("Bearer"))

    def test_email_is_mandatory_for_both_modes(self):
        """Verifica que ambos modos exijan el correo electrónico para HTTP Basic."""
        with self.assertRaises(ValueError):
            ConfluenceClient(
                site_domain="example.atlassian.net",
                email="",
                api_token="token_valido",
                token_type="unscoped",
            )

        with self.assertRaises(ValueError):
            ConfluenceClient(
                site_domain="example.atlassian.net",
                email="",
                api_token="token_valido",
                token_type="scoped",
                cloud_id="12345",
            )

    def test_token_redacted_on_error(self):
        """Verifica que el token y correo nunca se registren o impriman en mensajes de error."""
        email = "dev@example.com"
        token = "super_secret_personal_token_999"
        client = ConfluenceClient(
            site_domain="example.atlassian.net",
            email=email,
            api_token=token,
            token_type="unscoped",
        )

        error_bytes = f'{{"error": "Invalid token {token} for user {email}"}}'.encode("utf-8")
        mock_http_error = urllib.error.HTTPError(
            url="https://example.atlassian.net/wiki/api/v2/pages/12345",
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=io.BytesIO(error_bytes),
        )

        with patch("urllib.request.urlopen", side_effect=mock_http_error):
            with self.assertRaises(ConfluenceAPIError) as ctx:
                client.get_page("12345")

            error_msg = str(ctx.exception)
            self.assertNotIn(token, error_msg)
            self.assertIn("[REDACTED_API_TOKEN]", error_msg)
            self.assertIn("[USER_EMAIL]", error_msg)


class TestMarkdownConversionAndStrictValidation(unittest.TestCase):
    """Valida la conversión de test_page.md y la falla temprana ante Markdown no soportado."""

    def test_valid_page_conversion(self):
        """Verifica que el Markdown válido de prueba se convierta y pase la validación XML."""
        test_file = Path(__file__).resolve().parent / "test_page.md"
        with open(test_file, "r", encoding="utf-8") as f:
            md_text = f.read()

        title, storage = markdown_to_storage(md_text)
        self.assertEqual(title, "Prueba de publicación automática — GDP")
        self.assertIn("<h1>Prueba de publicación automática — GDP</h1>", storage)
        self.assertIn("<table><thead><tr>", storage)
        self.assertIn('<ac:structured-macro ac:name="code"', storage)
        self.assertIn("<blockquote><p>", storage)
        # Debe ser XML estrictamente válido
        validate_storage_xml(storage)

    def test_unclosed_code_block_fails(self):
        """Verifica que falle claramente si un bloque de código cercado no se cierra."""
        md = "# Titulo\n\n```python\nprint('codigo sin cierre')\n"
        with self.assertRaises(ValueError) as ctx:
            markdown_to_storage(md)
        self.assertIn("bloque de código cercado", str(ctx.exception).lower())

    def test_malformed_table_separator_fails(self):
        """Verifica que falle si la tabla tiene un separador inválido."""
        md = "# Titulo\n\n| Col 1 | Col 2 |\n| texto | sin guiones |\n| A | B |\n"
        with self.assertRaises(ValueError) as ctx:
            markdown_to_storage(md)
        self.assertIn("tabla", str(ctx.exception).lower())

    def test_table_column_mismatch_fails(self):
        """Verifica que falle si las filas de datos tienen más o menos columnas que la cabecera."""
        md = "# Titulo\n\n| Col 1 | Col 2 |\n| --- | --- |\n| Solo una columna |\n"
        with self.assertRaises(ValueError) as ctx:
            markdown_to_storage(md)
        self.assertIn("inconsistente", str(ctx.exception).lower())

    def test_embedded_raw_html_fails(self):
        """Verifica que falle si se introducen etiquetas HTML embebidas no soportadas."""
        md = "# Titulo\n\n<div class='custom'>Contenido HTML</div>\n"
        with self.assertRaises(ValueError) as ctx:
            markdown_to_storage(md)
        self.assertIn("etiqueta html embebida", str(ctx.exception).lower())

    def test_unsupported_task_lists_fails(self):
        """Verifica que falle ante listas de tareas (- [ ])."""
        md = "# Titulo\n\n- [ ] Tarea pendiente por hacer\n"
        with self.assertRaises(ValueError) as ctx:
            markdown_to_storage(md)
        self.assertIn("listas de tareas", str(ctx.exception).lower())

    def test_unsupported_math_delimiters_fails(self):
        """Verifica que falle ante sintaxis matemática ($ / $$)."""
        md = "# Titulo\n\nEcuación: $$x^2 + y^2 = z^2$$\n"
        with self.assertRaises(ValueError) as ctx:
            markdown_to_storage(md)
        self.assertIn("matemáticas", str(ctx.exception).lower())

    def test_unclosed_inline_backtick_fails(self):
        """Verifica que falle ante comillas invertidas de código en línea sin cerrar."""
        md = "# Titulo\n\nParrafo con `codigo en linea sin cerrar\n"
        with self.assertRaises(ValueError) as ctx:
            markdown_to_storage(md)
        self.assertIn("comilla invertida", str(ctx.exception).lower())


class TestPublisherWorkflow(unittest.TestCase):
    """Pruebas del flujo completo del publicador (dry-run, publicación, idempotencia)."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.state_file = Path(self.temp_dir.name) / ".confluence_state.json"
        self.doc_file = Path(self.temp_dir.name) / "doc.md"
        self.doc_file.write_text("# Prueba\n\nContenido de prueba.\n", encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_dry_run_new_page(self):
        """Valida que dry-run reporte acción de creación sin llamar a create_page ni escribir estado."""
        from publisher import main
        import sys

        test_args = [
            "publisher.py",
            "--dry-run",
            "--root-id", "2097153",
            "--file", str(self.doc_file),
            "--state-file", str(self.state_file),
            "--email", "dev@example.com",
            "--token", "dummy_token",
        ]
        with patch.object(sys, "argv", test_args):
            with patch("publisher.ConfluenceClient") as mock_client_cls:
                mock_inst = MagicMock()
                mock_inst.base_url = "https://unitru-team-hpj93f6y.atlassian.net/wiki/api/v2"
                mock_inst.get_page.return_value = {"title": "GDP Raiz", "spaceId": "54321", "version": {"number": 1}}
                mock_inst.search_pages_by_title.return_value = []
                mock_client_cls.return_value = mock_inst

                with self.assertRaises(SystemExit) as exit_ctx:
                    main()
                self.assertEqual(exit_ctx.exception.code, 0)
                mock_inst.create_page.assert_not_called()
                mock_inst.update_page.assert_not_called()
                self.assertFalse(self.state_file.exists())

    def test_safety_check_orphan_page(self):
        """Valida que aborte si existe una página con el mismo título sin registrar en estado local."""
        from publisher import main
        import sys

        test_args = [
            "publisher.py",
            "--publish",
            "--root-id", "2097153",
            "--file", str(self.doc_file),
            "--state-file", str(self.state_file),
            "--email", "dev@example.com",
            "--token", "dummy_token",
        ]
        with patch.object(sys, "argv", test_args):
            with patch("publisher.ConfluenceClient") as mock_client_cls:
                mock_inst = MagicMock()
                mock_inst.base_url = "https://unitru-team-hpj93f6y.atlassian.net/wiki/api/v2"
                mock_inst.get_page.return_value = {"title": "GDP Raiz", "spaceId": "54321", "version": {"number": 1}}
                mock_inst.search_pages_by_title.return_value = [{"id": "88888", "title": "Prueba"}]
                mock_client_cls.return_value = mock_inst

                with self.assertRaises(SystemExit) as exit_ctx:
                    main()
                self.assertEqual(exit_ctx.exception.code, 1)
                mock_inst.create_page.assert_not_called()
                mock_inst.update_page.assert_not_called()

    def test_idempotent_skip_when_content_identical(self):
        """Valida que si el hash coincide, omite la actualización sin llamar a la API."""
        from publisher import main
        from markdown_to_storage import markdown_to_storage
        import sys

        _, storage_xml = markdown_to_storage(self.doc_file.read_text(encoding="utf-8"))
        chash = calculate_hash(storage_xml)

        save_state(self.state_file, {
            "page_id": "77777",
            "space_id": "54321",
            "root_id": "2097153",
            "title": "Prueba",
            "content_sha256": chash,
            "version": 3,
        })

        test_args = [
            "publisher.py",
            "--publish",
            "--root-id", "2097153",
            "--file", str(self.doc_file),
            "--state-file", str(self.state_file),
            "--email", "dev@example.com",
            "--token", "dummy_token",
        ]
        with patch.object(sys, "argv", test_args):
            with patch("publisher.ConfluenceClient") as mock_client_cls:
                mock_inst = MagicMock()
                mock_inst.base_url = "https://unitru-team-hpj93f6y.atlassian.net/wiki/api/v2"
                mock_inst.get_page.side_effect = [
                    {"title": "GDP Raiz", "spaceId": "54321", "version": {"number": 1}},
                    {"title": "Prueba", "spaceId": "54321", "version": {"number": 3}},
                ]
                mock_client_cls.return_value = mock_inst

                with self.assertRaises(SystemExit) as exit_ctx:
                    main()
                self.assertEqual(exit_ctx.exception.code, 0)
                mock_inst.update_page.assert_not_called()

    def test_root_overwrite_prevention(self):
        """Verifica que el publicador aborte si el ID registrado coincide con la raíz."""
        from publisher import main
        import sys

        save_state(self.state_file, {
            "page_id": "2097153",
            "space_id": "12345",
            "root_id": "2097153",
            "title": "Prueba",
        })

        test_args = [
            "publisher.py",
            "--publish",
            "--root-id", "2097153",
            "--file", str(self.doc_file),
            "--state-file", str(self.state_file),
            "--email", "dev@example.com",
            "--token", "dummy_token",
        ]
        with patch.object(sys, "argv", test_args):
            with patch("publisher.ConfluenceClient") as mock_client_cls:
                mock_inst = MagicMock()
                mock_inst.base_url = "https://unitru-team-hpj93f6y.atlassian.net/wiki/api/v2"
                mock_inst.get_page.return_value = {"title": "Raiz", "spaceId": "12345", "version": {"number": 1}}
                mock_client_cls.return_value = mock_inst

                with self.assertRaises(SystemExit) as exit_ctx:
                    main()
                self.assertEqual(exit_ctx.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
