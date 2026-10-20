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

        _, storage_xml = markdown_to_storage(self.doc_file.read_text(encoding="utf-8"), str(self.doc_file))
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


class TestLinkResolver(unittest.TestCase):
    """Pruebas del resolutor de enlaces para código y documentos Confluence."""

    def setUp(self):
        self.manifest = {
            "metadata": {
                "repo_url": "https://github.com/JMarkoFlores/gemelo-digital-polinizadores",
                "documented_code_commit": "0d62f6634e1eb4a5066a2bd9e76efe2cb00fee02",
            },
            "documents": [
                {
                    "file": "docs/arquitectura.md",
                    "slug": "arquitectura",
                    "title": "Arquitectura de Software y Sistemas",
                },
                {
                    "file": "docs/api.md",
                    "slug": "api",
                    "title": "Especificación y Catálogo de la API REST",
                },
            ],
        }

    def test_resolve_code_links_to_github(self):
        """Verifica que enlaces relativos al código apunten a GitHub con commit documentado."""
        from link_resolver import resolve_markdown_links

        md = "Ver archivo [main.py](../backend/app/main.py#L10-L20) para el router."
        resolved = resolve_markdown_links(md, "docs/index.md", self.manifest)
        expected_url = (
            "https://github.com/JMarkoFlores/gemelo-digital-polinizadores/blob/"
            "0d62f6634e1eb4a5066a2bd9e76efe2cb00fee02/backend/app/main.py#L10-L20"
        )
        self.assertIn(expected_url, resolved)
        self.assertNotIn("../backend", resolved)

    def test_resolve_doc_links_to_confluence(self):
        """Verifica que enlaces a otros documentos se resuelvan al título de Confluence."""
        from markdown_to_storage import markdown_to_storage

        md = "Consultar [Arquitectura](./arquitectura.md) y [API](api.md#endpoints)."
        title, storage = markdown_to_storage(md, "docs/index.md", self.manifest)
        self.assertIn('<ri:page ri:content-title="Arquitectura de Software y Sistemas"/>', storage)
        self.assertIn('<ri:page ri:content-title="Especificación y Catálogo de la API REST"/>', storage)
        self.assertIn("<ac:link-anchor>endpoints</ac:link-anchor>", storage)
        self.assertNotIn("./arquitectura.md", storage)
        self.assertNotIn("api.md", storage)

    def test_unresolved_relative_link_fails(self):
        """Verifica que rutas relativas desconocidas lancen error inmediato."""
        from link_resolver import resolve_markdown_links

        md = "Enlace a [documento inexistente](./no_existe.md)."
        with self.assertRaises(ValueError) as ctx:
            resolve_markdown_links(md, "docs/index.md", self.manifest)
        self.assertIn("no_existe.md", str(ctx.exception))


class TestManifestAndCompatibility(unittest.TestCase):
    """Pruebas de estructura del manifiesto y matriz de compatibilidad."""

    def test_manifest_contains_exact_12_documents(self):
        """Verifica que el manifiesto contenga exactamente los 12 documentos reales de docs/."""
        manifest_file = Path(__file__).resolve().parent / "docs_manifest.json"
        self.assertTrue(manifest_file.is_file())

        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        meta = manifest.get("metadata", {})
        self.assertEqual(meta.get("root_page_id"), "2097153")
        self.assertEqual(meta.get("space_id"), "2031619")
        self.assertEqual(meta.get("test_page_id"), "2162690")
        self.assertEqual(meta.get("documented_code_commit"), "0d62f6634e1eb4a5066a2bd9e76efe2cb00fee02")

        docs = manifest.get("documents", [])
        self.assertEqual(len(docs), 12)

        # Verificar que todos los archivos existan en disco
        for doc in docs:
            fpath = Path(__file__).resolve().parent.parent.parent / doc["file"]
            self.assertTrue(fpath.is_file(), f"Archivo {doc['file']} no encontrado")
            self.assertIn(doc["status"], ["ready", "blocked"])
            self.assertEqual(doc["parent_id"], "2097153")
            self.assertEqual(doc["space_id"], "2031619")

    def test_compatibility_matrix_detection(self):
        """Verifica que los documentos con sintaxis soportada sean 'ready' y los no soportados sean 'blocked'."""
        from markdown_to_storage import check_document_compatibility

        # Documento con Mermaid soportado localmente
        mermaid_md = "# Doc\n\n```mermaid\ngraph TD\nA-->B\n```"
        compat_m = check_document_compatibility(mermaid_md, "test_mermaid.md")
        self.assertEqual(compat_m["status"], "ready")

        # Documento con Math soportado (KaTeX block / Unicode inline)
        math_md = "# Doc\n\nTexto con fórmula $x_1 \\in [40, 85]$ y bloque:\n$$f_1(X) = -x$$"
        compat_math = check_document_compatibility(math_md, "test_math.md")
        self.assertEqual(compat_math["status"], "ready")

        # Documento limpio
        clean_md = "# Doc\n\nTexto limpio con **negrita** y lista:\n- item 1\n- item 2"
        compat_clean = check_document_compatibility(clean_md, "test_clean.md")
        self.assertEqual(compat_clean["status"], "ready")

        # Documento con imagen externa no procesada -> debe ser bloqueado
        unsupported_img_md = "# Doc\n\n![Foto](https://externo.com/imagen.png)"
        compat_img = check_document_compatibility(unsupported_img_md, "test_img.md")
        self.assertEqual(compat_img["status"], "blocked")
        self.assertIn("imagen embebida no procesada", compat_img["reasons"][0])


class TestMultiDocRemoteIntegrity(unittest.TestCase):
    """Pruebas de integridad remota para el modo multi-documento."""

    def test_space_id_mismatch_aborts(self):
        """Verifica que aborte si la raíz en Confluence devuelve un spaceId distinto a 2031619."""
        from publisher import main
        import sys

        test_args = [
            "publisher.py",
            "--check",
            "--multi",
            "--email", "dev@example.com",
            "--token", "dummy_token",
        ]
        with patch.object(sys, "argv", test_args):
            with patch("publisher.ConfluenceClient") as mock_client_cls:
                mock_inst = MagicMock()
                # Simular que Confluence devuelve spaceId erróneo
                mock_inst.get_page.return_value = {"title": "Raiz", "spaceId": "9999999", "version": {"number": 1}}
                mock_client_cls.return_value = mock_inst

                with self.assertRaises(SystemExit) as exit_ctx:
                    main()
                self.assertEqual(exit_ctx.exception.code, 1)

    def test_reserved_test_page_protected(self):
        """Verifica que si un documento intenta asignarse el ID 2162690, se aborte inmediatamente."""
        from publisher import main
        import sys

        # Crear manifiesto temporal con ID de la página de prueba
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as tf:
            temp_manifest = {
                "metadata": {
                    "space_id": "2031619",
                    "root_page_id": "2097153",
                    "test_page_id": "2162690",
                },
                "documents": [
                    {
                        "file": "docs/index.md",
                        "title": "Index",
                        "page_id": "2162690",  # ID reservado de prueba!
                        "status": "ready",
                    }
                ],
            }
            json.dump(temp_manifest, tf)
            tf_path = Path(tf.name)

        try:
            test_args = [
                "publisher.py",
                "--check",
                "--multi",
                "--manifest", str(tf_path),
                "--email", "dev@example.com",
                "--token", "dummy_token",
            ]
            with patch.object(sys, "argv", test_args):
                with patch("publisher.ConfluenceClient") as mock_client_cls:
                    mock_inst = MagicMock()
                    mock_inst.get_page.side_effect = [
                        {"title": "Raiz", "spaceId": "2031619", "version": {"number": 1}},
                        {"title": "Prueba", "spaceId": "2031619", "version": {"number": 2}},
                    ]
                    mock_client_cls.return_value = mock_inst

                    with self.assertRaises(SystemExit) as exit_ctx:
                        main()
                    self.assertEqual(exit_ctx.exception.code, 1)
        finally:
            if tf_path.exists():
                tf_path.unlink()


