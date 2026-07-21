# Contribuir a PlanificaHoy

Esta guía establece un flujo mínimo para que el equipo trabaje sobre una base
común y verificable.

## Preparar el entorno

```bash
git clone https://github.com/DChristofileas/TG2_PrograWeb_G3.git
cd TG2_PrograWeb_G3
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest
```

En Windows PowerShell, la activación del entorno es:

```powershell
.venv\Scripts\Activate.ps1
```

## Flujo recomendado

1. Actualizar `main` antes de comenzar:

   ```bash
   git switch main
   git pull --ff-only origin main
   ```

2. Crear una rama con un nombre descriptivo:

   ```bash
   git switch -c feature/nombre-corto
   ```

   Se recomiendan los prefijos `feature/`, `fix/`, `test/`, `docs/` y `chore/`.

3. Mantener los cambios enfocados y ejecutar todas las pruebas:

   ```bash
   python -m pytest
   ```

4. Crear commits claros, por ejemplo:

   ```text
   feat: add activity selection
   fix: handle missing forecast values
   test: cover precipitation threshold
   docs: clarify local setup
   chore: update repository configuration
   ```

5. Publicar la rama y abrir un pull request hacia `main`.

## Reglas básicas

- No subir `.env`, credenciales, tokens, cachés ni entornos virtuales.
- Utilizar `.env.example` para documentar configuración sin secretos.
- No llamar Open-Meteo directamente desde el frontend.
- Mantener FastAPI, reglas internas y adaptadores en sus responsabilidades
  actuales.
- No cambiar endpoints, contratos o arquitectura sin coordinarlo con el equipo.
- Toda nueva funcionalidad debe incluir pruebas y documentación proporcional.

## Pull requests

El pull request debe explicar qué cambia, por qué cambia y cómo se verificó. Al
menos otro integrante debería revisarlo antes de integrarlo cuando la dinámica
del curso lo permita.
