# How AI tools were used

Tool: Claude (Anthropic), used in chat sessions. Editor: Google Antigravity IDE.

## What the AI helped with
- Early analysis, notebooks 01-09 (12-13 October 2026): written with Claude's help (code and explanations), then run and reviewed by me.
- Harmonisation scripts notebooks/10_harmonize.py, 11_harmonize_monthly.py and 12_final_series.py, and the forecast backtest notebooks/13_forecast_backtest.py, written with Claude on 14 November 2026.
- The web app (web/src/App.tsx, web/src/MapView.tsx and configuration), written with Claude, including fixes for MapLibre and Vite errors.
- Drafts of the README, this statement, the sources list and the pitch outline.
- Explaining terminal, Git and build errors.

## What I did myself
- Chose the challenge and the study area, and requested and downloaded the NASA FIRMS data.
- Ran every script and the app on my own machine and reported the outputs back; results were checked against the earlier notebooks (for example, the gap-model coefficients matched notebook 07).
- Reviewed the text of the app and the documents before submitting.

## Where AI-written work was wrong, and how it was caught
- A first month-by-month delay model failed out of sample (median error 60%); it was replaced by a simpler design after testing.
- A first version of the map did not draw because of MapLibre 6 changes (no default export, separate worker file); it was fixed after reading the browser errors.
- A forecast was considered; a backtest showed that simple forecasts fail after 2022, so none is offered.