class TestAssetRenderingAndUnicodeConversion(unittest.TestCase):
    """Pruebas de conversión matemática a Unicode y renderizado local de activos visuales."""

    def test_convert_simple_math_to_unicode_all_rules(self):
        """Verifica la conversión semántica rigurosa de todas las fórmulas inline a caracteres Unicode."""
        from asset_renderer import convert_simple_math_to_unicode

        # Comparaciones y relaciones
        self.assertEqual(convert_simple_math_to_unicode(r"\ge 8"), "≥ 8")
        self.assertEqual(convert_simple_math_to_unicode(r"\le 100\%"), "≤ 100%")
        self.assertEqual(convert_simple_math_to_unicode(r"g_1(X) \le 0"), "g₁(X) ≤ 0")
        self.assertEqual(convert_simple_math_to_unicode(r"\text{crop\_area\_pct} \in [40, 85]"), "crop_area_pct ∈ [40, 85]")

        # Operadores y unidades
        self.assertEqual(convert_simple_math_to_unicode(r"18 \times 18"), "18 × 18")
        self.assertEqual(convert_simple_math_to_unicode(r"^\circ\text{C}"), "°C")
        self.assertEqual(convert_simple_math_to_unicode(r"\sum \text{coberturas} \le 100\%"), "∑ coberturas ≤ 100%")

        # Letras griegas y subíndices
        self.assertEqual(convert_simple_math_to_unicode(r"\eta = 0.0015"), "η = 0.0015")
        self.assertEqual(convert_simple_math_to_unicode(r"\alpha_{adj} = 0.05 / (M - 1)"), "α_adj = 0.05 / (M - 1)")
        self.assertEqual(convert_simple_math_to_unicode(r"\leftrightarrow"), "↔")
        self.assertEqual(convert_simple_math_to_unicode(r"R^2"), "R²")

    def test_unsupported_latex_raises_error(self):
        """Verifica que comandos LaTeX desconocidos o inválidos lancen ValueError sin eliminar delimitadores."""
        from asset_renderer import convert_simple_math_to_unicode

        with self.assertRaises(ValueError):
            convert_simple_math_to_unicode(r"\comandoInexistenteDesconocido{abc}")

    def test_mermaid_rendering_produces_valid_png(self):
        """Verifica que el renderizado local de Mermaid genere un PNG válido no vacío con dimensiones recortadas."""
        from asset_renderer import render_mermaid_to_png
        import tempfile

        test_code = "graph TD\n    A[Inicio] --> B[Fin]"
        with tempfile.TemporaryDirectory() as td:
            meta = render_mermaid_to_png(test_code, "test-mermaid.png", output_dir=Path(td))
            self.assertEqual(meta["filename"], "test-mermaid.png")
            self.assertTrue(Path(meta["path"]).is_file())
            self.assertGreater(meta["size_bytes"], 1000)
            self.assertEqual(meta["content_type"], "image/png")
            self.assertEqual(len(meta["sha256"]), 64)
            width, height = meta["dimensions"]
            self.assertGreater(width, 50)
            self.assertGreater(height, 50)

    def test_katex_formula_rendering_produces_valid_png(self):
        """Verifica que el renderizado KaTeX de fórmulas complejas genere un archivo PNG válido."""
        from asset_renderer import render_latex_math_to_png
        import tempfile

        test_formula = r"d = \frac{\bar{x}_{\text{competidor}} - \bar{x}_{\text{baseline}}}{s_{\text{diferencia}}}"
        with tempfile.TemporaryDirectory() as td:
            meta = render_latex_math_to_png(test_formula, "test-math.png", output_dir=Path(td))
            self.assertEqual(meta["filename"], "test-math.png")
            self.assertTrue(Path(meta["path"]).is_file())
            self.assertGreater(meta["size_bytes"], 1000)
            self.assertEqual(meta["content_type"], "image/png")
            self.assertEqual(len(meta["sha256"]), 64)

    def test_confluence_image_storage_structure(self):
        """Verifica que el XML de almacenamiento contenga ac:image, ac:alt y la macro expand con código fuente."""
        from asset_renderer import create_confluence_image_storage

        xml = create_confluence_image_storage(
            filename="diagrama-1.png",
            alt_text="Diagrama descriptivo accesible",
            source_code="graph TD; A-->B;",
            source_lang="text",
            expand_title="Código fuente",
        )
        self.assertIn('<ac:image ac:alt="Diagrama descriptivo accesible">', xml)
        self.assertIn('<ri:attachment ri:filename="diagrama-1.png"/>', xml)
        self.assertIn('<ac:structured-macro ac:name="expand"', xml)
        self.assertIn('<ac:parameter ac:name="title">Código fuente</ac:parameter>', xml)
        self.assertIn("graph TD; A-->B;", xml)


