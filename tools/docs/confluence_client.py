"""Cliente seguro para la API REST v2 de Confluence Cloud.

Gestiona la autenticación con API Tokens personales de Atlassian mediante
HTTP Basic Authentication (correo + token personal), distinguiendo entre:
  - API Token personal sin ámbitos: contra https://{site_domain}/wiki/api/v2
  - API Token personal con ámbitos: contra https://api.atlassian.com/ex/confluence/{cloudId}/wiki/api/v2

Garantiza que las cabeceras de autorización y secretos nunca queden expuestos
en logs, impresiones de consola o mensajes de error.
"""

from __future__ import annotations

import base64
import json
import logging
from typing import Any, Dict, List, Optional
import urllib.parse
import urllib.request
import urllib.error

logger = logging.getLogger("confluence_client")


class ConfluenceAPIError(Exception):
    """Excepción específica para errores de la API de Confluence sin exposición de credenciales."""

    def __init__(self, message: str, status_code: Optional[int] = None, response_body: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class ConfluenceClient:
    """Cliente para interactuar con Confluence Cloud REST API v2 mediante API Tokens personales."""

    def __init__(
        self,
        site_domain: str,
        email: str,
        api_token: str,
        token_type: str = "unscoped",
        cloud_id: Optional[str] = None,
        timeout: int = 15,
    ):
        """Inicializa el cliente de Confluence.

        Args:
            site_domain: Dominio del sitio Atlassian (ej. 'unitru-team-hpj93f6y.atlassian.net').
            email: Correo electrónico de la cuenta Atlassian (obligatorio para HTTP Basic en ambos modos).
            api_token: API token personal generado desde la cuenta Atlassian (nunca se imprime ni almacena).
            token_type: 'unscoped' (sitio directo) o 'scoped' (api.atlassian.com con cloudId). Ambos usan HTTP Basic.
            cloud_id: Atlassian Cloud ID (requerido para tokens 'scoped'; se detecta automáticamente si se omite).
            timeout: Tiempo de espera en segundos para solicitudes HTTP.
        """
        # Normalizar dominio
        self.site_domain = site_domain.replace("https://", "").replace("http://", "").strip("/")
        self.email = email.strip() if email else ""
        self._api_token = api_token.strip() if api_token else ""
        self.token_type = token_type.lower().strip()
        self.timeout = timeout

        if not self.email:
            raise ValueError(
                "El correo electrónico de la cuenta Atlassian es obligatorio para la autenticación "
                "HTTP Basic con API Token personal."
            )

        if not self._api_token:
            raise ValueError("El API token personal de Atlassian es obligatorio y no puede estar vacío.")

        if self.token_type == "scoped":
            self.cloud_id = cloud_id.strip() if cloud_id else self._resolve_cloud_id()
            self.base_url = f"https://api.atlassian.com/ex/confluence/{self.cloud_id}/wiki/api/v2"
        elif self.token_type == "unscoped":
            self.cloud_id = cloud_id.strip() if cloud_id else None
            self.base_url = f"https://{self.site_domain}/wiki/api/v2"
        else:
            raise ValueError(
                f"Tipo de token personal no reconocido: '{token_type}'. Debe ser 'unscoped' o 'scoped'."
            )

    def _resolve_cloud_id(self) -> str:
        """Resuelve el Cloud ID de Atlassian consultando el endpoint público /_edge/tenant_info."""
        info_url = f"https://{self.site_domain}/_edge/tenant_info"
        try:
            req = urllib.request.Request(
                info_url,
                headers={"Accept": "application/json", "User-Agent": "ConfluencePublisher/1.0"},
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                cid = data.get("cloudId")
                if cid:
                    return str(cid)
        except Exception as exc:
            raise ConfluenceAPIError(
                f"No fue posible resolver automáticamente el Cloud ID desde {info_url}. "
                "Especifíquelo explícitamente mediante el argumento --cloud-id o CONFLUENCE_CLOUD_ID."
            ) from exc

        raise ConfluenceAPIError(
            f"El endpoint {info_url} no devolvió un cloudId válido. "
            "Especifíquelo explícitamente mediante --cloud-id o CONFLUENCE_CLOUD_ID."
        )

    def _get_auth_header(self) -> str:
        """Genera la cabecera HTTP Basic Authentication (email:token) sin registrar secretos.

        Ambos modos (sin ámbitos y con ámbitos) de API Tokens personales de Atlassian
        utilizan HTTP Basic Authentication codificada en base64.
        """
        auth_str = f"{self.email}:{self._api_token}"
        encoded = base64.b64encode(auth_str.encode("utf-8")).decode("ascii")
        return f"Basic {encoded}"

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Ejecuta una solicitud HTTP a la API v2 con cabeceras seguras y saneamiento de errores."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        if params:
            query_string = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
            if query_string:
                url = f"{url}?{query_string}"

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "ConfluenceDocsPublisher/1.0",
            "Authorization": self._get_auth_header(),
        }

        body_bytes = None
        if data is not None:
            body_bytes = json.dumps(data).encode("utf-8")

        req = urllib.request.Request(url, data=body_bytes, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                resp_text = response.read().decode("utf-8")
                if resp_text:
                    return json.loads(resp_text)
                return {}
        except urllib.error.HTTPError as err:
            err_code = err.code
            try:
                err_body = err.read().decode("utf-8")
            except Exception:
                err_body = "<no-body>"

            # Saneamiento del mensaje: asegurar que no se filtren cabeceras, token ni email
            auth_b64 = self._get_auth_header().split(" ")[-1]
            clean_body = (
                err_body.replace(self._api_token, "[REDACTED_API_TOKEN]")
                .replace(self.email, "[USER_EMAIL]")
                .replace(auth_b64, "[REDACTED_AUTH]")
            )

            raise ConfluenceAPIError(
                f"Error HTTP {err_code} al llamar a {method} {endpoint}: {clean_body}",
                status_code=err_code,
                response_body=clean_body,
            ) from None
        except urllib.error.URLError as err:
            raise ConfluenceAPIError(f"Error de red o conexión al contactar Confluence: {err.reason}") from None
        except Exception as err:
            raise ConfluenceAPIError(f"Error inesperado durante la solicitud: {str(err)}") from None

    def get_page(self, page_id: str, body_format: str = "storage") -> Dict[str, Any]:
        """Obtiene los metadatos y contenido de una página por su ID numérico."""
        params = {"body-format": body_format}
        return self._request("GET", f"pages/{page_id}", params=params)

    def search_pages_by_title(self, title: str, space_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Busca páginas por título exacto en la API v2, filtrando opcionalmente por spaceId."""
        params: Dict[str, Any] = {"title": title, "status": "current"}
        if space_id:
            params["space-id"] = space_id

        res = self._request("GET", "pages", params=params)
        results = res.get("results", [])
        return results

    def create_page(
        self,
        space_id: str,
        title: str,
        parent_id: str,
        storage_xml: str,
    ) -> Dict[str, Any]:
        """Crea una nueva página en el espacio indicado bajo la página padre especificada."""
        payload = {
            "spaceId": str(space_id),
            "status": "current",
            "title": title,
            "parentId": str(parent_id),
            "body": {
                "representation": "storage",
                "value": storage_xml,
            },
        }
        return self._request("POST", "pages", data=payload)

    def update_page(
        self,
        page_id: str,
        space_id: str,
        title: str,
        parent_id: str,
        storage_xml: str,
        next_version: int,
        version_message: str = "Actualización automática de documentación técnica",
    ) -> Dict[str, Any]:
        """Actualiza una página existente gestionando el incremento de versión requerido por la API v2."""
        payload = {
            "id": str(page_id),
            "status": "current",
            "title": title,
            "parentId": str(parent_id),
            "body": {
                "representation": "storage",
                "value": storage_xml,
            },
            "version": {
                "number": next_version,
                "message": version_message,
            },
        }
        return self._request("PUT", f"pages/{page_id}", data=payload)
