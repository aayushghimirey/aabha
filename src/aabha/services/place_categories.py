"""Turning what someone says out loud into a Geoapify place category.

"Find me a mobile shop" is not a place name, and looking it up in a geocoder
answers with whatever is called that anywhere on earth - which is how a shop
1,200km away once came back as the nearest one. A category search asks the
right question instead: what sorts of place are these, and which are near.

Every category here has been checked against the live Places API. Geoapify's
own spelling wins where it differs from ours - "elektronics" is theirs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Words people wrap a request in that say nothing about what they want. They
# come off before the phrase is matched, so "find me a pharmacy near here"
# and "pharmacy" land in the same place.
_FILLER = frozenset(
    {
        "a",
        "an",
        "the",
        "any",
        "some",
        "find",
        "show",
        "get",
        "me",
        "my",
        "for",
        "is",
        "are",
        "there",
        "please",
        "nearby",
        "near",
        "nearest",
        "closest",
        "close",
        "around",
        "here",
        "by",
        "local",
        "good",
        "best",
        "cheap",
        "open",
        "to",
        "in",
        "at",
        "of",
        "area",
        "this",
        "us",
        "i",
        "want",
        "need",
        "looking",
        "look",
        "somewhere",
        "something",
        "anywhere",
    }
)

# Plurals that do not come off with a trailing "s".
_IRREGULAR = {
    "pharmacies": "pharmacy",
    "bakeries": "bakery",
    "groceries": "grocery",
    "libraries": "library",
    "agencies": "agency",
    "eateries": "eatery",
    "clinics": "clinic",
    "churches": "church",
    "mosques": "mosque",
    "buses": "bus",
    "dentists": "dentist",
    "places": "place",
}


@dataclass(frozen=True)
class PlaceCategory:
    """A kind of place worth searching for, in the API's terms and in ours."""

    # Comma-separated Geoapify categories, sent as the `categories` parameter.
    categories: str

    # What to call it when speaking - "mobile phone shop", not
    # "commercial.elektronics".
    label: str

    # The OpenStreetMap tag values that are actually what was asked for.
    # Geoapify's categories are broad - a phone shop, a printer repair desk
    # and a fridge showroom all sit under `commercial.elektronics` - so these
    # say which of them to put first. Empty means the category is tight
    # enough that everything in it counts.
    prefers: tuple[str, ...] = ()


def _c(categories: str, label: str, *prefers: str) -> PlaceCategory:
    return PlaceCategory(categories=categories, label=label, prefers=prefers)


# Phrase -> category. Keys are singular and lowercase; plurals are handled by
# the matcher, so add "mobile shop" and never "mobile shops".
_PHRASES: dict[str, PlaceCategory] = {}


def _add(category: PlaceCategory, *phrases: str) -> None:
    for phrase in phrases:
        _PHRASES[phrase] = category


_electronics = _c("commercial.elektronics", "electronics shop", "electronics")
_add(
    _c("commercial.elektronics", "mobile phone shop", "mobile_phone"),
    "mobile shop",
    "mobile store",
    "mobile phone shop",
    "mobile phone store",
    "phone shop",
    "phone store",
    "cell phone shop",
    "cellphone shop",
    "mobile repair shop",
    "phone repair shop",
    "mobile",
    "iphone shop",
    "iphone store",
    "iphone",
    "samsung shop",
    "android phone shop",
    "smartphone shop",
)
_add(_electronics, "electronics shop", "electronic shop", "electronics store", "electronics")
_add(_c("commercial.elektronics", "computer shop", "computer"), "computer shop", "computer store", "laptop shop")

_add(_c("healthcare.pharmacy", "pharmacy"), "pharmacy", "chemist", "drugstore", "drug store", "medical shop", "medical store", "medicine shop", "medical")
_add(_c("healthcare.hospital", "hospital"), "hospital")
_add(_c("healthcare.clinic_or_praxis", "clinic"), "clinic", "health post", "doctor", "health centre", "health center")
_add(_c("healthcare.dentist", "dentist"), "dentist", "dental clinic", "dental")

_add(_c("service.financial.atm", "ATM"), "atm", "cash machine", "cashpoint", "cash point")
_add(_c("service.financial.bank", "bank"), "bank")

_add(_c("service.vehicle.fuel", "petrol station"), "petrol pump", "petrol station", "gas station", "fuel station", "filling station", "petrol", "fuel", "pump")
_add(_c("service.vehicle.charging_station", "charging station"), "charging station", "ev charger", "ev charging station", "charger")
_add(_c("service.vehicle.repair", "repair workshop"), "mechanic", "garage", "car repair shop", "bike repair shop", "motorcycle repair shop", "workshop", "repair shop")
_add(_c("service.vehicle.car_wash", "car wash"), "car wash", "carwash")