class TestRemoteConflictDetection(unittest.TestCase):
    """Pruebas de detección de conflicto remoto y protección contra sobrescritura."""

    def test_remote_version_higher_blocks_update(self):
        """Verifica que si la versión remota es mayor a la última registrada localmente, se bloquee la actualización."""
        from publisher import main
        import sys

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as tf:
            manifest_data = {
                "metadata": {"space_id": "2031619", "root_page_id": "2097153", "test_page_id": "2162690"},
                "documents": [
                    {
                        "file": "docs/instalacion.md",
                        "title": "Guía de Instalación y Despliegue Local",
                        "page_id": "55555",
                        "version": 1,  # Registrado localmente como v1
                        "remote_body_hash": "hash_antiguo_123",
                        "content_sha256": "hash_local_123",
                        "status": "ready",
                        "attachments": [],
                    }
                ],
            }
            json.dump(manifest_data, tf)
            tf_path = Path(tf.name)

        try:
            test_args = [
                "publisher.py",
                "--check",
                "--multi",
                "--manifest", str(tf_path),
                "--email", "dev@example.com",
                "--token", "dummy_token",
            ]
            with patch.object(sys, "argv", test_args):
                with patch("publisher.ConfluenceClient") as mock_client_cls:
                    mock_inst = MagicMock()
                    mock_inst.get_page.side_effect = [
                        {"title": "Raiz", "spaceId": "2031619", "version": {"number": 1}},
                        {"title": "Prueba", "spaceId": "2031619", "version": {"number": 2}},
                        # La página 55555 fue editada remotamente: versión 2
                        {
                            "id": "55555",
                            "title": "Guía de Instalación y Despliegue Local",
                            "spaceId": "2031619",
                            "parentId": "2097153",
                            "version": {"number": 2},
                            "body": {"storage": {"value": "<p>Edición manual remota</p>"}},
                        },
                    ]
                    mock_client_cls.return_value = mock_inst

                    # Capturar salida estándar
                    with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                        main()
                        output = mock_stdout.getvalue()
                        self.assertIn("CONFLICTO REMOTO DETECTADO - ACTUALIZACIÓN BLOQUEADA", output)
                        self.assertIn("Versión local registrada: v1", output)
                        self.assertIn("Versión remota actual   : v2", output)
        finally:
            if tf_path.exists():
                tf_path.unlink()

    def test_remote_body_hash_mismatch_blocks_update(self):
        """Verifica que si la versión es igual pero el hash remoto difiere (edición sin incremento), se bloquee."""
        from publisher import main
        import sys

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as tf:
            manifest_data = {
                "metadata": {"space_id": "2031619", "root_page_id": "2097153", "test_page_id": "2162690"},
                "documents": [
                    {
                        "file": "docs/instalacion.md",
                        "title": "Guía de Instalación y Despliegue Local",
                        "page_id": "55555",
                        "version": 1,
                        "remote_body_hash": "hash_original_esperado",
                        "content_sha256": "hash_local_123",
                        "status": "ready",
                        "attachments": [],
                    }
                ],
            }
            json.dump(manifest_data, tf)
            tf_path = Path(tf.name)

        try:
            test_args = [
                "publisher.py",
                "--check",
                "--multi",
                "--manifest", str(tf_path),
                "--email", "dev@example.com",
                "--token", "dummy_token",
            ]
            with patch.object(sys, "argv", test_args):
                with patch("publisher.ConfluenceClient") as mock_client_cls:
                    mock_inst = MagicMock()
                    mock_inst.get_page.side_effect = [
                        {"title": "Raiz", "spaceId": "2031619", "version": {"number": 1}},
                        {"title": "Prueba", "spaceId": "2031619", "version": {"number": 2}},
                        # Mismo número de versión pero cuerpo alterado
                        {
                            "id": "55555",
                            "title": "Guía de Instalación y Despliegue Local",
                            "spaceId": "2031619",
                            "parentId": "2097153",
                            "version": {"number": 1},
                            "body": {"storage": {"value": "<p>Cuerpo alterado diferente</p>"}},
                        },
                    ]
                    mock_client_cls.return_value = mock_inst

                    with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                        main()
                        output = mock_stdout.getvalue()
                        self.assertIn("CONFLICTO REMOTO DETECTADO - ACTUALIZACIÓN BLOQUEADA", output)
        finally:
            if tf_path.exists():
                tf_path.unlink()


class TestRecoverableDocumentIdentity(unittest.TestCase):
    """Pruebas para la recuperación de páginas creadas tras una interrupción de red."""

    def test_interrupted_creation_recovers_page_with_matching_identity(self):
        """Verifica que si la página fue creada pero el ID no se guardó, se recupere mediante su firma de identidad."""
        from publisher import main
        import sys

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as tf:
            manifest_data = {
                "metadata": {"space_id": "2031619", "root_page_id": "2097153", "test_page_id": "2162690"},
                "documents": [
                    {
                        "file": "docs/instalacion.md",
                        "slug": "instalacion",
                        "title": "Guía de Instalación y Despliegue Local",
                        "page_id": None,  # Interrupción: el ID no se guardó
                        "version": 0,
                        "status": "ready",
                        "attachments": [],
                    }
                ],
            }
            json.dump(manifest_data, tf)
            tf_path = Path(tf.name)

        try:
            test_args = [
                "publisher.py",
                "--check",
                "--multi",
                "--manifest", str(tf_path),
                "--email", "dev@example.com",
                "--token", "dummy_token",
            ]
            with patch.object(sys, "argv", test_args):
                with patch("publisher.ConfluenceClient") as mock_client_cls:
                    mock_inst = MagicMock()
                    mock_inst.get_page.side_effect = [
                        {"title": "Raiz", "spaceId": "2031619", "version": {"number": 1}},
                        {"title": "Prueba", "spaceId": "2031619", "version": {"number": 2}},
                        # Al consultar la página encontrada, contiene la firma de identidad
                        {
                            "id": "778899",
                            "title": "Guía de Instalación y Despliegue Local",
                            "spaceId": "2031619",
                            "parentId": "2097153",
                            "version": {"number": 1},
                            "body": {
                                "storage": {
                                    "value": (
                                        "<!-- confluence-doc-identity: slug=instalacion; space_id=2031619; parent_id=2097153 -->\n"
                                        '<p style="display:none">confluence-doc-identity:slug=instalacion;space_id=2031619;parent_id=2097153</p>\n'
                                        "<h1>Contenido</h1>"
                                    )
                                }
                            },
                        },
                    ]
                    # Búsqueda por título devuelve la página creada antes de la interrupción
                    mock_inst.search_pages_by_title.return_value = [{"id": "778899", "title": "Guía de Instalación y Despliegue Local"}]
                    mock_client_cls.return_value = mock_inst

                    with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                        main()
                        output = mock_stdout.getvalue()
                        self.assertIn("RECUPERACIÓN SEGURA DE IDENTIDAD", output)
                        self.assertIn("ID 778899", output)

            # Comprobar que el manifiesto fue actualizado con el ID recuperado
            updated_manifest = json.loads(tf_path.read_text(encoding="utf-8"))
            self.assertEqual(updated_manifest["documents"][0]["page_id"], "778899")
            self.assertEqual(updated_manifest["documents"][0]["version"], 1)

        finally:
            if tf_path.exists():
                tf_path.unlink()

    def test_orphan_page_without_identity_aborts_without_recreating(self):
        """Verifica que una página ajena con el mismo título pero sin firma de identidad aborte sin adoptar."""
        from publisher import main
        import sys

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as tf:
            manifest_data = {
                "metadata": {"space_id": "2031619", "root_page_id": "2097153", "test_page_id": "2162690"},
                "documents": [
                    {
                        "file": "docs/instalacion.md",
                        "slug": "instalacion",
                        "title": "Guía de Instalación y Despliegue Local",
                        "page_id": None,
                        "version": 0,
                        "status": "ready",
                        "attachments": [],
                    }
                ],
            }
            json.dump(manifest_data, tf)
            tf_path = Path(tf.name)

        try:
            test_args = [
                "publisher.py",
                "--check",
                "--multi",
                "--manifest", str(tf_path),
                "--email", "dev@example.com",
                "--token", "dummy_token",
            ]
            with patch.object(sys, "argv", test_args):
                with patch("publisher.ConfluenceClient") as mock_client_cls:
                    mock_inst = MagicMock()
                    mock_inst.get_page.side_effect = [
                        {"title": "Raiz", "spaceId": "2031619", "version": {"number": 1}},
                        {"title": "Prueba", "spaceId": "2031619", "version": {"number": 2}},
                        # Página existente pero sin firma de identidad (de otro autor)
                        {
                            "id": "112233",
                            "title": "Guía de Instalación y Despliegue Local",
                            "spaceId": "2031619",
                            "parentId": "2097153",
                            "version": {"number": 1},
                            "body": {"storage": {"value": "<p>Página creada manualmente sin firma</p>"}},
                        },
                    ]
                    mock_inst.search_pages_by_title.return_value = [{"id": "112233", "title": "Guía de Instalación y Despliegue Local"}]
                    mock_client_cls.return_value = mock_inst

                    with self.assertRaises(SystemExit) as exit_ctx:
                        main()
                    self.assertEqual(exit_ctx.exception.code, 1)

        finally:
            if tf_path.exists():
                tf_path.unlink()


