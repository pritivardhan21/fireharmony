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