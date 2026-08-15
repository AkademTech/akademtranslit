"""Worked examples. Run with: python examples/basic_usage.py"""

from akademtranslit import (
    CYRILLIC,
    LATIN_1995,
    LATIN_2026,
    convert,
    detect_script,
    normalize,
    to_cyrillic,
    to_latin,
)


def transliterating_a_title() -> None:
    """A journal article title, as it would arrive from an older archive."""
    title = "Ўзбекистонда илмий тадқиқот тизимини ривожлантириш"

    print("Cyrillic   :", title)
    print("latin_1995 :", to_latin(title, variant=LATIN_1995))
    print("latin_2026 :", to_latin(title, variant=LATIN_2026))


def migrating_an_existing_corpus() -> None:
    """The 1995 -> 2026 upgrade. Lossless in both directions."""
    records = [
        "Toshkent davlat universiteti",
        "Mirzo Ulugʻbek nomidagi Oʻzbekiston Milliy universiteti",
        "Qashqadaryo viloyati",
    ]

    for old in records:
        new = convert(old, source=LATIN_1995, target=LATIN_2026)
        restored = convert(new, source=LATIN_2026, target=LATIN_1995)
        print(f"{old}\n  -> {new}\n  -> {restored}  (lossless: {restored == old})")


def building_a_search_index() -> None:
    """The point of normalize(): one key for every spelling of one name."""
    index: dict[str, list[str]] = {}

    for record in [
        "Şoşimova N.",        # a record entered under the 2026 alphabet
        "Shoshimova N.",      # the same author under the 1995 alphabet
        "Шошимова Н.",        # and again from a Cyrillic-era archive
        "Gʻafurov A.",
        "Ğafurov A.",
    ]:
        index.setdefault(normalize(record), []).append(record)

    for key, records in index.items():
        print(f"{key!r}\n  {records}")


def detecting_what_you_were_handed() -> None:
    """Untagged text from a mixed corpus."""
    for text in ["Самарқанд", "Samarqand", "Toşkent", "Uluğbek"]:
        print(f"{text:12} -> {detect_script(text)}")

    # Detection is a heuristic. When the orthography is known from context --
    # a document's metadata, a database column -- pass it explicitly, because
    # a 2026 string with none of the four reformed letters looks exactly like
    # a 1995 one.
    print("\nWhy explicit source matters:")
    print("  auto  :", to_cyrillic("Ishoq"))
    print("  2026  :", convert("Ishoq", source=LATIN_2026, target=CYRILLIC))


if __name__ == "__main__":
    for section in (
        transliterating_a_title,
        migrating_an_existing_corpus,
        building_a_search_index,
        detecting_what_you_were_handed,
    ):
        print(f"\n=== {section.__name__.replace('_', ' ')} ===")
        section()
