"""
IntelliDesk AI — API Documentation Controller (Blueprint)
Serves the interactive Swagger UI and OpenAPI specifications.
Route prefix: /api/v1
"""

import json
import os
from flask import Blueprint, Response, current_app, render_template_string, jsonify
from app.utils.exceptions import NotFoundError

docs_bp = Blueprint("docs", __name__, url_prefix="/api/v1")

SWAGGER_UI_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=device-width, initial-scale=1" />
  <title>IntelliDesk AI — API Documentation</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/5.17.14/swagger-ui.css" />
  <link rel="icon" type="image/png" href="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/5.17.14/favicon-32x32.png" sizes="32x32" />
  <link rel="icon" type="image/png" href="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/5.17.14/favicon-16x16.png" sizes="16x16" />
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <style>
    html {
      box-sizing: border-box;
      overflow-y: scroll;
    }
    *, *:before, *:after {
      box-sizing: inherit;
    }
    body {
      margin: 0;
      background: #fafafa;
      font-family: 'Outfit', sans-serif !important;
    }
    /* Brand Header */
    .brand-header {
      background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
      color: #ffffff;
      padding: 1.5rem 2rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    }
    .brand-title {
      font-size: 1.5rem;
      font-weight: 700;
      letter-spacing: -0.025em;
      margin: 0;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }
    .brand-title span {
      background: linear-gradient(to right, #38bdf8, #818cf8);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    .brand-subtitle {
      font-size: 0.875rem;
      color: #94a3b8;
    }
    .swagger-ui .topbar {
      display: none !important;
    }
    .swagger-ui .info {
      margin: 20px 0 0 0 !important;
    }
    .swagger-ui .info .title {
      font-family: 'Outfit', sans-serif !important;
    }
  </style>
</head>
<body>
  <header class="brand-header">
    <h1 class="brand-title">IntelliDesk <span>AI</span></h1>
    <div class="brand-subtitle">Interactive API Playground</div>
  </header>

  <div id="swagger-ui"></div>

  <script src="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/5.17.14/swagger-ui-bundle.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/5.17.14/swagger-ui-standalone-preset.js"></script>
  <script>
    window.onload = () => {
      window.ui = SwaggerUIBundle({
        url: '/api/v1/docs/openapi.json',
        dom_id: '#swagger-ui',
        deepLinking: true,
        presets: [
          SwaggerUIBundle.presets.apis,
          SwaggerUIStandalonePreset
        ],
        layout: "BaseLayout",
        defaultModelsExpandDepth: -1,
        docExpansion: "list"
      });
    };
  </script>
</body>
</html>
"""

@docs_bp.route("/docs", methods=["GET"])
def get_docs():
    """GET /api/v1/docs — Render interactive Swagger UI documentation page."""
    return render_template_string(SWAGGER_UI_HTML)

@docs_bp.route("/docs/openapi.json", methods=["GET"])
def get_spec():
    """GET /api/v1/docs/openapi.json — Return the OpenAPI 3.0 specification."""
    static_folder = os.path.join(current_app.root_path, "static")
    spec_path = os.path.join(static_folder, "openapi.json")
    if not os.path.exists(spec_path):
        raise NotFoundError("OpenAPI specification file not found.")

    with open(spec_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data)
