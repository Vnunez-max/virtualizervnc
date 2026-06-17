# ARCHITECTURE D1 - Complemento de linea observada en deferred

Fecha: 2026-06-14

Estado:

```text
Documento conceptual operativo
```

## 1. Tesis corregida

El modulo general funciona y sigue siendo la columna vertebral de la unidad modular.

D1 no debe reemplazarlo ni competir con el. D1 debe actuar como complemento local sobre el residuo `deferred`.

La pregunta primaria de D1 no es:

```text
esto pertenece a una rejilla?
```

La pregunta primaria correcta es:

```text
esto es linea observada dentro del deferred?
```

Solo despues, en otro nivel separado, puede preguntarse:

```text
que rol geometrico podria tener esa linea observada?
```

## 2. Problema de base

El problema de base no era que el modulo general estuviera roto.

El problema era que, despues de aplicar el modulo general, quedaba un residuo `deferred` que mezclaba cosas distintas:

```text
linea observada no nombrada
marcas lineales no estructurales
texto o digitos
bordes o caja de pagina
curvas o trazas de datos
ruido o fragmentos ambiguos
```

El fallo conceptual era tratar ese `deferred` como una zona demasiado opaca.

El fallo computacional era exigir interpretacion de familia o contexto antes de aceptar una evidencia mas basica:

```text
hay pixeles observados con linealidad real
```

## 3. Jerarquia correcta

La jerarquia correcta queda asi:

```text
mask original observada
  -> modulo general unitario
    -> soporte aceptado / organizado / calibrado
    -> deferred residual
      -> D1.0: auditoria de linea observada en deferred
        -> linea observada
        -> no-linea observada
        -> ambiguo
      -> D1.1: clasificacion opcional de rol geometrico
        -> posible rol estructural
        -> posible rol no estructural
        -> reserva
      -> modulo posterior, si se aprueba
        -> uso controlado de evidencia lineal
```

D1.0 debe estar antes de cualquier interpretacion de rejilla, eje, borde, texto o curva.

D1.1 puede existir, pero no debe dominar la decision primaria. Su funcion es ordenar la linea observada ya detectada, no definir si algo es linea.

## 4. Regla critica

La regla global sigue siendo:

```text
ningun modulo puede ganar interpretacion perdiendo trazabilidad geometrica
```

Aplicada a D1:

```text
D1 puede aumentar visibilidad sobre deferred,
pero no puede inventar geometria,
no puede rellenar gaps como pixeles aceptados,
no puede crear lineas finales,
no puede borrar la condicion de deferred original,
no puede convertir rol probable en verdad geometrica.
```

Cada pixel marcado por D1 debe conservar:

```text
sample_id
x
y
source_deferred_map
linearity_hypothesis_id, si aplica
decision primaria: linea / no-linea / ambiguo
decision secundaria de rol, si aplica
```

## 5. Papel del modulo general

El modulo general sigue resolviendo el problema principal:

```text
organizacion global de la mascara
familias principales
soporte aceptado
calibracion modular
comparacion entre tests
unidad de trazabilidad global
```

D1 no debe contradecirlo. D1 observa solo lo que el modulo general no pudo cerrar.

Por eso D1 debe ser:

```text
deferred-only
complementario
auditable
local
geometricamente simple
sin verdad externa en runtime
sin OCR
sin semantica clinica
sin coordenadas manuales sample-specific
```

## 6. Papel de D1.0

D1.0 es la pieza mas importante de este complemento.

Pregunta:

```text
que pixeles deferred forman alineaciones simples observadas?
```

Salida conceptual:

```text
deferred_line_observed
deferred_not_line_observed
deferred_ambiguous
```

En la implementacion actual, D1.0 produjo sobre `test3.3`:

```text
deferred total:                 1885 px
deferred con linealidad simple: 1041 px
ratio:                          55.23%
```

Ese dato es el avance central:

```text
habia mucha linea observada dentro del deferred
```

## 7. Papel de D1.1

D1.1 es secundario.

No responde la pregunta:

```text
esto es linea?
```

Responde una pregunta posterior:

```text
si D1.0 ya encontro linea observada, que rol podria tener?
```

Por tanto, etiquetas como:

```text
grid_line_candidate
axis_line_candidate
tick_or_scale_mark
page_border_or_layout_box
text_or_digit_stroke
curve_or_data_trace
ambiguous_linear
```

deben entenderse como roles tentativos, no como decision primaria de linea.

Si una etiqueta de D1.1 introduce sesgo hacia rejilla, la arquitectura debe corregir la interpretacion:

```text
primero linea observada
despues rol probable
despues, solo si corresponde, uso por otro modulo
```

## 8. Que queda prohibido

Queda prohibido usar D1 para:

```text
reemplazar el modulo general
promover automaticamente deferred a geometria final
mezclar linea observada con pertenencia a rejilla
descartar no-grid como basura
cerrar gaps como si fueran pixeles observados
crear LineObjects finales
crear ejes, cruces, tablas, celdas u OCR
modificar V3.4.1
modificar V3.4.2
modificar resultados upstream
```

Especialmente:

```text
linea observada no equivale a rejilla
rol probable no equivale a geometria final
no-linea para D1 no equivale a inutil para el sistema
```

Lo que no sea linea observada debe quedar reservado para otros modelos futuros cuando corresponda.

## 9. Criterio de progreso

Vamos progresando bien si se cumplen estas condiciones:

```text
el modulo general conserva su papel principal
D1 trabaja solo sobre deferred
D1.0 mejora la visibilidad de linea observada
D1.1 no contamina la decision primaria
todo pixel marcado conserva trazabilidad
ninguna salida D1 crea geometria final
las reservas no-lineales siguen disponibles para modulos futuros
```

## 10. Formula corta

La formula operativa queda:

```text
modulo general primero
deferred despues
D1.0 reconoce linea observada
D1.1 ordena roles sin imponer rejilla
otro modulo posterior decide si usa esa evidencia
```

La realidad visual debe imponerse al computo en el primer nivel:

```text
si es linea observada, debe poder nombrarse como linea observada
```

Pero la interpretacion final debe seguir siendo disciplinada:

```text
nombrar linea observada no autoriza crear geometria final
```
