# Datos

## Qué hay en el repositorio

Los **datos procesados** están versionados y son los que consume el tablero:

| Ruta | Contenido |
|---|---|
| `web/data.js` | Las 42 políticas, los seis criterios, los estándares de servicio y los 2,480 indicadores con su serie 2019–2025 |
| `web/data/*.json` | Tablas derivadas: resumen, políticas, criterios, cruce mejora × meta, estándares |
| `web/data/rc/rc_0NN.json` | Un reporte de cumplimiento por política, en bloques (párrafos, viñetas, notas al pie), para carga bajo demanda |

Los genera `scripts/preparar_datos.py` a partir de los archivos de origen, y el mismo
script **verifica sus resultados contra el informe publicado** y se detiene si alguna
cifra no coincide.

## Qué no está, y por qué

Los seis archivos de origen **no se versionan**. Van en una carpeta `fuentes/`, hermana
del repositorio y excluida en `.gitignore`:

| Archivo | Qué es |
|---|---|
| `evaluacion_ispn_2025_sin_complementarios.xlsx` | Resultados de la evaluación del ISPN 2025 por política, criterio e indicador |
| `progreso_sin_complementarios.json` | Avance del procesamiento de la evaluación |
| `matriz_rc_2025.xlsx` · `matriz_rc_2024.xlsx` | Reportes de cumplimiento de las rectorías y conductoras |
| `base_seguimiento_pn_2025.xlsx` | Reporte de seguimiento de indicadores, 2019–2025 |
| `matriz_consistencia_50_pn.xlsx` | Matriz de consistencia de las políticas nacionales aprobadas |

La razón es que las bases de trabajo traen datos que no corresponde publicar: una hoja
con usuarios y contraseñas de coordinadores de los ministerios, y columnas con nombres
y correos de coordinadores sectoriales. El procesamiento no los usa y el tablero no los
muestra.

## Cómo obtener los datos

El contenido sustantivo es público y está en el **Informe Anual de Políticas Nacionales
2025** del CEPLAN: [PDF del informe](https://www.minsa.gob.pe/Recursos/OTRANS/09GestionIns/informe/2026/Informe-Anual-de-Pol%C3%ADticas-Nacionales-2025.pdf). El tablero reproduce sus cifras y las
verifica contra él.

Para reejecutar el procesamiento hace falta la versión de trabajo de las bases, que se
solicita al CEPLAN. Una vez en `fuentes/` (o en la ruta que indique la variable de
entorno `ISPN_FUENTES`):

```bash
python scripts/preparar_datos.py
python scripts/empaquetar.py
```
