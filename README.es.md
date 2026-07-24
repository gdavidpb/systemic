# systemic

*[Read this in English](README.md)*

**Una skill de Claude Code que audita software como audita un sistema la
Teoría General de Sistemas — y reporta las propiedades que viola, no las
líneas que escribió mal.**

La mayoría de los errores graves no son typos. Son violaciones de propiedades
sistémicas: una operación que produce un estado que el sistema no puede
representar, un operador sin inverso, un valor que está a la vez almacenado y
derivado, un ciclo de vida cuyas reglas declaradas el código contradice.
`systemic` modela tu solución como un sistema —elementos, operadores, máquinas
de estados conceptuales— y verifica doce propiedades de consistencia contra
él.

Funciona sobre código, sobre documentos de diseño, o sobre ambos.

```
/systemic analiza el ciclo de vida de pedidos en src/orders
```

---

## La idea

Un sistema es *un conjunto de componentes que se relacionan entre sí con un
único objetivo*. No solo las piezas — las piezas **y su capacidad de unirse**.
Dos categorías:

- **Elementos** — lo concreto: tus modelos, entidades, registros.
- **Operadores** — lo abstracto que los relaciona: tus casos de uso,
  endpoints, jobs, handlers.

Un sistema es **consistente** cuando está libre de contradicciones, y la
prueba estrella es la **clausura**: toda operación sobre los elementos del
sistema debe producir un elemento del sistema. Los enteros no son cerrados
bajo división — `1/2 = 0.5`, y `0.5` no existe ahí. Dos elementos legítimos,
un operador legítimo, y un resultado que el sistema no tiene forma de
representar.

Ese fallo tiene un análogo exacto en software, y `systemic` está construida
para encontrarlo:

```python
STATUS = {"draft", "pending_payment", "paid", "shipped", "delivered", ...}

def refund(order):
    order.status = "refund_pending"   # ← no está en STATUS. 1/2 = 0.5.
```

El pedido queda fuera de toda operación que el sistema define. No es terminal,
así que nada lo archiva. No está declarado, así que nada lo lee. Un linter ve
una asignación de string. `systemic` ve una violación de clausura y lo dice.

## Instalación

El nombre de la carpeta debe coincidir con el de la skill, así que clónala
como `systemic`:

```bash
git clone https://github.com/gdavidpb/systemic ~/.claude/skills/systemic
```

Eso es todo — Claude Code la toma de `~/.claude/skills/`. Para instalarla solo
en un proyecto, clónala en `.claude/skills/systemic` dentro del repo.

## Uso

Invócala por su nombre, o simplemente describe el problema — la skill se
dispara por la intención, no por la palabra clave:

```
/systemic audita el ciclo de vida de suscripciones en billing/
```
```
¿Este diseño es consistente? [pega o apunta a un documento]
```
```
Encuentra contradicciones entre lo que promete el README y lo que hace el código.
```
```
Revisa mi máquina de estados — creo que hay transiciones que nadie maneja.
```

Apúntala a una ruta, a un documento de diseño, o a ambos. Ante un repo grande
sin foco, propondrá acotar al subsistema con más estado — que es donde el
análisis rinde.

## Qué verifica

Doce propiedades. Cuatro vienen directamente del marco sistémico; el resto
aplican el mismo principio —la consistencia— a software real, con colas,
reintentos y concurrencia.

| # | Verificación | La pregunta que hace |
|---|---|---|
| 1 | **Clausura** | ¿Toda operación produce un estado que el sistema puede representar? |
| 2 | **Ambigüedad de operador** | ¿Alguna operación admite dos interpretaciones razonables? |
| 3 | **Completitud de transiciones** | Para cada par (estado, operador): ¿definida, prohibida, o un **hueco**? |
| 4 | **Alcanzabilidad** | Estados que nada produce; estados de los que nada sale; transiciones muertas. |
| 5 | **Estados ilegales representables** | ¿Puede el modelo persistir una combinación que el negocio prohíbe? |
| 6 | **Invariantes y fallo parcial** | ¿Qué se rompe si el operador muere a medias, y quién lo repara? |
| 7 | **Idempotencia** | Clausura bajo repetición: ¿el reintento duplica el efecto? |
| 8 | **Concurrencia** | Dos operadores sobre un elemento: ¿conmutan, se serializan, o se pisan? |
| 9 | **Simetría** | Abrir sin cerrar, bloquear sin liberar, pausar sin reanudar. |
| 10 | **Expresión mínima** | Un valor almacenado y derivado a la vez: dos fuentes de verdad que divergen. |
| 11 | **Límites del sistema** | Requisitos fuera del conjunto representable — los hacks son la evidencia. |
| 12 | **Bucles de retroalimentación** | Reintentos que alimentan colas que alimentan reintentos, sin amortiguador. |

Aplica las que tu material permite verificar honestamente, y declara cuáles no
aplicaron y por qué.

## Qué obtienes

Un archivo Markdown en tu disco — `systemic-out/<alcance>.md`. Nunca un
artifact, nunca una página servida desde localhost.

- **Sistemas identificados** — tabla de sistemas, objetivos, elementos,
  operadores.
- **Máquinas conceptuales** — diagramas mermaid de lo *declarado* y lo
  *construido*, más la matriz estado × operador cuando la máquina es
  suficientemente pequeña. La divergencia entre ambos diagramas suele ser lo
  más valioso del reporte.
- **Hallazgos** — ordenados por severidad, cada uno con el check del que
  salió, la evidencia, el diagnóstico sistémico y una recomendación concreta.