_add(_c("catering.restaurant", "restaurant"), "restaurant", "place to eat", "somewhere to eat", "eatery", "diner", "khaja ghar", "food", "eat", "somewhere eat", "food place")
_add(_c("catering.cafe", "cafe"), "cafe", "coffee shop", "coffee", "coffee place", "tea shop")
_add(_c("catering.fast_food", "fast food place"), "fast food", "fast food place", "burger place", "pizza place", "momo shop")
_add(_c("catering.bar,catering.pub", "bar"), "bar", "pub")
_add(_c("catering.ice_cream", "ice cream shop"), "ice cream shop", "ice cream")

_add(_c("commercial.supermarket,commercial.department_store", "supermarket"), "supermarket", "grocery store", "grocery shop", "grocery", "kirana", "kirana pasal", "department store")
_add(_c("commercial.marketplace", "market"), "market", "marketplace", "bazaar", "bazar")
_add(_c("commercial.food_and_drink.bakery", "bakery"), "bakery", "cake shop", "cake")
_add(_c("commercial.shopping_mall", "shopping mall"), "mall", "shopping mall", "shopping centre", "shopping center")
_add(_c("commercial.clothing", "clothes shop"), "clothing store", "clothes shop", "clothes store", "clothes", "garment shop", "boutique", "shoe shop")
_add(_c("commercial.houseware_and_hardware", "hardware shop"), "hardware shop", "hardware store", "hardware")
_add(_c("commercial.books", "book shop"), "book shop", "bookshop", "book store", "bookstore", "stationery shop", "stationery")
_add(_c("commercial.gas", "gas shop"), "gas shop", "gas cylinder shop", "lpg", "cooking gas")
_add(_c("commercial.pet", "pet shop"), "pet shop", "pet store")
_add(_c("commercial.florist", "florist"), "florist", "flower shop")
_add(_c("commercial.toy_and_game", "toy shop"), "toy shop", "toy store")
_add(_c("commercial.gift_and_souvenir", "gift shop"), "gift shop", "souvenir shop")
_add(_c("commercial.outdoor_and_sport", "sports shop"), "sports shop", "sport shop", "sporting goods shop")
_add(_c("commercial.garden", "garden centre"), "nursery", "garden centre", "garden center", "plant shop")
_add(_c("commercial.newsagent", "newsagent"), "newsagent", "newspaper shop")
_add(_c("commercial.baby_goods", "baby shop"), "baby shop", "baby store")
_add(_c("commercial.second_hand", "second hand shop"), "second hand shop", "thrift store", "used shop")

_add(_c("accommodation.hotel", "hotel"), "hotel", "place to stay", "somewhere to stay", "lodge", "guest house", "guesthouse")
_add(_c("service.police", "police station"), "police", "police station", "police post")
_add(_c("service.post", "post office"), "post office", "postal office")
_add(_c("service.cleaning.laundry,service.cleaning.dry_cleaning", "laundry"), "laundry", "dry cleaner", "dry cleaning", "laundromat")
_add(_c("service.beauty", "salon"), "salon", "beauty parlour", "beauty parlor", "beauty salon", "spa")
_add(_c("service.beauty.hairdresser", "barber"), "barber", "barber shop", "hairdresser", "hair salon", "haircut")
_add(_c("service.travel_agency", "travel agency"), "travel agency", "ticket counter", "travel agent")

_add(_c("education.school", "school"), "school", "college")
_add(_c("education.library", "library"), "library")

_add(_c("public_transport.bus", "bus stop"), "bus stop", "bus station", "bus park", "bus stand")
_add(_c("public_transport.train", "train station"), "train station", "railway station")
_add(_c("airport", "airport"), "airport")
_add(_c("parking", "car park"), "parking", "car park", "parking lot")

_add(_c("leisure.park", "park"), "park", "playground")
_add(_c("sport.fitness", "gym"), "gym", "fitness centre", "fitness center")
_add(_c("religion.place_of_worship", "place of worship"), "temple", "mandir", "church", "mosque", "monastery", "gumba", "place of worship")
_add(_c("tourism.attraction", "attraction"), "tourist attraction", "attraction", "sightseeing", "things to see")

