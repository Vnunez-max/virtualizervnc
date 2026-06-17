# Unidad modular funcional VM V1

Fecha: 2026-06-15

Este paquete contiene solo la unidad funcional para copiar a una VM.

No incluye datasets, samples, resultados historicos ni outputs de test.

## Contenido

```text
modules/      codigo runtime de la unidad modular
models/       artefacto entrenado minimo usado por G1.0-CAL V1
contracts/    contratos tecnicos de los modulos incluidos
docs/         nota arquitectonica D1 como complemento deferred-only
tools/        verificador de paquete
requirements.txt
```

## Excluido a proposito

```text
datasets DG1/A4G6
samples sinteticos
outputs historicos test2.1/test3.2/test3.3
auditorias historicas
imagenes de resultados historicos
__pycache__
.DS_Store
V3.4.1 congelado
modificaciones de V3.4.2
```

V3.4.1 no se incluye. V3.4.2 puede estar incluido como modulo upstream
congelado para runtime, pero no debe modificarse.

## Regla critica

```text
Ningun modulo puede ganar interpretacion perdiendo trazabilidad geometrica.
```

Los modulos incluidos siguen escribiendo mapas, tablas, memberships, summaries y auditorias cuando se ejecutan con inputs validos.

## Requisitos

En la VM:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python tools/verify_vm_runtime.py
```

La verificacion comprueba:

```text
compilacion de todos los modules/*.py
import de numpy y Pillow
presencia del modelo G1.0-CAL V1
ausencia de datasets/samples/resultados historicos en el paquete
```

## Uso operativo

No uses los defaults historicos de los scripts. En VM, pasa siempre rutas explicitas.

Secuencia conceptual:

```text
U1.1
L1.0
L1.1
L1.2
L1.2-CAL
G1.0
G1.0-CAL V1
UNIT
D1.0 opcional sobre deferred
D1.1 opcional sobre D1.0
X3.0 integracion entrenable-aware
```

El adaptador G1.0-CAL V1 usa el modelo incluido:

```bash
python modules/g1/module_g1_0_cal_v1_apply_trainable_calibrator.py \
  --g1-run-dir /ruta/a/g1_0_run \
  --model-dir models/g1_0_cal_v1_deferred_family \
  --out /ruta/a/g1_0_cal_v1_out \
  --sample-id sample_id
```

El ensamblador de unidad completa requiere las salidas U/L/G ya generadas:

```bash
python modules/unit/module_unit_full_model_v1_apply.py \
  --u1-1-dir /ruta/a/u1_1 \
  --l1-0-dir /ruta/a/l1_0 \
  --l1-1-dir /ruta/a/l1_1 \
  --l1-2-dir /ruta/a/l1_2 \
  --l1-2-cal-dir /ruta/a/l1_2_cal \
  --g1-0-dir /ruta/a/g1_0 \
  --g1-0-cal-v1-dir /ruta/a/g1_0_cal_v1 \
  --out /ruta/a/unit_out \
  --sample-id sample_id
```

D1.0 es complementario: solo analiza deferred y nombra linea observada sin crear geometria final.

```bash
python modules/d1/module_d1_0_deferred_simple_linearity_auditor.py \
  --g1-cal-dir /ruta/a/g1_0_cal_v1_out \
  --unit-dir /ruta/a/unit_out \
  --out /ruta/a/d1_0_out \
  --sample-id sample_id
```

D1.1 es secundario: clasifica roles de la linea observada por D1.0, sin imponer rejilla y sin crear geometria final.

```bash
python modules/d1/module_d1_1_deferred_linear_role_classifier.py \
  --d1-dir /ruta/a/d1_0_out \
  --unit-dir /ruta/a/unit_out \
  --out /ruta/a/d1_1_out \
  --sample-id sample_id
```

X3.0 integra la unidad funcional con C1 opcional, G1.0-CAL V1 y D1,
escribiendo mapas de influencia entrenable sin convertir toda la unidad en
modelo black-box. C1 y D1 son capas funcionales activas; C1-CAL/D1-CAL son
solo slots entrenables reservados hasta contrato.

```bash
python modules/x3/module_x3_0_trainable_geometric_evidence_unit.py \
  --unit-dir /ruta/a/unit_out \
  --g1-cal-dir /ruta/a/g1_0_cal_v1_out \
  --d1-0-dir /ruta/a/d1_0_out \
  --d1-1-dir /ruta/a/d1_1_out \
  --model-dir models/g1_0_cal_v1_deferred_family \
  --out /ruta/a/x3_out \
  --sample-id sample_id \
  --c1-0-dir /ruta/opcional/a/c1_0_out \
  --c1-1-dir /ruta/opcional/a/c1_1_out
```

## Nota sobre inputs

Este paquete es runtime de unidad modular, no contiene los datos de entrada.

Para ejecutar toda la cadena desde cero, la VM debe tener disponibles los outputs upstream esperados por cada modulo. Los contratos en `contracts/` documentan entradas/salidas e invariantes.

## Paquete limpio

Este zip debe mantenerse como codigo funcional. Si se generan resultados en VM, guardarlos fuera de esta carpeta o en un directorio de ejecucion separado.
