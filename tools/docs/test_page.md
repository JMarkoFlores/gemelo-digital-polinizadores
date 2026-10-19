# Prueba de publicación automática — GDP

Esta página constituye una **prueba controlada de publicación automatizada** desde el repositorio `gemelo-digital-polinizadores` hacia el espacio **GDP** en Confluence Cloud. Su objetivo es validar la conversión de Markdown a formato _storage_ XHTML de Confluence, la autenticación segura sin exposición de secretos y el control de versiones idempotente.

---

## 1. Verificaciones del Entorno de Publicación

Los siguientes elementos han sido comprobados antes de la emisión del documento:

- Conexión al sitio Atlassian Cloud (`unitru-team-hpj93f6y.atlassian.net`).
- Resolución del identificador numérico de espacio (`spaceId`) a partir de la página raíz.
- Inyección de credenciales mediante variables de entorno o entrada oculta en terminal.

### Pasos del Procedimiento de Despliegue

1. Ejecutar el modo de comprobación de conexión (`--check`).
2. Realizar una simulación en seco (`--dry-run`) para inspeccionar el contenido generado.
3. Ejecutar la publicación explícita (`--publish`) para crear o actualizar la página hija.

---

## 2. Parámetros de la Prueba

| Parámetro              | Valor Configurado                | Descripción Técnica                               |
| :--------------------- | :------------------------------- | :------------------------------------------------ |
| **Espacio Confluence** | `GDP`                            | Clave del espacio documental de destino           |
| **Página Raíz Padre**  | `2097153`                        | Identificador de la página superior jerárquica    |
| **Rama de Trabajo**    | `docs/automatizacion-confluence` | Rama autorizada de documentación                  |
| **Formato de Cuerpo**  | `storage` (XHTML)                | Formato nativo de almacenamiento en Confluence v2 |
| **Control de Estado**  | Local excluido de Git            | Persistencia del ID y hash de contenido           |

---

## 3. Ejemplo de Integración Técnica

El siguiente bloque de código ilustra la consulta básica de salud del backend del gemelo digital en Python:

```python
import urllib.request
import json

def verificar_estado_gemelo(api_url="http://localhost:8000/health"):
    """Consulta el estado del modelo surrogate cargado en el backend."""
    try:
        req = urllib.request.Request(api_url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as response:
            datos = json.loads(response.read().decode("utf-8"))
            print(f"Estado: {datos.get('status')} | Modelo: {datos.get('model_version')}")
            return datos.get("model_ready", False)
    except Exception as error:
        print(f"Error de conexión: {error}")
        return False

if __name__ == "__main__":
    listo = verificar_estado_gemelo()
    print("Metamodelo operativo:", listo)
```

> **Nota:** Esta página fue generada y publicada de forma programática. No modifique manualmente su contenido en Confluence si desea preservar la sincronización con el repositorio de documentación.

Actualización de prueba: se verifica que el publicador conserva el mismo ID de página.
