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

## Flujo obligatorio

`main` no es una rama de trabajo: todos los cambios deben llegar mediante un
pull request desde una rama creada a partir de `main` actualizado.

1. Actualizar `main` antes de comenzar:

   ```bash
   git switch main
   git pull --ff-only origin main
   ```

2. Crear una rama propia con un nombre descriptivo:

   ```bash
   git switch -c feature/nombre-corto
   ```

   Se recomiendan los prefijos `feature/`, `fix/`, `test/`, `docs/` y `chore/`.

3. Trabajar únicamente en esa rama y mantener los cambios enfocados.

4. Ejecutar todas las pruebas antes de publicar:

   ```bash
   python -m pytest
   ```

5. Crear commits claros y publicar la rama con `git push -u origin
   nombre-de-rama`.

   Ejemplos de mensajes:

   ```text
   feat: add activity selection
   fix: handle missing forecast values
   test: cover precipitation threshold
   docs: clarify local setup
   chore: update repository configuration
   ```

6. Abrir un pull request hacia `main`.
7. Esperar a que GitHub Actions complete el check requerido `pytest`.
8. Abrir y revisar el Vercel Preview generado para el pull request. Las
   Preview protegidas requieren iniciar sesión con una cuenta que tenga acceso
   al proyecto Vercel; si un integrante no tiene acceso, debe solicitarlo a la
   persona propietaria del proyecto o pedirle un Shareable Link del deployment.
9. Solicitar revisión a otro integrante cuando el alcance o riesgo del cambio
   lo amerite. La aprobación es recomendada, pero no obligatoria.
10. Integrar solamente cuando la rama esté actualizada y el check requerido
    `pytest` esté verde.

Las ramas previstas para el trabajo de producción son:

- `feature/frontend-production`
- `feature/production-qa`
- `feature/secops-docs`

Cada integrante debe crear su propia rama desde `main` actualizado cuando
reciba sus instrucciones; estas ramas no se crean por adelantado. Persona 1
creará ramas específicas únicamente cuando necesite realizar cambios concretos.

## Contratos estables

Se consideran estables los endpoints `/locations`, `/weather` y
`/recommendation`, junto con sus parámetros y modelos de respuesta consumidos
por el frontend. También se mantiene la dirección arquitectónica
Open-Meteo → adaptadores → servicios → FastAPI.

Cualquier cambio incompatible debe coordinarse con Persona 1 antes de
implementarse y debe actualizar en el mismo trabajo todos sus consumidores,
pruebas y documentación.

## Reglas básicas

- No subir `.env`, credenciales, tokens, cachés ni entornos virtuales.
- Utilizar `.env.example` para documentar configuración sin secretos.
- No llamar Open-Meteo directamente desde el frontend.
- Mantener FastAPI, reglas internas y adaptadores en sus responsabilidades
  actuales.
- No cambiar endpoints, contratos o arquitectura fuera del proceso de
  coordinación descrito en esta guía.
- Toda nueva funcionalidad debe incluir pruebas y documentación proporcional.

## Pull requests

El pull request debe explicar qué cambia, por qué cambia y cómo se verificó.
Cada integrante puede integrar su propio pull request cuando `pytest` esté
verde; para cambios amplios o sensibles se recomienda solicitar revisión.