_add(_c("entertainment.cinema", "cinema"), "cinema", "movie theater", "movie theatre", "movie hall", "movie", "film hall", "picture hall", "multiplex", "movie place", "watch movie", "theater", "theatre")
_add(_c("entertainment.culture.theatre", "playhouse"), "playhouse", "drama theatre", "stage theatre")
_add(_c("entertainment.museum", "museum"), "museum", "art gallery", "gallery")
_add(_c("entertainment.bowling_alley", "bowling alley"), "bowling alley", "bowling")
_add(_c("entertainment.amusement_arcade", "arcade"), "arcade", "amusement arcade", "game centre", "game center", "gaming centre")
_add(_c("entertainment.activity_park", "activity park"), "activity park", "amusement park", "theme park", "water park", "fun park")
_add(_c("entertainment.zoo", "zoo"), "zoo")
_add(_c("entertainment.aquarium", "aquarium"), "aquarium")
_add(_c("entertainment.escape_game", "escape room"), "escape room", "escape game")
_add(_c("entertainment", "something to do"), "entertainment", "somewhere to go out", "night out", "fun")


# Words that say the user means somewhere close by. They are filler as far as
# matching goes, but the fact that one was said is worth keeping.
_NEARBY = frozenset(
    {"near", "nearby", "nearest", "closest", "close", "around", "here"}
)

# Words that make a request out of a phrase. "Pokhara Pharmacy" is the name
# over a door; "find me a pharmacy" is somebody asking for one, and only the
# second should be read as a kind of place when the words around it do not
# quite line up.
_REQUEST = frozenset(
    {
        "find",
        "search",
        "show",
        "suggest",
        "recommend",
        "want",
        "need",
        "looking",
        "look",
        "watch",
        "get",
        "help",
        "hepl",
        "any",
        "is",
        "are",
        "there",
        "i",
        "me",
        "my",
        "please",
        "somewhere",
        "something",
        "anywhere",
        "buy",
        "go",
        "visit",
    }
)


def resolve(query: str, nearby_hint: bool = False) -> PlaceCategory | None:
    """The kind of place `query` describes, or None if it names one instead.

    Returns a category when the whole request - once "find me a" and "near
    here" come off - is a kind of place. "mobile shops near me" is a category;
    "Ananya Mobile & Electronics" and "the German bakery in Jhamsikhel" are
    places, and belong in the geocoder.

    When the user has said they mean somewhere nearby, the kind of place is
    also looked for inside a longer sentence, because a request that arrives
    as "hepl me to find near by mobile shops" is still a request for a mobile
    shop. That is only done with a nearby signal to lean on: without one,
    "Pokhara Pharmacy" is a place someone named, not a search for a chemist.
    """
    spoken = re.findall(r"[a-z]+", query.lower())
    words = [word for word in spoken if word not in _FILLER]

    if not words:
        return None

    for candidate in _variants(words):
        category = _PHRASES.get(candidate)

        if category is not None:
            return category

    # Nothing matched end to end. That is normal for anything spoken loosely -
    # "search for moive theaters" carries a typo, "i want to watch a movie
    # tonight" carries a plan - so the kind of place is looked for inside the
    # sentence. Only for something that reads as a request, though: a bare
    # "Pokhara Pharmacy" is a name over a door, and belongs to the geocoder.
    if (
        nearby_hint
        or not _NEARBY.isdisjoint(spoken)
        or not _REQUEST.isdisjoint(spoken)
    ):
        return _within(words)

    return None


def _within(words: list[str]) -> PlaceCategory | None:
    """The kind of place named somewhere inside a longer request.

    Longest run of words first, so "mobile shop" wins over the "mobile" that
    sits inside it and the answer stays the more specific one.
    """
    for size in range(len(words), 0, -1):
        for start in range(len(words) - size + 1):
            run = words[start : start + size]

            for candidate in _variants(run):
                category = _PHRASES.get(candidate)

                if category is not None:
                    return category

    return None


def _variants(words: list[str]) -> list[str]:
    """The phrasings to try, most literal first.

    People say "mobile shops"; the table stores "mobile shop". Rather than
    listing every plural, the spoken form is walked back to the singular -
    first the last word alone, which covers "mobile shops", then every word,
    which covers "medical stores".
    """
    joined = " ".join(words)

    last = words[:-1] + [_singular(words[-1])]
    every = [_singular(word) for word in words]

    # A bare "shop" or "store" left over from "mobile phone shops" says
    # nothing on its own, but "phone" does.
    trimmed = [word for word in every if word not in ("shop", "store", "place")]

    variants = [joined, " ".join(last), " ".join(every)]

    if trimmed and trimmed != every:
        variants.append(" ".join(trimmed))

    # dict.fromkeys keeps the order while dropping the repeats a
    # single-word query produces.
    return list(dict.fromkeys(variants))


def _singular(word: str) -> str:
    if word in _IRREGULAR:
        return _IRREGULAR[word]

    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"

    # "gas" and "bus" are not plurals; "ss" endings never are.
    if word.endswith("s") and not word.endswith(("ss", "us", "as", "is")):
        return word[:-1]

    return word
