"""Approximate geographic distance from Prague, used to rank opportunities."""
from __future__ import annotations

import math
import unicodedata

PRAGUE = (50.0755, 14.4378)

# lat, lon for cities seen in collected opportunities. Keys are normalized
# (lowercase, diacritics stripped, no trailing state/country abbreviation).
CITY_COORDS: dict[str, tuple[float, float]] = {
    "aachen": (50.7753, 6.0839),
    "aalborg": (57.0488, 9.9217),
    "amsterdam": (52.3676, 4.9041),
    "antwerp": (51.2194, 4.4025),
    "augsburg": (48.3705, 10.8978),
    "bamberg": (49.8988, 10.9028),
    "berlin": (52.5200, 13.4050),
    "birmingham": (33.5207, -86.8025),  # Alabama, US
    "bochum": (51.4818, 7.2162),
    "bonn": (50.7374, 7.0982),
    "bratislava": (48.1486, 17.1077),
    "braunschweig": (52.2689, 10.5268),
    "brno": (49.1951, 16.6068),
    "brussels": (50.8503, 4.3517),
    "cannes": (43.5528, 7.0174),
    "chemnitz": (50.8278, 12.9214),
    "copenhagen": (55.6761, 12.5683),
    "davenport": (41.5236, -90.5776),
    "den haag": (52.0705, 4.3007),
    "dortmund": (51.5136, 7.4653),
    "enschede": (52.2215, 6.8937),
    "erfurt": (50.9848, 11.0299),
    "essen": (51.4556, 7.0116),
    "evansville": (37.9716, -87.5711),
    "faro": (37.0194, -7.9304),
    "gera": (50.8797, 12.0817),
    "glasgow": (55.8642, -4.2518),
    "gothenburg": (57.7089, 11.9746),
    "goteborg": (57.7089, 11.9746),
    "guiyang": (26.6470, 106.6302),
    "gyor": (47.6875, 17.6504),
    "gorlitz": (51.1531, 14.9857),
    "gottingen": (51.5413, 9.9158),
    "hamburg": (53.5511, 9.9937),
    "hannover": (52.3759, 9.7320),
    "heilbronn": (49.1427, 9.2109),
    "helena": (46.5891, -112.0391),
    "herford": (52.1149, 8.6733),
    "hildesheim": (52.1508, 9.9511),
    "hilversum": (52.2242, 5.1758),
    "hof": (50.3138, 11.9166),
    "kaiserslautern": (49.4432, 7.7702),
    "karlsruhe": (49.0069, 8.4037),
    "kiel": (54.3233, 10.1228),
    "kosice": (48.7164, 21.2611),
    "kristiansand": (58.1467, 7.9956),
    "kuopio": (62.8980, 27.6782),
    "kobenhavn": (55.6761, 12.5683),
    "las palmas de gran canaria": (28.1235, -15.4363),
    "liege": (50.6326, 5.5797),
    "liepaja": (56.5046, 21.0111),
    "lincoln": (40.8136, -96.7026),
    "lisbon": (38.7223, -9.1393),
    "ljubljana": (46.0569, 14.5058),
    "ludwigshafen": (49.4741, 8.4356),
    "magdeburg": (52.1205, 11.6276),
    "manchester": (53.4808, -2.2426),
    "mannheim": (49.4875, 8.4660),
    "marianske lazne": (49.9636, 12.7069),
    "milano": (45.4642, 9.1900),
    "munchen": (48.1351, 11.5820),
    "mnichov": (48.1351, 11.5820),
    "montpellier": (43.6108, 3.8767),
    "mulhouse": (47.7508, 7.3359),
    "norfolk": (36.8508, -76.2859),
    "norimberk": (49.4521, 11.0767),
    "nurnberg": (49.4521, 11.0767),
    "odense": (55.4038, 10.4024),
    "omaha": (41.2565, -95.9345),
    "paris": (48.8566, 2.3522),
    "perth": (-31.9505, 115.8605),
    "pittsburgh": (40.4406, -79.9959),
    "plzen": (49.7384, 13.3736),
    "regensburg": (49.0134, 12.1016),
    "rennes": (48.1173, -1.6778),
    "reutlingen": (48.4919, 9.2043),
    "reykjavik": (64.1466, -21.9426),
    "roma": (41.9028, 12.4964),
    "shenzhen": (22.5431, 114.0579),
    "sioux city": (42.4999, -96.4003),
    "spokane": (47.6588, -117.4260),
    "st. louis": (38.6270, -90.1994),
    "stavanger": (58.9700, 5.7331),
    "stockholm": (59.3293, 18.0686),
    "strasbourg": (48.5734, 7.7521),
    "stuttgart": (48.7758, 9.1829),
    "sydney": (-33.8688, 151.2093),
    "tallinn": (59.4370, 24.7536),
    "teplice": (50.6404, 13.8245),
    "toulouse": (43.6047, 1.4442),
    "umea": (63.8258, 20.2630),
    "vymar": (50.9795, 11.3235),
    "weimar": (50.9795, 11.3235),
    "warsaw": (52.2297, 21.0122),
    "warszawa": (52.2297, 21.0122),
    "wroclaw": (51.1079, 17.0385),
    "wuppertal": (51.2562, 7.1508),
    "zlin": (49.2265, 17.6683),
    "zurich": (47.3769, 8.5417),
    "le bourget du lac": (45.6486, 5.8564),
    "prague": (50.0755, 14.4378),
    "praha": (50.0755, 14.4378),
    "ceske budejovice": (48.9744, 14.4744),
    "karlovy vary": (50.2311, 12.8718),
    "olomouc": (49.5938, 17.2509),
    "pardubice": (50.0343, 15.7812),
}

_EXTRA_REPLACEMENTS = {"ø": "o", "æ": "ae", "å": "a", "ł": "l"}


def _normalize(city: str) -> str:
    city = city.split(",")[0].strip().lower()
    for src, dst in _EXTRA_REPLACEMENTS.items():
        city = city.replace(src, dst)
    return "".join(
        c for c in unicodedata.normalize("NFKD", city) if not unicodedata.combining(c)
    )


def distance_from_prague_km(city: str) -> float | None:
    """Approximate great-circle distance from Prague to `city`, or None if unknown."""
    if not city:
        return None
    coords = CITY_COORDS.get(_normalize(city))
    if coords is None:
        return None
    lat1, lon1 = math.radians(PRAGUE[0]), math.radians(PRAGUE[1])
    lat2, lon2 = math.radians(coords[0]), math.radians(coords[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    return 6371.0 * 2 * math.asin(math.sqrt(a))
