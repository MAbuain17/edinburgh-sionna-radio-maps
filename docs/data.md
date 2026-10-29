# Data and model conventions

## Study extent

The scoring boundary is [OpenStreetMap way 9514792](https://www.openstreetmap.org/way/9514792), covering 18.93 hectares. The surrounding scene covers 990 by 750 metres and contains 855 building parts, including 66 inside the selected campus polygon. The University of Edinburgh describes a wider 35-hectare King's Buildings estate; the study uses the explicitly mapped polygon as its reproducible scoring extent.

The OSM snapshot has a database timestamp of 4 October 2026, 21:52:50 UTC. Cached Mapzen / Tilezen Terrarium tiles supply the terrain elevations. Source links and input checksums are stored in `data/provenance.json`.

## Coordinates and geometry

`data/buildings.geojson` and `data/campus_boundary.geojson` use WGS84 longitude and latitude. `data/buildings_local.geojson` contains local metric coordinates for the simulation, with its convention recorded in the file and in `data/metadata.json`.

The local frame uses UTM zone 30N, with an origin at 55.922 degrees N, 3.175 degrees W. The UTM origin is approximately E 489063.667 m, N 6197412.288 m. The source terrain elevation reference is 80.738 m. `geodesy.py` implements the forward and inverse coordinate transforms.

Building outlines are extruded with flat roofs. Five campus parts use explicit OSM heights, 44 use mapped storey counts multiplied by 3.5 m, and 17 use a 10.5 m default. Across the full scene, 535 of 855 parts use the default. Foundation and roof elevations account for terrain under each footprint. Courtyard holes are preserved in triangulation.

## Scenario

| Parameter | Setting |
|---|---|
| Frequencies | 2.4, 3.5 and 5.8 GHz |
| Sites | A: Murray Library; B: James Clerk Maxwell Building; C: Joseph Black Building |
| Placement | Hypothetical rooftop positions, 3 m above the modeled roof |
| Antenna | One isotropic, vertically polarized element per site |
| Power | 30 dBm per active site |
| Propagation | Line of sight and specular reflection, maximum depth 3 |
| Materials | ITU concrete for buildings; ITU wet ground for terrain |
| Receiver surface | Terrain translated vertically by 1.5 m |
| Measurement mesh | 10 m grid, two triangles per cell |
| Noise | 20 MHz bandwidth, 7 dB noise figure, -174 dBm/Hz |
| Sampling | 20 million rays per transmitter per seed; seeds 17 and 29 |
| Study targets | RSS >= -85 dBm; SINR >= 5 dB |

The propagation model covers outdoor geometry and specular interactions. Diffraction, diffuse scattering, refraction, vegetation, vehicles, indoor receivers and external networks are outside the experiment. Field calibration can refine the heights, materials and antenna assumptions.

## Result arrays and metrics

Each `results/rt_*.npz` stores:

| Array | Shape | Meaning |
|---|---|---|
| `path_gain` | `[site, triangle]` | Mean linear path gain over the saved seeds |
| `seed_gains` | `[seed, site, triangle]` | Linear gains for each run |

Site order is A, B, C. Triangle order follows `data/measurement.npz`, which contains `vertices`, `faces`, `centers`, `areas` and `mask`. Path gain is dimensionless. Convert a positive gain to decibels with `10 log10(g)`.

Received power in mW is `10^(P_dBm/10) * path_gain`. Best-site RSS is the largest received power among active sites, expressed in dBm. SINR divides that serving power by the sum of other active-site powers and thermal noise. All active sites share the same fully loaded channel. With one active site, the metric becomes SNR. Each added site contributes an additional 30 dBm transmitter, so total transmitted power increases with site count.

Reported percentages are weighted by terrain-triangle surface area. The outdoor mask selects triangle centroids inside the campus polygon and outside building footprints. The explorer uses triangle counts for its live display; its rounded percentages can differ slightly from the area-weighted report.

RSS represents total received power. LTE/NR RSRP and throughput require their own system and resource models. Zero path gain identifies a cell with no sampled path in the configured model; CSV decibel fields are blank for those cells, and the explorer applies a display floor.

