"""Smoke tests: the package imports and exposes its public API surface."""


def test_package_imports():
    import geostl

    assert geostl.__version__


def test_public_api_present():
    import geostl

    for name in ("GeoPoint", "BoundingBox", "ElevationTile", "Region", "Section", "Grid"):
        assert hasattr(geostl, name), f"missing public export: {name}"


def test_sources_import_and_subclass():
    from geostl.sources import (
        AustriaDGMSource,
        ElevationSource,
        LocalGeoTiffSource,
        OpenTopographySource,
        RemoteCOGSource,
    )

    for cls in (LocalGeoTiffSource, RemoteCOGSource, OpenTopographySource, AustriaDGMSource):
        assert issubclass(cls, ElevationSource)