class TestMultiDocumentPublishOperations(unittest.TestCase):
    """Pruebas simuladas para el modo de publicación múltiple (--publish --multi, --check, --dry-run)."""

    def setUp(self):
        self.tools_dir = Path(__file__).resolve().parent
        self.repo_root = self.tools_dir.parent.parent

    def test_publish_multi_creates_page_uploads_attachments_and_updates_manifest(self):
        """Verifica que --publish --multi ejecute create_page, upload_attachment y guarde IDs en el manifiesto."""
        from publisher import main
        import sys

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as tf:
            manifest_data = {
                "metadata": {
                    "space_id": "2031619",
                    "root_page_id": "2097153",
                    "test_page_id": "2162690",
                    "repo_url": "https://github.com/JMarkoFlores/gemelo-digital-polinizadores",
                    "documented_code_commit": "0d62f6634e1eb4a5066a2bd9e76efe2cb00fee02",
                },
                "documents": [
                    {
                        "file": "docs/arquitectura.md",
                        "slug": "arquitectura",
                        "title": "Arquitectura de Software y Sistemas",
                        "parent_id": "2097153",
                        "space_id": "2031619",
                        "page_id": None,
                        "version": 0,
                        "content_sha256": None,
                        "status": "ready",
                        "attachments": [
                            {
                                "filename": "arquitectura-mermaid-1.png",
                                "sha256": "bf730245c27f547bb496786da65c5be83746e47c6d93a805d494500f8ff68cc5",
                                "size_bytes": 20190,
                                "content_type": "image/png",
                            }
                        ],
                        "remote_body_hash": None,
                    }
                ],
            }
            json.dump(manifest_data, tf)
            tf_path = Path(tf.name)

        try:
            test_args = [
                "publisher.py",
                "--publish",
                "--multi",
                "--manifest", str(tf_path),
                "--email", "dev@example.com",
                "--token", "dummy_token",
            ]
            with patch.object(sys, "argv", test_args):
                with patch("publisher.ConfluenceClient") as mock_client_cls:
                    mock_inst = MagicMock()
                    mock_inst.get_page.side_effect = [
                        {"title": "Raiz", "spaceId": "2031619", "version": {"number": 1}},
                        {"title": "Prueba", "spaceId": "2031619", "version": {"number": 2}},
                        # Post-creación para lectura de cuerpo remoto
                        {
                            "id": "334455",
                            "title": "Arquitectura de Software y Sistemas",
                            "spaceId": "2031619",
                            "parentId": "2097153",
                            "version": {"number": 1},
                            "body": {"storage": {"value": "<p>Contenido creado</p>"}},
                        },
                    ]
                    mock_inst.search_pages_by_title.return_value = []
                    mock_inst.create_page.return_value = {"id": "334455", "version": {"number": 1}}
                    mock_inst.get_attachments.return_value = []
                    mock_inst.upload_attachment.return_value = {"id": "att_1"}
                    mock_client_cls.return_value = mock_inst

                    with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                        main()
                        output = mock_stdout.getvalue()
                        self.assertIn("[PUBLICACIÓN EXITOSA]", output)
                        self.assertIn("Páginas creadas con éxito     : 1", output)
                        self.assertIn("Adjuntos PNG subidos          : 1", output)

            # Verificar llamadas
            mock_inst.create_page.assert_called_once()
            call_kwargs = mock_inst.create_page.call_args[1]
            self.assertEqual(call_kwargs["space_id"], "2031619")
            self.assertEqual(call_kwargs["title"], "Arquitectura de Software y Sistemas")
            self.assertEqual(call_kwargs["parent_id"], "2097153")

            mock_inst.upload_attachment.assert_called_once()
            att_kwargs = mock_inst.upload_attachment.call_args[1] if mock_inst.upload_attachment.call_args[1] else {}
            att_args = mock_inst.upload_attachment.call_args[0]
            target_page_id = att_kwargs.get("page_id") or att_args[0]
            self.assertEqual(str(target_page_id), "334455")

            # Verificar que el manifiesto fue actualizado en disco inmediatamente
            saved_manifest = json.loads(tf_path.read_text(encoding="utf-8"))
            saved_doc = saved_manifest["documents"][0]
            self.assertEqual(saved_doc["page_id"], "334455")
            self.assertEqual(saved_doc["version"], 1)
            self.assertIsNotNone(saved_doc["content_sha256"])
            self.assertIsNotNone(saved_doc["remote_body_hash"])

        finally:
            if tf_path.exists():
                tf_path.unlink()

    def test_check_and_dry_run_never_perform_writes(self):
        """Verifica que ni --check ni --dry-run realicen llamadas de escritura (create, update, upload)."""
        from publisher import main
        import sys

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as tf:
            manifest_data = {
                "metadata": {
                    "space_id": "2031619",
                    "root_page_id": "2097153",
                    "test_page_id": "2162690",
                    "repo_url": "https://github.com/JMarkoFlores/gemelo-digital-polinizadores",
                    "documented_code_commit": "0d62f6634e1eb4a5066a2bd9e76efe2cb00fee02",
                },
                "documents": [
                    {
                        "file": "docs/arquitectura.md",
                        "slug": "arquitectura",
                        "title": "Arquitectura de Software y Sistemas",
                        "parent_id": "2097153",
                        "space_id": "2031619",
                        "page_id": None,
                        "version": 0,
                        "content_sha256": None,
                        "status": "ready",
                        "attachments": [{"filename": "arquitectura-mermaid-1.png", "sha256": "123", "size_bytes": 100}],
                        "remote_body_hash": None,
                    }
                ],
            }
            json.dump(manifest_data, tf)
            tf_path = Path(tf.name)

        try:
            for mode_flag in ["--check", "--dry-run"]:
                test_args = [
                    "publisher.py",
                    mode_flag,
                    "--multi",
                    "--manifest", str(tf_path),
                    "--email", "dev@example.com",
                    "--token", "dummy_token",
                ]
                with patch.object(sys, "argv", test_args):
                    with patch("publisher.ConfluenceClient") as mock_client_cls:
                        mock_inst = MagicMock()
                        mock_inst.get_page.side_effect = [
                            {"title": "Raiz", "spaceId": "2031619", "version": {"number": 1}},
                            {"title": "Prueba", "spaceId": "2031619", "version": {"number": 2}},
                        ]
                        mock_inst.search_pages_by_title.return_value = []
                        mock_client_cls.return_value = mock_inst

                        with patch("sys.stdout", new_callable=io.StringIO):
                            main()

                        mock_inst.create_page.assert_not_called()
                        mock_inst.update_page.assert_not_called()
                        mock_inst.upload_attachment.assert_not_called()

        finally:
            if tf_path.exists():
                tf_path.unlink()

    def test_repeat_publish_without_changes_skips_writes_and_reloads(self):
        """Verifica que una repetición sin cambios no duplique páginas ni recargue adjuntos."""
        from publisher import calculate_hash, main
        from markdown_to_storage import markdown_to_storage
        import sys

        raw_md = (self.repo_root / "docs/arquitectura.md").read_text(encoding="utf-8")
        manifest_data = {
            "metadata": {
                "space_id": "2031619",
                "root_page_id": "2097153",
                "test_page_id": "2162690",
                "repo_url": "https://github.com/JMarkoFlores/gemelo-digital-polinizadores",
                "documented_code_commit": "0d62f6634e1eb4a5066a2bd9e76efe2cb00fee02",
            },
            "documents": [
                {
                    "file": "docs/arquitectura.md",
                    "slug": "arquitectura",
                    "title": "Arquitectura de Software y Sistemas",
                    "parent_id": "2097153",
                    "space_id": "2031619",
                    "page_id": "334455",
                    "version": 1,
                    "content_sha256": None,
                    "status": "ready",
                    "attachments": [
                        {
                            "filename": "arquitectura-mermaid-1.png",
                            "sha256": "bf730245c27f547bb496786da65c5be83746e47c6d93a805d494500f8ff68cc5",
                            "size_bytes": 20190,
                            "content_type": "image/png",
                            "published_sha256": "bf730245c27f547bb496786da65c5be83746e47c6d93a805d494500f8ff68cc5",
                            "attachment_id": "att_1",
                            "published_version": 1,
                        }
                    ],
                    "remote_body_hash": None,
                }
            ],
        }

        # Asegurar que published_sha256 coincida con el activo real en disco
        local_att_file = self.repo_root / "tools/docs/rendered_assets/arquitectura-mermaid-1.png"
        if local_att_file.is_file():
            import hashlib
            real_att_hash = hashlib.sha256(local_att_file.read_bytes()).hexdigest()
            manifest_data["documents"][0]["attachments"][0]["published_sha256"] = real_att_hash

        _, storage_xml, _ = markdown_to_storage(raw_md, "docs/arquitectura.md", manifest_data, return_attachments=True)
        local_hash = calculate_hash(storage_xml)
        remote_body_xml = storage_xml
        remote_hash = calculate_hash(remote_body_xml)

        manifest_data["documents"][0]["content_sha256"] = local_hash
        manifest_data["documents"][0]["remote_body_hash"] = remote_hash

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as tf:
            json.dump(manifest_data, tf)
            tf_path = Path(tf.name)

        try:
            test_args = [
                "publisher.py",
                "--publish",
                "--multi",
                "--manifest", str(tf_path),
                "--email", "dev@example.com",
                "--token", "dummy_token",
            ]
            with patch.object(sys, "argv", test_args):
                with patch("publisher.ConfluenceClient") as mock_client_cls:
                    mock_inst = MagicMock()
                    mock_inst.get_page.side_effect = [
                        {"title": "Raiz", "spaceId": "2031619", "version": {"number": 1}},
                        {"title": "Prueba", "spaceId": "2031619", "version": {"number": 2}},
                        # Página existente
                        {
                            "id": "334455",
                            "title": "Arquitectura de Software y Sistemas",
                            "spaceId": "2031619",
                            "parentId": "2097153",
                            "version": {"number": 1},
                            "body": {"storage": {"value": remote_body_xml}},
                        },
                    ]
                    # Adjunto ya existente en Confluence
                    mock_inst.get_attachments.return_value = [{"title": "arquitectura-mermaid-1.png", "id": "att_1", "version": {"number": 1}}]
                    mock_client_cls.return_value = mock_inst

                    with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                        main()
                        output = mock_stdout.getvalue()
                        self.assertIn("Páginas creadas con éxito     : 0", output)
                        self.assertIn("Páginas actualizadas          : 0", output)
                        self.assertIn("Páginas omitidas (sin cambios): 1", output)
                        self.assertIn("Adjuntos PNG subidos          : 0", output)
                        self.assertIn("Adjuntos PNG actualizados     : 0", output)
                        self.assertIn("Adjuntos PNG omitidos         : 1", output)
                        self.assertIn("SIN CAMBIOS", output)
                        self.assertIn("comprobado idéntico", output)

            # Cero escrituras
            mock_inst.create_page.assert_not_called()
            mock_inst.update_page.assert_not_called()
            mock_inst.upload_attachment.assert_not_called()
            mock_inst.update_attachment.assert_not_called()

        finally:
            if tf_path.exists():
                tf_path.unlink()

    def test_publish_multi_fails_and_exits_nonzero_when_creation_fails(self):
        """Verifica que si la publicación queda incompleta, termine con código distinto de cero."""
        from publisher import main
        import sys

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as tf:
            manifest_data = {
                "metadata": {
                    "space_id": "2031619",
                    "root_page_id": "2097153",
                    "test_page_id": "2162690",
                    "repo_url": "https://github.com/JMarkoFlores/gemelo-digital-polinizadores",
                    "documented_code_commit": "0d62f6634e1eb4a5066a2bd9e76efe2cb00fee02",
                },
                "documents": [
                    {
                        "file": "docs/arquitectura.md",
                        "slug": "arquitectura",
                        "title": "Arquitectura de Software y Sistemas",
                        "parent_id": "2097153",
                        "space_id": "2031619",
                        "page_id": None,
                        "version": 0,
                        "content_sha256": None,
                        "status": "ready",
                        "attachments": [],
                        "remote_body_hash": None,
                    }
                ],
            }
            json.dump(manifest_data, tf)
            tf_path = Path(tf.name)

        try:
            test_args = [
                "publisher.py",
                "--publish",
                "--multi",
                "--manifest", str(tf_path),
                "--email", "dev@example.com",
                "--token", "dummy_token",
            ]
            with patch.object(sys, "argv", test_args):
                with patch("publisher.ConfluenceClient") as mock_client_cls:
                    mock_inst = MagicMock()
                    mock_inst.get_page.side_effect = [
                        {"title": "Raiz", "spaceId": "2031619", "version": {"number": 1}},
                        {"title": "Prueba", "spaceId": "2031619", "version": {"number": 2}},
                    ]
                    mock_inst.search_pages_by_title.return_value = []
                    mock_inst.create_page.side_effect = ConfluenceAPIError("Error simulado de API 500")
                    mock_client_cls.return_value = mock_inst

                    with self.assertRaises(SystemExit) as exit_ctx:
                        main()
                    self.assertEqual(exit_ctx.exception.code, 1)

        finally:
            if tf_path.exists():
                tf_path.unlink()

    def test_publish_multi_immediate_manifest_save_on_partial_failure(self):
        """Verifica que el ID obtenido se guarde inmediatamente en disco tras crear cada página, incluso si falla la siguiente."""
        from publisher import main
        import sys

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as tf:
            manifest_data = {
                "metadata": {
                    "space_id": "2031619",
                    "root_page_id": "2097153",
                    "test_page_id": "2162690",
                    "repo_url": "https://github.com/JMarkoFlores/gemelo-digital-polinizadores",
                    "documented_code_commit": "0d62f6634e1eb4a5066a2bd9e76efe2cb00fee02",
                },
                "documents": [
                    {
                        "file": "docs/arquitectura.md",
                        "slug": "arquitectura",
                        "title": "Arquitectura de Software y Sistemas",
                        "parent_id": "2097153",
                        "space_id": "2031619",
                        "page_id": None,
                        "version": 0,
                        "content_sha256": None,
                        "status": "ready",
                        "attachments": [],
                        "remote_body_hash": None,
                    },
                    {
                        "file": "docs/instalacion.md",
                        "slug": "instalacion",
                        "title": "Guía de Instalación y Despliegue Local",
                        "parent_id": "2097153",
                        "space_id": "2031619",
                        "page_id": None,
                        "version": 0,
                        "content_sha256": None,
                        "status": "ready",
                        "attachments": [],
                        "remote_body_hash": None,
                    },
                ],
            }
            json.dump(manifest_data, tf)
            tf_path = Path(tf.name)

        try:
            test_args = [
                "publisher.py",
                "--publish",
                "--multi",
                "--manifest", str(tf_path),
                "--email", "dev@example.com",
                "--token", "dummy_token",
            ]
            with patch.object(sys, "argv", test_args):
                with patch("publisher.ConfluenceClient") as mock_client_cls:
                    mock_inst = MagicMock()
                    mock_inst.get_page.side_effect = [
                        {"title": "Raiz", "spaceId": "2031619", "version": {"number": 1}},
                        {"title": "Prueba", "spaceId": "2031619", "version": {"number": 2}},
                        # Post-creación doc 1
                        {
                            "id": "111222",
                            "title": "Arquitectura de Software y Sistemas",
                            "spaceId": "2031619",
                            "parentId": "2097153",
                            "version": {"number": 1},
                            "body": {"storage": {"value": "<p>Doc 1 creado</p>"}},
                        },
                    ]
                    mock_inst.search_pages_by_title.return_value = []
                    # Doc 1 creación exitosa; Doc 2 falla con error 500
                    mock_inst.create_page.side_effect = [
                        {"id": "111222", "version": {"number": 1}},
                        ConfluenceAPIError("Error simulado en Doc 2"),
                    ]
                    mock_client_cls.return_value = mock_inst

                    with self.assertRaises(SystemExit) as exit_ctx:
                        main()
                    self.assertEqual(exit_ctx.exception.code, 1)

            # Comprobar que a pesar de que doc 2 falló, doc 1 fue persistido INMEDIATAMENTE en disco
            saved_manifest = json.loads(tf_path.read_text(encoding="utf-8"))
            doc_1 = saved_manifest["documents"][0]
            doc_2 = saved_manifest["documents"][1]
            self.assertEqual(doc_1["page_id"], "111222")
            self.assertEqual(doc_1["version"], 1)
            self.assertIsNone(doc_2["page_id"])

        finally:
            if tf_path.exists():
                tf_path.unlink()

    def test_attachment_same_name_same_content_skipped(self):
        """Verifica que un adjunto existente con el mismo nombre y mismo contenido SHA-256 sea omitido."""
        from publisher import calculate_hash, main
        from markdown_to_storage import markdown_to_storage
        import hashlib
        import sys

        raw_md = (self.repo_root / "docs/arquitectura.md").read_text(encoding="utf-8")
        local_att_path = self.repo_root / "tools/docs/rendered_assets/arquitectura-mermaid-1.png"
        self.assertTrue(local_att_path.is_file(), f"Activo {local_att_path} no encontrado")
        real_sha256 = hashlib.sha256(local_att_path.read_bytes()).hexdigest()

        manifest_data = {
            "metadata": {
                "space_id": "2031619",
                "root_page_id": "2097153",
                "test_page_id": "2162690",
                "repo_url": "https://github.com/JMarkoFlores/gemelo-digital-polinizadores",
                "documented_code_commit": "0d62f6634e1eb4a5066a2bd9e76efe2cb00fee02",
            },
            "documents": [
                {
                    "file": "docs/arquitectura.md",
                    "slug": "arquitectura",
                    "title": "Arquitectura de Software y Sistemas",
                    "parent_id": "2097153",
                    "space_id": "2031619",
                    "page_id": "334455",
                    "version": 1,
                    "content_sha256": None,
                    "status": "ready",
                    "attachments": [
                        {
                            "filename": "arquitectura-mermaid-1.png",
                            "sha256": real_sha256,
                            "size_bytes": 20190,
                            "content_type": "image/png",
                            "published_sha256": real_sha256,
                            "attachment_id": "att_1",
                            "published_version": 1,
                        }
                    ],
                    "remote_body_hash": None,
                }
            ],
        }

        _, storage_xml, _ = markdown_to_storage(raw_md, "docs/arquitectura.md", manifest_data, return_attachments=True)
        local_hash = calculate_hash(storage_xml)
        manifest_data["documents"][0]["content_sha256"] = local_hash
        manifest_data["documents"][0]["remote_body_hash"] = local_hash

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as tf:
            json.dump(manifest_data, tf)
            tf_path = Path(tf.name)

        try:
            test_args = [
                "publisher.py",
                "--publish",
                "--multi",
                "--manifest", str(tf_path),
                "--email", "dev@example.com",
                "--token", "dummy_token",
            ]
            with patch.object(sys, "argv", test_args):
                with patch("publisher.ConfluenceClient") as mock_client_cls:
                    mock_inst = MagicMock()
                    mock_inst.get_page.side_effect = [
                        {"title": "Raiz", "spaceId": "2031619", "version": {"number": 1}},
                        {"title": "Prueba", "spaceId": "2031619", "version": {"number": 2}},
                        {
                            "id": "334455",
                            "title": "Arquitectura de Software y Sistemas",
                            "spaceId": "2031619",
                            "parentId": "2097153",
                            "version": {"number": 1},
                            "body": {"storage": {"value": storage_xml}},
                        },
                    ]
                    # Adjunto remoto idéntico
                    mock_inst.get_attachments.return_value = [
                        {"title": "arquitectura-mermaid-1.png", "id": "att_1", "version": {"number": 1}}
                    ]
                    mock_client_cls.return_value = mock_inst

                    with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                        main()
                        output = mock_stdout.getvalue()
                        self.assertIn("Adjuntos PNG omitidos         : 1", output)
                        self.assertIn("Adjuntos PNG actualizados     : 0", output)
                        self.assertIn("Adjuntos PNG subidos          : 0", output)
                        self.assertIn("comprobado idéntico", output)

            mock_inst.upload_attachment.assert_not_called()
            mock_inst.update_attachment.assert_not_called()

        finally:
            if tf_path.exists():
                tf_path.unlink()

    def test_attachment_same_name_different_content_updates(self):
        """Verifica que un adjunto existente con el mismo nombre pero diferente contenido local sea actualizado."""
        from publisher import calculate_hash, main
        from markdown_to_storage import markdown_to_storage
        import hashlib
        import sys

        raw_md = (self.repo_root / "docs/arquitectura.md").read_text(encoding="utf-8")
        local_att_path = self.repo_root / "tools/docs/rendered_assets/arquitectura-mermaid-1.png"
        self.assertTrue(local_att_path.is_file())
        real_sha256 = hashlib.sha256(local_att_path.read_bytes()).hexdigest()
        old_different_hash = "0000000000000000000000000000000000000000000000000000000000000000"

        manifest_data = {
            "metadata": {
                "space_id": "2031619",
                "root_page_id": "2097153",
                "test_page_id": "2162690",
                "repo_url": "https://github.com/JMarkoFlores/gemelo-digital-polinizadores",
                "documented_code_commit": "0d62f6634e1eb4a5066a2bd9e76efe2cb00fee02",
            },
            "documents": [
                {
                    "file": "docs/arquitectura.md",
                    "slug": "arquitectura",
                    "title": "Arquitectura de Software y Sistemas",
                    "parent_id": "2097153",
                    "space_id": "2031619",
                    "page_id": "334455",
                    "version": 1,
                    "content_sha256": None,
                    "status": "ready",
                    "attachments": [
                        {
                            "filename": "arquitectura-mermaid-1.png",
                            "sha256": real_sha256,
                            "size_bytes": 20190,
                            "content_type": "image/png",
                            "published_sha256": old_different_hash,
                            "attachment_id": "att_1",
                            "published_version": 1,
                        }
                    ],
                    "remote_body_hash": None,
                }
            ],
        }

        _, storage_xml, _ = markdown_to_storage(raw_md, "docs/arquitectura.md", manifest_data, return_attachments=True)
        local_hash = calculate_hash(storage_xml)
        manifest_data["documents"][0]["content_sha256"] = local_hash
        manifest_data["documents"][0]["remote_body_hash"] = local_hash

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as tf:
            json.dump(manifest_data, tf)
            tf_path = Path(tf.name)

        try:
            test_args = [
                "publisher.py",
                "--publish",
                "--multi",
                "--manifest", str(tf_path),
                "--email", "dev@example.com",
                "--token", "dummy_token",
            ]
            with patch.object(sys, "argv", test_args):
                with patch("publisher.ConfluenceClient") as mock_client_cls:
                    mock_inst = MagicMock()
                    mock_inst.get_page.side_effect = [
                        {"title": "Raiz", "spaceId": "2031619", "version": {"number": 1}},
                        {"title": "Prueba", "spaceId": "2031619", "version": {"number": 2}},
                        {
                            "id": "334455",
                            "title": "Arquitectura de Software y Sistemas",
                            "spaceId": "2031619",
                            "parentId": "2097153",
                            "version": {"number": 1},
                            "body": {"storage": {"value": storage_xml}},
                        },
                    ]
                    # Adjunto remoto existe pero su hash local difiere
                    mock_inst.get_attachments.return_value = [
                        {"title": "arquitectura-mermaid-1.png", "id": "att_1", "version": {"number": 1}}
                    ]
                    mock_inst.update_attachment.return_value = {"id": "att_1", "version": {"number": 2}}
                    mock_client_cls.return_value = mock_inst

                    with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                        main()
                        output = mock_stdout.getvalue()
                        self.assertIn("Adjuntos PNG actualizados     : 1", output)
                        self.assertIn("Contenido local de 'arquitectura-mermaid-1.png' modificado", output)
                        self.assertIn("[ÉXITO]: Adjunto 'arquitectura-mermaid-1.png' actualizado satisfactoriamente", output)

            # Debe haber llamado a update_attachment, NUNCA a upload_attachment
            mock_inst.upload_attachment.assert_not_called()
            mock_inst.update_attachment.assert_called_once()
            call_kwargs = mock_inst.update_attachment.call_args[1] or {}
            call_args = mock_inst.update_attachment.call_args[0]
            target_page_id = call_kwargs.get("page_id") or call_args[0]
            target_att_id = call_kwargs.get("attachment_id") or call_args[1]
            self.assertEqual(str(target_page_id), "334455")
            self.assertEqual(str(target_att_id), "att_1")

            # Comprobar que el manifiesto fue actualizado en disco con el nuevo hash publicado y versión 2
            saved_manifest = json.loads(tf_path.read_text(encoding="utf-8"))
            saved_att = saved_manifest["documents"][0]["attachments"][0]
            self.assertEqual(saved_att["published_sha256"], real_sha256)
            self.assertEqual(saved_att["published_version"], 2)
            self.assertEqual(saved_att["attachment_id"], "att_1")

        finally:
            if tf_path.exists():
                tf_path.unlink()

    def test_attachment_updates_when_page_unchanged_but_image_modified(self):
        """Verifica que cuando el cuerpo de la página no cambia pero la imagen cambia, el adjunto se actualice sin reescribir la página."""
        from publisher import calculate_hash, main
        from markdown_to_storage import markdown_to_storage
        import hashlib
        import sys

        raw_md = (self.repo_root / "docs/arquitectura.md").read_text(encoding="utf-8")
        local_att_path = self.repo_root / "tools/docs/rendered_assets/arquitectura-mermaid-1.png"
        self.assertTrue(local_att_path.is_file())
        real_sha256 = hashlib.sha256(local_att_path.read_bytes()).hexdigest()
        old_image_hash = "1111111111111111111111111111111111111111111111111111111111111111"

        manifest_data = {
            "metadata": {
                "space_id": "2031619",
                "root_page_id": "2097153",
                "test_page_id": "2162690",
                "repo_url": "https://github.com/JMarkoFlores/gemelo-digital-polinizadores",
                "documented_code_commit": "0d62f6634e1eb4a5066a2bd9e76efe2cb00fee02",
            },
            "documents": [
                {
                    "file": "docs/arquitectura.md",
                    "slug": "arquitectura",
                    "title": "Arquitectura de Software y Sistemas",
                    "parent_id": "2097153",
                    "space_id": "2031619",
                    "page_id": "334455",
                    "version": 1,
                    "content_sha256": None,
                    "status": "ready",
                    "attachments": [
                        {
                            "filename": "arquitectura-mermaid-1.png",
                            "sha256": real_sha256,
                            "size_bytes": 20190,
                            "content_type": "image/png",
                            "published_sha256": old_image_hash,
                            "attachment_id": "att_1",
                            "published_version": 1,
                        }
                    ],
                    "remote_body_hash": None,
                }
            ],
        }

        _, storage_xml, _ = markdown_to_storage(raw_md, "docs/arquitectura.md", manifest_data, return_attachments=True)
        local_hash = calculate_hash(storage_xml)
        # La página está idéntica
        manifest_data["documents"][0]["content_sha256"] = local_hash
        manifest_data["documents"][0]["remote_body_hash"] = local_hash

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as tf:
            json.dump(manifest_data, tf)
            tf_path = Path(tf.name)

        try:
            test_args = [
                "publisher.py",
                "--publish",
                "--multi",
                "--manifest", str(tf_path),
                "--email", "dev@example.com",
                "--token", "dummy_token",
            ]
            with patch.object(sys, "argv", test_args):
                with patch("publisher.ConfluenceClient") as mock_client_cls:
                    mock_inst = MagicMock()
                    mock_inst.get_page.side_effect = [
                        {"title": "Raiz", "spaceId": "2031619", "version": {"number": 1}},
                        {"title": "Prueba", "spaceId": "2031619", "version": {"number": 2}},
                        # Página existente remota (cuerpo idéntico)
                        {
                            "id": "334455",
                            "title": "Arquitectura de Software y Sistemas",
                            "spaceId": "2031619",
                            "parentId": "2097153",
                            "version": {"number": 1},
                            "body": {"storage": {"value": storage_xml}},
                        },
                    ]
                    mock_inst.get_attachments.return_value = [
                        {"title": "arquitectura-mermaid-1.png", "id": "att_1", "version": {"number": 1}}
                    ]
                    mock_inst.update_attachment.return_value = {"id": "att_1", "version": {"number": 2}}
                    mock_client_cls.return_value = mock_inst

                    with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                        main()
                        output = mock_stdout.getvalue()
                        # La página se omitió como idéntica
                        self.assertIn("Páginas omitidas (sin cambios): 1", output)
                        self.assertIn("Páginas actualizadas          : 0", output)
                        # El adjunto se actualizó
                        self.assertIn("Adjuntos PNG actualizados     : 1", output)

            # La página no se tocó
            mock_inst.create_page.assert_not_called()
            mock_inst.update_page.assert_not_called()
            # Pero el adjunto sí fue actualizado
            mock_inst.update_attachment.assert_called_once()

            # El hash publicado del adjunto se actualizó en disco
            saved_manifest = json.loads(tf_path.read_text(encoding="utf-8"))
            saved_att = saved_manifest["documents"][0]["attachments"][0]
            self.assertEqual(saved_att["published_sha256"], real_sha256)
            self.assertEqual(saved_att["published_version"], 2)

        finally:
            if tf_path.exists():
                tf_path.unlink()

    def test_attachment_upload_failure_and_resumption(self):
        """Verifica que ante un fallo de subida de adjunto se detenga con resultado incompleto y permita reanudar sin duplicar la página."""
        from publisher import calculate_hash, main
        from markdown_to_storage import markdown_to_storage
        import hashlib
        import sys

        raw_md = (self.repo_root / "docs/arquitectura.md").read_text(encoding="utf-8")
        local_att_path = self.repo_root / "tools/docs/rendered_assets/arquitectura-mermaid-1.png"
        self.assertTrue(local_att_path.is_file())
        real_sha256 = hashlib.sha256(local_att_path.read_bytes()).hexdigest()

        manifest_data = {
            "metadata": {
                "space_id": "2031619",
                "root_page_id": "2097153",
                "test_page_id": "2162690",
                "repo_url": "https://github.com/JMarkoFlores/gemelo-digital-polinizadores",
                "documented_code_commit": "0d62f6634e1eb4a5066a2bd9e76efe2cb00fee02",
            },
            "documents": [
                {
                    "file": "docs/arquitectura.md",
                    "slug": "arquitectura",
                    "title": "Arquitectura de Software y Sistemas",
                    "parent_id": "2097153",
                    "space_id": "2031619",
                    "page_id": "334455",
                    "version": 1,
                    "content_sha256": None,
                    "status": "ready",
                    "attachments": [
                        {
                            "filename": "arquitectura-mermaid-1.png",
                            "sha256": real_sha256,
                            "size_bytes": 20190,
                            "content_type": "image/png",
                            # Sin published_sha256 aún
                        }
                    ],
                    "remote_body_hash": None,
                }
            ],
        }

        _, storage_xml, _ = markdown_to_storage(raw_md, "docs/arquitectura.md", manifest_data, return_attachments=True)
        local_hash = calculate_hash(storage_xml)
        manifest_data["documents"][0]["content_sha256"] = local_hash
        manifest_data["documents"][0]["remote_body_hash"] = local_hash

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as tf:
            json.dump(manifest_data, tf)
            tf_path = Path(tf.name)

        try:
            test_args = [
                "publisher.py",
                "--publish",
                "--multi",
                "--manifest", str(tf_path),
                "--email", "dev@example.com",
                "--token", "dummy_token",
            ]

            # --- EJECUCIÓN 1: Fallo de red en la subida del adjunto ---
            with patch.object(sys, "argv", test_args):
                with patch("publisher.ConfluenceClient") as mock_client_cls:
                    mock_inst = MagicMock()
                    mock_inst.get_page.side_effect = [
                        {"title": "Raiz", "spaceId": "2031619", "version": {"number": 1}},
                        {"title": "Prueba", "spaceId": "2031619", "version": {"number": 2}},
                        {
                            "id": "334455",
                            "title": "Arquitectura de Software y Sistemas",
                            "spaceId": "2031619",
                            "parentId": "2097153",
                            "version": {"number": 1},
                            "body": {"storage": {"value": storage_xml}},
                        },
                    ]
                    # No existe remotamente aún
                    mock_inst.get_attachments.return_value = []
                    mock_inst.upload_attachment.side_effect = ConfluenceAPIError("Error de conexión al cargar adjunto")
                    mock_client_cls.return_value = mock_inst

                    with self.assertRaises(SystemExit) as exit_ctx:
                        main()
                    # Debe devolver código 1 (resultado incompleto)
                    self.assertEqual(exit_ctx.exception.code, 1)

            # Verificar que el fallo NO guardó published_sha256 en el manifiesto
            manifest_after_fail = json.loads(tf_path.read_text(encoding="utf-8"))
            att_after_fail = manifest_after_fail["documents"][0]["attachments"][0]
            self.assertIsNone(att_after_fail.get("published_sha256"))
            # La página sigue registrada
            self.assertEqual(manifest_after_fail["documents"][0]["page_id"], "334455")

            # --- EJECUCIÓN 2: Reanudación exitosa sin duplicar página ---
            with patch.object(sys, "argv", test_args):
                with patch("publisher.ConfluenceClient") as mock_client_cls:
                    mock_inst = MagicMock()
                    mock_inst.get_page.side_effect = [
                        {"title": "Raiz", "spaceId": "2031619", "version": {"number": 1}},
                        {"title": "Prueba", "spaceId": "2031619", "version": {"number": 2}},
                        {
                            "id": "334455",
                            "title": "Arquitectura de Software y Sistemas",
                            "spaceId": "2031619",
                            "parentId": "2097153",
                            "version": {"number": 1},
                            "body": {"storage": {"value": storage_xml}},
                        },
                    ]
                    mock_inst.get_attachments.return_value = []
                    # Ahora la subida triunfa
                    mock_inst.upload_attachment.return_value = {"id": "att_1", "version": {"number": 1}}
                    mock_client_cls.return_value = mock_inst

                    with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                        main()
                        output = mock_stdout.getvalue()
                        self.assertIn("[PUBLICACIÓN EXITOSA]", output)
                        self.assertIn("Adjuntos PNG subidos          : 1", output)

            # La página NUNCA se duplicó (no se llamó a create_page)
            mock_inst.create_page.assert_not_called()
            mock_inst.upload_attachment.assert_called_once()

            # El manifiesto final guardó el hash de publicación
            manifest_final = json.loads(tf_path.read_text(encoding="utf-8"))
            att_final = manifest_final["documents"][0]["attachments"][0]
            self.assertEqual(att_final["published_sha256"], real_sha256)
            self.assertEqual(att_final["attachment_id"], "att_1")
            self.assertEqual(att_final["published_version"], 1)

        finally:
            if tf_path.exists():
                tf_path.unlink()


if __name__ == "__main__":
    unittest.main()