- **Piezas faltantes** — los componentes que el sistema necesita; dónde el
  equipo está tallando el requisito en el tablero en vez de fabricar piezas.
- **Límites y no verificado** — qué no puede representar el sistema, y qué
  checks no pudieron correrse con el material disponible.

### Cada hallazgo lleva una etiqueta de honestidad

| Etiqueta | Significa |
|---|---|
| `INCONSISTENCY` | Una contradicción **demostrada** con evidencia. El sistema hace X y también no-X. |
| `RISK` | Se rompe bajo una condición concreta y enunciada — la condición queda escrita. |
| `AMBIGUITY` | Subespecificado. La skill **no adivina**: enuncia la pregunta que tu arquitecto o dueño de producto tiene que responder. |

La severidad es `critical` / `high` / `medium` / `low`, calibrada por el daño
que el hallazgo realmente causa.

Las etiquetas y severidades se mantienen en inglés en todos los idiomas, a
propósito: son un enum, no prosa, y así los reportes siguen siendo comparables
entre proyectos e idiomas.

**La regla de honestidad no es negociable**: ningún hallazgo sin evidencia
efectivamente leída. Toda afirmación cita `archivo:línea` o una sección del
documento. Lo que no se puede evidenciar, no se reporta.

## Un ejemplo real

Corrida contra un módulo de pedidos deliberadamente roto
([`evals/fixtures/orders/`](evals/fixtures/orders/)), el reporte lee la matriz
así:

> De 56 celdas de la matriz estado × operador, **una sola columna** está
> correctamente cerrada (`deliver`) y **43 son huecos**. `add_item` y
> `apply_discount` no aparecen porque son ciegas al estado: mutan un pedido
> `delivered` igual que uno `draft`.
>
> La función `is_final()` existe y **ningún operador la llama**. El sistema
> declara la noción de estado final y no la usa.

Y cierra nombrando la única pieza faltante que disuelve nueve de los catorce
hallazgos de golpe:

> Cada operación escribe `order.status` directamente. Eso significa que la
> máquina de estados **no está implementada en ninguna parte** — existe como
> prosa en el README y como conjunto de strings en `models.py`, pero ningún
> componente la hace cumplir. El equipo está cortando la madera: cada operador
> talla su transición a mano, y por eso cada uno puede tallarla mal de una
> manera distinta.

Esa es la diferencia con un code review. Un review dice *falta un guard en la
línea 30*. Esto dice *la máquina no está implementada, aquí está la pieza, y
estos son los nueve hallazgos que hace desaparecer*.

## Qué no es

- **No es un linter.** Lee significado, no patrones. No va a encontrar tus
  imports sin usar, y sí va a encontrar que tu README prohíbe lo que tu código
  permite.
- **No es un escáner de seguridad.** Usa uno; son complementarios.
- **No es gratis.** El pensamiento sistémico es caro y no apunta a apps
  triviales. Apunta a sistemas con estado real —ciclos de vida, workflows,
  sagas, cualquier cosa con una columna `status`— donde una inconsistencia
  cuesta dinero. El reporte refleja ese criterio y recomienda componentes
  nuevos solo cuando el beneficio los justifica.

## Idioma

El reporte se escribe en el idioma que pidas. Si nombras uno, gana; si no,
sigue el idioma en que estés escribiendo. Solo las etiquetas de honestidad y
las severidades se mantienen como keywords fijos.

## Estructura

```
SKILL.md                      la skill: fases, estructura del reporte, reglas
references/
  gst-framework.md            el vocabulario conceptual, se lee antes de la fase 1
  checks.md                   cómo detectar cada uno de los 12, se lee en la fase 2
evals/
  evals.json                  6 evals con aserciones
  fixtures/orders/            módulo de código con 9 defectos sembrados
  fixtures/rental-doc/        documento de diseño con 7 defectos sembrados
  fixtures/booking-saga/      saga con compensaciones: fallo parcial y bucles
  fixtures/clean-ticket/      ciclo de vida correcto: control de falsos positivos
```

## Evals

`evals/evals.json` tiene seis casos con aserciones explícitas:

1. **seeded-defects-code** — 9 defectos sembrados en un módulo Python.
2. **design-doc-only** — un documento de diseño sin código; verifica que la
   skill cite solo secciones del documento y no invente rutas de código.
3. **real-repo-lifecycle** — plantilla; aporta tu propio repo y ciclo de vida.
4. **explicit-report-language** — prompt en español pidiendo reporte en
   inglés; verifica que la petición explícita gane y las etiquetas no se
   traduzcan.
5. **saga-compensations-and-loops** — una saga con compensaciones; ejercita
   los checks 6 y 12, que las otras fixtures apenas tocan.
6. **clean-code-no-false-positives** — un módulo deliberadamente correcto.
   Todas las demás fixtures premian encontrar cosas; ésta se califica por lo
   que la skill **no** reporta. Una corrida que «encuentra más» aquí es una
   corrida peor.

Sustituye `<SKILL_DIR>` por la ruta absoluta de la skill al correrlas.

La eval 6 es la que más importa a medida que la skill cambia. Una herramienta
que reporta problemas vale lo que valga su tasa de falsos positivos, y todas
las demás evals empujan hacia reportar más.

## Contribuir

Las contribuciones más útiles son **fixtures**: un ciclo de vida con un
defecto que la skill no encuentre, más la aserción que debería haberlo
atrapado. Un check que nunca dispara sobre ninguna fixture es un check en el
que nadie puede confiar.

## Licencia

MIT — ver [LICENSE](LICENSE).
