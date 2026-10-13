# Findings log

Data: FIRMS MODIS C6.1 and VIIRS S-NPP, box 73.8,27.6,77.6,32.6 (Punjab + Haryana), 2012-2025.
Filters: type 0 (vegetation fire), daytime, MODIS confidence >= 30, VIIRS confidence != low.

1. Aqua minus S-NPP median pass time: about 0.1-0.25 h (2012-2022), then 0.47 (2023), 0.82 (2024), 1.43 h (2025).
2. Oct-Nov S-NPP/Aqua FRP ratio: about 2.0 (2012-2022) to 0.76 (2025). Count ratio: 4.6-5.8 to 2.17.
3. FRP per detection, Aqua/S-NPP: flat at about 2.4-2.7 (2.85 in 2025). The change is in how many fires are seen, not their intensity.
4. S-NPP Oct-Nov night/day detection ratio: 0.002-0.008 (2012-2022), 0.050 (2024), 0.054 (2025). Daytime detections fell from 91,523 (2021) to 9,126 (2025); night detections did not fall.
5. Gap model (log-linear, 14 years): at zero gap, S-NPP/Aqua = 5.35 (counts) and 2.19 (FRP); each extra hour of Aqua delay multiplies the ratio by 0.55 and 0.50; R2 = 0.92 and 0.94 (in-sample).
6. Caveat: Aqua orbit drift and the reported shift of burning to later in the day overlap in time and are not yet separated.

Sources: NASA Aqua mission site (orbit drift), iFOREST Stubble Burning Status Report 2025, ISRO SAC study in Current Science (Nov 2025).
7. Out-of-sample test: model trained on 2012-2023 predicts 2024/2025 Oct-Nov S-NPP/Aqua ratios within 3-9%; leave-one-year-out median error about 6%, worst about 15%.
8. NOAA-20 and S-NPP pass at the same local time (differences <= 0.1 h); N20/S-NPP ratio stays 0.98-1.05 whole year and 0.99-1.15 in Oct-Nov (2018-2025): the S-NPP decline is not an instrument artifact, and ~15% is the noise floor between identical VIIRS sensors.
9. NOAA-21 (NRT data, 2024-2025): counts match S-NPP but FRP is 12-30% higher; unexplained, treated as provisional.