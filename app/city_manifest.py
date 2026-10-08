from __future__ import annotations

from dataclasses import dataclass
from types import ModuleType

from app.data import (
    arkhangelsk,
    chelyabinsk,
    irkutsk,
    kaliningrad,
    kazan,
    khabarovsk,
    krasnodar,
    krasnoyarsk,
    moscow,
    murmansk,
    nizhny_novgorod,
    novosibirsk,
    omsk,
    perm,
    pskov,
    rostov_on_don,
    samara,
    saratov,
    sochi,
    spb,
    tomsk,
    tula,
    tyumen,
    ufa,
    veliky_novgorod,
    vladimir,
    vladivostok,
    volgograd,
    vologda,
    voronezh,
    yaroslavl,
    yekaterinburg,
)
from app.domain import Place, RoutePlan


@dataclass(frozen=True, slots=True)
class CatalogQualityProfile:
    min_places: int
    min_routes: int
    min_districts: int
    min_categories: int
    min_free_places: int
    min_family_places: int
    min_museums: int


@dataclass(frozen=True, slots=True)
class CityManifest:
    slug: str
    name: str
    category_labels: dict[str, str]
    places: tuple[Place, ...]
    routes: tuple[RoutePlan, ...]
    quality: CatalogQualityProfile


def _city(module: ModuleType, quality: CatalogQualityProfile) -> CityManifest:
    return CityManifest(
        slug=module.CITY_SLUG,
        name=module.CITY_NAME,
        category_labels=module.CATEGORY_LABELS,
        places=module.PLACES,
        routes=module.ROUTES,
        quality=quality,
    )


CITY_MANIFESTS = (
    _city(arkhangelsk, CatalogQualityProfile(30, 9, 10, 5, 16, 16, 10)),
    _city(chelyabinsk, CatalogQualityProfile(22, 7, 9, 5, 14, 19, 5)),
    _city(irkutsk, CatalogQualityProfile(23, 7, 10, 5, 12, 14, 9)),
    _city(khabarovsk, CatalogQualityProfile(28, 9, 10, 5, 18, 18, 6)),
    _city(kaliningrad, CatalogQualityProfile(30, 12, 10, 5, 13, 9, 10)),
    _city(kazan, CatalogQualityProfile(28, 10, 9, 5, 18, 10, 8)),
    _city(krasnodar, CatalogQualityProfile(22, 7, 8, 5, 17, 13, 4)),
    _city(krasnoyarsk, CatalogQualityProfile(21, 7, 9, 5, 13, 10, 6)),
    _city(moscow, CatalogQualityProfile(18, 8, 8, 4, 8, 5, 3)),
    _city(murmansk, CatalogQualityProfile(34, 10, 12, 5, 19, 20, 8)),
    _city(nizhny_novgorod, CatalogQualityProfile(31, 13, 10, 5, 15, 10, 10)),
    _city(novosibirsk, CatalogQualityProfile(33, 13, 12, 5, 18, 15, 9)),
    _city(omsk, CatalogQualityProfile(21, 7, 10, 5, 16, 15, 4)),
    _city(perm, CatalogQualityProfile(19, 7, 5, 5, 8, 5, 6)),
    _city(pskov, CatalogQualityProfile(35, 9, 9, 5, 21, 14, 8)),
    _city(rostov_on_don, CatalogQualityProfile(22, 7, 10, 5, 14, 12, 6)),
    _city(spb, CatalogQualityProfile(20, 6, 5, 4, 7, 4, 7)),
    _city(samara, CatalogQualityProfile(19, 7, 7, 5, 12, 9, 6)),
    _city(saratov, CatalogQualityProfile(25, 8, 10, 5, 16, 12, 7)),
    _city(sochi, CatalogQualityProfile(34, 12, 10, 5, 15, 12, 9)),
    _city(tomsk, CatalogQualityProfile(23, 7, 10, 5, 15, 13, 6)),
    _city(tula, CatalogQualityProfile(28, 8, 10, 5, 16, 13, 10)),
    _city(tyumen, CatalogQualityProfile(22, 7, 10, 5, 17, 16, 5)),
    _city(ufa, CatalogQualityProfile(20, 7, 8, 5, 12, 10, 5)),
    _city(veliky_novgorod, CatalogQualityProfile(30, 9, 9, 5, 16, 14, 10)),
    _city(vladimir, CatalogQualityProfile(30, 9, 10, 5, 16, 15, 10)),
    _city(vladivostok, CatalogQualityProfile(18, 7, 6, 5, 10, 6, 5)),
    _city(volgograd, CatalogQualityProfile(19, 7, 5, 5, 12, 8, 5)),
    _city(vologda, CatalogQualityProfile(33, 10, 10, 5, 19, 19, 10)),
    _city(voronezh, CatalogQualityProfile(23, 7, 9, 5, 16, 15, 6)),
    _city(yaroslavl, CatalogQualityProfile(28, 10, 10, 5, 13, 10, 8)),
    _city(yekaterinburg, CatalogQualityProfile(15, 7, 4, 5, 7, 2, 5)),
)


def list_city_manifests() -> tuple[CityManifest, ...]:
    return CITY_MANIFESTS
