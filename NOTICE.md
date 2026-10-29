# Sources and attribution

Original study code is distributed under the [MIT license](LICENSE). Geographic data and dependencies retain their respective licenses.

## Geographic data

- Copyright [OpenStreetMap contributors](https://www.openstreetmap.org/copyright). OpenStreetMap data are available under the Open Database License (ODbL). Derived geographic datasets remain subject to the applicable ODbL attribution and share-alike terms.
- Terrain: [Mapzen / Tilezen Terrain Tiles](https://registry.opendata.aws/terrain-tiles/). Underlying elevation sources and their attribution are documented in the [Tilezen source register](https://github.com/tilezen/joerd/blob/master/docs/attribution.md).
- Campus context: [University of Edinburgh location and maps](https://science-engineering.ed.ac.uk/about/location-map) and [university maps](https://www.ed.ac.uk/maps).

The cached inputs and source checksums are listed in `data/provenance.json`.

## Software references

- [Sionna RT](https://github.com/NVlabs/sionna-rt): ray tracing and radio-map computation.
- [NVIDIA sionna-large-radio-maps](https://github.com/NVlabs/sionna-large-radio-maps): geographic orchestration and export conventions referenced by this study; Apache License 2.0.
- [Mitsuba](https://github.com/mitsuba-renderer/mitsuba3) and [Dr.Jit](https://github.com/mitsuba-renderer/drjit): rendering and execution backends.

Dependency licenses are provided by their upstream distributions. The repository links to the NVIDIA pipeline rather than redistributing its source archive.

