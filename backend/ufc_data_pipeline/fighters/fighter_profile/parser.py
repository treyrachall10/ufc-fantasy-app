"""
Pure HTML parsing for UFC Stats fighter profile pages.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from bs4 import BeautifulSoup


@dataclass
class FighterProfileData:
    """Parsed fighter metadata from a UFC Stats profile page."""

    first_name: str | None = None
    last_name: str | None = None
    full_name: str | None = None
    nick_name: str | None = None
    height: int | None = None
    weight: int | None = None
    reach: int | None = None
    stance: str | None = None
    dob: date | None = None


def convert_height_to_inches(value: str | None) -> int | None:
    """
    Convert a height string like ``5' 7"`` to total inches.
    Receives a height string and returns total inches or None.
    """
    if not isinstance(value, str) or not value.strip() or value.strip() == "--":
        return None
    stripped_str = value.replace("'", "").replace('"', "").strip()
    parts = stripped_str.split()
    if len(parts) < 2:
        return None
    feet = int(parts[0])
    inches = int(parts[1])
    return (feet * 12) + inches


def convert_weight_to_lbs(value: str | None) -> int | None:
    """
    Convert a weight string like ``145 lbs.`` to integer pounds.
    Receives a weight string and returns pounds or None.
    """
    if not isinstance(value, str) or not value.strip() or value.strip() == "--":
        return None
    return int(value.split()[0])


def convert_reach_to_inches(value: str | None) -> int | None:
    """
    Convert a reach string like ``72"`` to integer inches.
    Receives a reach string and returns inches or None.
    """
    if not isinstance(value, str) or not value.strip() or value.strip() == "--":
        return None
    return int(value.replace('"', "").strip())


def convert_dob(value: str | None) -> date | None:
    """
    Convert a DOB string like ``Jan 01, 1990`` to a date.
    Receives a DOB string and returns a date or None.
    """
    if not isinstance(value, str) or not value.strip() or value.strip() == "--":
        return None
    return datetime.strptime(value.strip(), "%b %d, %Y").date()


def parse_fighter_profile(soup: BeautifulSoup) -> FighterProfileData:
    """
    Parse fighter metadata from a UFC Stats profile page soup.
    Receives a BeautifulSoup object and returns FighterProfileData.
    """
    profile = FighterProfileData()

    title_el = soup.find("span", class_="b-content__title-highlight")
    if title_el is not None:
        profile.full_name = title_el.get_text(strip=True) or None

    if profile.full_name:
        name_parts = profile.full_name.split()
        profile.first_name = name_parts[0]
        profile.last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else None

    nick_el = soup.find(class_="b-content__Nickname")
    if nick_el is not None:
        nick = nick_el.get_text(strip=True)
        profile.nick_name = nick or None

    tott_lists = soup.find_all("ul", class_="b-list__box-list")
    if tott_lists:
        tott = tott_lists[0]
        labeled_values: dict[str, str] = {}
        # Loop through each label/value pair in the tale-of-the-tape list.
        for tag in tott.find_all("i"):
            raw = (tag.text or "") + (tag.next_sibling or "")
            cleaned = raw.replace("\n", "").replace("  ", "").strip()
            if ":" in cleaned:
                label, value = cleaned.split(":", 1)
                labeled_values[label.strip().lower()] = value.strip()

        profile.height = convert_height_to_inches(labeled_values.get("height"))
        profile.weight = convert_weight_to_lbs(labeled_values.get("weight"))
        profile.reach = convert_reach_to_inches(labeled_values.get("reach"))
        stance = labeled_values.get("stance")
        profile.stance = stance if stance and stance != "--" else None
        profile.dob = convert_dob(labeled_values.get("dob"))

    return profile


def profile_data_to_api_payload(profile: FighterProfileData) -> dict:
    """
    Convert FighterProfileData into a JSON-serializable API payload.
    Receives FighterProfileData and returns a dict for the SetFighterProfile endpoint.
    """
    payload: dict = {}
    for field in (
        "first_name",
        "last_name",
        "full_name",
        "nick_name",
        "stance",
        "weight",
        "height",
        "reach",
    ):
        value = getattr(profile, field)
        if value is not None:
            payload[field] = value
    if profile.dob is not None:
        payload["dob"] = profile.dob.isoformat()
    return payload
