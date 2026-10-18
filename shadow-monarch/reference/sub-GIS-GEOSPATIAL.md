# sub-GIS-GEOSPATIAL — Authoring Rules for PostGIS, GeoJSON, MapLibre/Leaflet & Spatial Indexing

Use when building map visualizations, asset/fleet tracking, geofencing, territory/boundary management (provinsi/kabupaten/desa),
distance/radius search, or geospatial data pipelines using PostGIS, GeoJSON, Vector Tiles, H3, MapLibre GL, Mapbox, or Leaflet.

## 1. Coordinate order & CRS / SRID discipline (source of 80% of GIS bugs)

- **Always verify coordinate order (`[Longitude, Latitude]` vs `[Latitude, Longitude]`)**:
  - **GeoJSON (RFC 7946), PostGIS (`ST_MakePoint(lng, lat)`), MapLibre GL, Mapbox GL, Turf.js, OSRM**: strictly use
    **`[Longitude, Latitude]` (`[X, Y]`)** (e.g., Jakarta is `[106.8456, -6.2088]`).
  - **Leaflet (`L.latLng(lat, lng)`), Google Maps JS API**: use **`[Latitude, Longitude]`**.
  - Validate ranges at input boundaries: `latitude` $\in [-90, 90]$ (Indonesia $\approx [-11, 6]$), `longitude` $\in [-180, 180]$ (Indonesia $\approx [95, 141]$). Reject `(0, 0)` ("Null Island") when GPS hardware fails to lock.
- **Coordinate Reference Systems (SRID)**:
  - **`EPSG:4326` (WGS 84)**: standard GPS storage and GeoJSON interchange in degrees.
  - **`EPSG:3857` (Web Mercator)**: slippy map tile rendering only — never calculate real-world area or distance directly in `3857` without geodesic correction.

## 2. PostGIS authoring rules

- **`geography(GeometryType, 4326)` vs `geometry(GeometryType, 4326)`**:
  - Use **`geography(Point, 4326)`** when calculating real-world distances or radius searches in **meters** across regions.
  - Use **`geometry(Polygon, 4326)`** when you need fast planar topological operations (`ST_Intersection`, `ST_Union`, MVT tile generation) and cast or transform to an appropriate local UTM zone or `geography` when computing exact area in $\text{m}^2$ / hectares.
- **Spatial indexing (mandatory)**:
  ```sql
  CREATE INDEX CONCURRENTLY idx_locations_geom ON locations USING GIST (geom);
  ```
- **Index-friendly proximity queries**:
  - **ALWAYS use `ST_DWithin(geom, target_geom, radius_meters)`** for radius searches — it uses the `GIST` index.
  - **NEVER use `WHERE ST_Distance(geom, target_geom) < 1000`** — `ST_Distance` in `WHERE` performs a full table sequential scan!
  - For $K$-Nearest Neighbors (KNN), use the `<->` distance operator in `ORDER BY geom <-> ST_SetSRID(ST_MakePoint($1, $2), 4326) LIMIT 10`.
- **Polygon validity**: repair imported shapefile/GeoJSON polygons with `ST_MakeValid(geom)` and enforce `ST_IsValid(geom)` before storing boundary polygons.

## 3. Vector Tiles (`MVT` / `PMTiles`) & large dataset rendering

- **Never send > 2,000 raw GeoJSON polygons or > 10,000 points directly to the browser**:
  - For medium point datasets (5k–50k points): use WebGL layers (MapLibre `circle` / `symbol` layer with GeoJSON `cluster: true`, or `deck.gl`), never thousands of DOM `<div>` markers in Leaflet.
  - For large polygon/parcel datasets (RTRW, plantation blocks, administrative boundaries): serve **Mapbox Vector Tiles (`.mvt` / `.pbf`)** generated dynamically via PostGIS `ST_AsMVT` / `pg_tileserv` / `martin` or pre-built static **`PMTiles`** on S3/CDN.
- **Geometry simplification**: simplify complex coastal/administrative boundaries per zoom level (`ST_SimplifyPreserveTopology`) and truncate GeoJSON coordinate precision to 6 decimal places ($\approx 11\text{ cm}$ accuracy) to cut payload size by 40%+.

## 4. Fleet tracking, Geofencing & H3 Spatial Indexing

- **Geofencing**: pre-filter candidate fences with bounding-box index (`geom && point`), then verify exact containment (`ST_Contains(fence_geom, point)`). Apply hysteresis (e.g., require 2 consecutive GPS pings or $\ge 15\text{m}$ inside/outside buffer) so GPS jitter near a boundary does not spam Entry/Exit alerts.
- **Uber H3 hexagonal indexing**: use H3 cell IDs (`bigint` / 15-char hex string at resolution 7–10) for fast spatial aggregation, heatmaps, surge pricing zones, and partitioning without expensive polygon joins.
