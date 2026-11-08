"""Lao to IPA (and other systems) transliteration utilities.

This module implements a rule-based pipeline that tokenizes Lao text,
groups characters into syllables, applies tone-placement heuristics,
and produces IPA (or alternative) transliterations using lookup
tables. It is intentionally conservative (no external models) and
follows conventions used in language reference materials with Vientiane tones.

Public functions:
 - `transliterate`: top-level pipeline for transliteration

Classes:
 - `Syllable`: represents an assembled Lao syllable (vowel, initials, finals, tone)

The implementation relies on several tables: `lao_consonant_assignments`,
`lao_vowel_assignments`, and helper sets for vowel/tone characters.
"""

# TODO: Type annotations, handle Lao abbreviations


# Final consonants that make a syllable checked/dead for tone assignment.
lao_dead_finals = {"ກ", "ຂ", "ຄ", "ດ", "ຕ", "ຖ", "ທ", "ບ", "ປ", "ພ", "ຟ", "ຝ"}
# Consonants that can close a Lao syllable.
lao_final_consonants = lao_dead_finals | {
    "ງ", "ຈ", "ຊ", "ຍ", "ສ", "ມ", "ນ", "ຣ", "ລ", "ວ"
}
# Maximum number of tokens to scan when placing a tone marker.
lao_tone_lookahead_limit = 7


class _LaoToken(str):
    """String token that remembers the source range it came from.

    The pipeline merges and reorders characters while assembling syllables.
    Carrying the original start/end offsets lets us map a finished
    `Syllable` back to the exact substring it represents.
    """

    def __new__(cls, value, start=0, end=None):
        obj = super().__new__(cls, value)
        obj.start = start
        obj.end = start + len(value) if end is None else end
        return obj

    def __add__(self, other):
        if isinstance(other, _LaoToken):
            return _LaoToken(str(self) + str(other), self.start, other.end)
        return _LaoToken(str(self) + str(other), self.start, self.end + len(other))

    def __radd__(self, other):
        return _LaoToken(str(other) + str(self), self.start, self.end)


def _replace_span(value, first, second):
    """Build a merged token spanning two source tokens when both are tracked."""
    if isinstance(first, _LaoToken) and isinstance(second, _LaoToken):
        return _LaoToken(value, first.start, second.end)
    return value


class Syllable:
    """Representation of a Lao syllable composed from orthographic parts.

    A `Syllable` stores the vowel token, optional initial and final
    consonant tokens, and an optional tone marker. It provides helpers to
    compute the syllable's tone contour and to render the syllable into
    a target transliteration system (e.g. IPA).

    Attributes:
        vowel (str): Vowel token for the syllable.
        initial_consonant (Optional[str]): Initial consonant or cluster.
        final_consonant (Optional[str]): Final consonant if present.
        tone_marker (Optional[str]): Tone marker character if present.
        letter_class (Optional[str]): Computed letter class ('high','middle','low').
        vowel_length (Optional[str]): 'short'|'long' or None.
        dead_syllable (bool): Whether the syllable is phonetically dead, used for tone processing.
    """

    # Vowel tokens that should be treated as "live" (exception to the
    # short->dead syllable rule). These tokens are short-form glyphs
    # orthographically but do not trigger checked/dead-tone behavior.
    LAO_SPECIAL_VOWELS = {"ຳ", "ເົາ", "ໃ", "ໄ", "ເັຽ", "ເັຍ"}

    def __init__(
        self, vowel, initial_consonant=None, final_consonant=None, tone_marker=None
    ):
        """Initialize a Syllable with its orthographic components.

        Args:
            vowel (str): Vowel string (one or more Lao characters) for this syllable.
            initial_consonant (Optional[str]): Initial consonant or cluster.
            final_consonant (Optional[str]): Final consonant.
            tone_marker (Optional[str]): Tone marker if present.

        Returns:
            None
        """
        self.vowel = vowel
        self.initial_consonant = initial_consonant
        self.final_consonant = final_consonant
        self.tone_marker = tone_marker
        self.letter_class = None
        self.vowel_length = Syllable.get_vowel_length(vowel)
        # Treat certain special vowels (am/ao/ai) as live for tone purposes
        self.dead_syllable = self.final_consonant in lao_dead_finals or (
            self.final_consonant is None
            and self.vowel_length == "short"
            and vowel not in Syllable.LAO_SPECIAL_VOWELS
        )

    def __str__(self):
        """Return the IPA transliteration for the syllable.

        Equivalent to `self.get_transliteration('ipa')`.
        """
        return self.get_transliteration("ipa")

    def __repr__(self):
        """Developer-friendly representation to generate the current Syllable object."""
        return f"Syllable(vowel='{self.vowel}', initial_consonant='{self.initial_consonant}', final_consonant='{self.final_consonant}', tone_marker='{self.tone_marker}')"

    # Reference: https://seasite.niu.edu/lao/LaoLanguage/IntroAlphabet/tonemarks/tonechart.htm
    def get_tone(self):
        """Compute the IPA tone contour for this syllable.

        The result uses internal mappings based on the consonant letter
        class (high/middle/low), whether the syllable is "dead" (checked)
        or "live", and any explicit tone marker present. Mapping values
        are expressed as IPA tone contours (e.g. '˧˩').

        Returns:
            str: tone contour string (empty string if none)
        """
        # Tone class is determined by the first initial consonant character
        # (for clusters we consider the first letter; special clusters like
        # 'ຫ' + consonant are handled by the letter_class lookup below).
        first_letter = self.initial_consonant[0] if self.initial_consonant is not None else None
        self.letter_class = Syllable.get_letter_class(first_letter)
        # Recompute dead_syllable taking into account special vowels as live
        self.dead_syllable = self.final_consonant in lao_dead_finals or (
            self.final_consonant is None
            and self.vowel_length == "short"
            and self.vowel not in Syllable.LAO_SPECIAL_VOWELS
        )
        # Tone mappings adjusted to match Wiktionary (Vientiane) IPA contours.
        tone_mapping_thoo = {
            # letter class: tone (for marker "້")
            "high": "˧˩",
            "middle": "˥˨",
            "low": "˥˨",
            None: None,
        }
        tone_mapping_live = {
            # letter class: tone for live (smooth) syllables
            "high": "˩˧",
            "middle": "˩˧",
            "low": "˧˥",
            None: None,
        }
        tone_mapping_dead = {
            # (letter class, vowel length): tone for checked (dead) syllables
            ("high", "long"): "˧˩",
            ("middle", "long"): "˧˩",
            ("low", "long"): "˥˨",
            ("high", "short"): "˧˥",
            ("middle", "short"): "˧˥",
            ("low", "short"): "˧",
        }
        tone = ""
        if self.tone_marker == "໋":
            tone = "˩˧"
        elif self.tone_marker == "໊":
            tone = "˧˥"
        elif self.tone_marker == "່":
            tone = "˧"
        elif self.tone_marker == "້":
            tone = tone_mapping_thoo[self.letter_class]
        elif not self.dead_syllable:
            tone = tone_mapping_live[self.letter_class]
        else:
            tone = (
                tone_mapping_dead[(self.letter_class, self.vowel_length)]
                if self.letter_class is not None and self.vowel_length is not None
                else None
            )
        return tone if tone is not None else ""

    def get_transliteration(self, system):
        """Render the syllable into the requested transliteration system.

        The method consults `lao_consonant_assignments` and
        `lao_vowel_assignments`. For initial/final consonants we prefer
        the explicit initial-form mapping so a single-element context does
        not accidentally use the final-form. If a token is not present in
        the lookup tables we fall back to calling `get_naive_transliteration()` on the
        token, allowing recursive handling of composed strings.

        Args:
            system (str): Output system key. Valid options (currently): `'ipa'`, `'moh'`.
                See the module-level `outputs` mapping for all available keys.

        Returns:
            str: Concatenated transliteration for initial, vowel, final and tone.
        """
        transliterated_list = []
        # Prefer explicit initial-form mapping for initial consonants so we don't
        # accidentally select final-form mapping when get_naive_transliteration() is called
        # with a single-element context.
        if self.initial_consonant is not None:
            # If the initial cluster ends with the semivowel 'ວ' and the
            # vowel is plain 'າ', merge the 'ວ' semivowel into the vowel instead
            # if isinstance(self.initial_consonant, str) and len(self.initial_consonant) > 1 and self.initial_consonant[-1] == 'ວ'  and self.vowel == 'າ':
            #     self.initial_consonant = self.initial_consonant.rstrip('ວ')
            #     self.vowel = 'ວາ'
            try:
                initial_cons_entry = lao_consonant_assignments[self.initial_consonant][outputs[system]]
                transliterated_list.append(initial_cons_entry[0])
            except KeyError:
                transliterated_list.extend(
                    get_naive_transliteration([self.initial_consonant], system)
                )

        # Vowel handling: when using direct table lookup append the string,
        # otherwise extend the get_naive_transliteration() result (a list).
        if self.vowel is not None:
            try:
                vowel_entry = lao_vowel_assignments[self.vowel][outputs[system]]
                transliterated_list.append(vowel_entry)
            except KeyError:
                transliterated_list.extend(get_naive_transliteration([self.vowel], system))

        if self.final_consonant is not None:
            try:
                final_cons_entry = lao_consonant_assignments[self.final_consonant][outputs[system]]
                # Prefer final-form mapping where available; otherwise use initial-form.
                transliterated_list.append(final_cons_entry[1] if final_cons_entry[1] is not None else final_cons_entry[0])
            except KeyError:
                transliterated_list.extend(get_naive_transliteration([self.final_consonant], system))
        transliterated_list.append(self.get_tone())
        return "".join(transliterated_list)

    @staticmethod
    def get_letter_class(letter):
        """Return the letter class ('high', 'middle', 'low') for a Lao consonant.

        Args:
            letter (str): Single Lao consonant character.

        Returns:
            Optional[str]: 'high', 'middle', 'low', or None for unknown.
        """
        if letter in {"ຂ", "ສ", "ຖ", "ຜ", "ຝ", "ຫ", "ໜ", "ໝ"}:
            return "high"
        elif letter in {"ກ", "ຈ", "ດ", "ຕ", "ບ", "ປ", "ຢ", "ອ"}:
            return "middle"
        elif letter in {"ຄ", "ງ", "ຊ", "ຍ", "ທ", "ນ", "ພ", "ຟ", "ມ", "ຣ", "ລ", "ວ", "ຮ"}:
            return "low"
        else:
            return None

    @staticmethod
    def get_vowel_length(vowel):
        """Return vowel length category for a Lao vowel token.

        Args:
            vowel (str): Lao vowel token.

        Returns:
            Optional[str]: 'short', 'long' or None if unknown.
        """
        if vowel in {"ະ", "ັ", "ເະ", "ເັ", "ແະ", "ແັ", "ິ", "ໂະ", "ົ", "ເາະ", "ັອ", "ຸ", "ຶ", "ເິ", "ົວະ", "ເຶອ", "ໃ", "ໄ", "ເົາ", "ເັຽ", "ເັຍ", "ຳ"}:
            return "short"
        elif vowel in {"າ", "ເ", "ແ", "ີ", "ໂ", "ໍ", "ອ", "ູ", "ື", "ເີ", "ເຍ", "ຽ", "ົວ", "ວ", "ວາ", "ເືອ"}:
            return "long"
        else:
            return None


# dictionary of Lao consonants and assignments (IPA, MoH2020).
# https://laoconverter.info/moh2020.html
lao_consonant_assignments = {
    # cons: [ipa sound list [beginning sound, final sound], ... other sound lists in same format]
    "ບ": [["b", "p"], ["b", "p"]],
    "ດ": [["d", "t"], ["d", "t"]],
    "ຝ": [["f", None], ["f", None]],
    "ຟ": [["f", None], ["f", None]],
    "ຫ": [["h", None], ["h", None]],
    "ຮ": [["h", None], ["h", None]],
    "ຢ": [["j", None], ["y", None]],
    "ກ": [["k", None], ["k", None]],
    "ຂ": [["kʰ", None], ["kh", None]],
    "ຄ": [["kʰ", None], ["kh", None]],
    "ລ": [["l", "n"], ["l", None]],
    "ຫຼ": [["l", None], ["l", None]],
    "ຫລ": [["l", None], ["l", None]],
    "ມ": [["m", None], ["m", None]],
    "ຫມ": [["m", None], ["m", None]],
    "ໝ": [["m", None], ["m", None]],
    "ນ": [["n", None], ["n", None]],
    "ຫນ": [["n", None], ["n", None]],
    "ໜ": [["n", None], ["n", None]],
    "ງ": [["ŋ", None], ["ng", None]],
    "ຫງ": [["ŋ", None], ["ng", None]],
    "ຍ": [["ɲ", "j"], ["ny", "y"]],
    "ຫຍ": [["ɲ", None], ["ny", None]],
    "ປ": [["p", None], ["p", None]],
    "ຜ": [["pʰ", None], ["ph", None]],
    "ພ": [["pʰ", None], ["ph", None]],
    "ຣ": [["l", "n"], ["r", None]],
    "ຫຣ": [["l", None], ["r", None]],
    "ສ": [["s", None], ["s", None]],
    "ຊ": [["s", None], ["x", None]],
    "ຕ": [["t", None], ["t", None]],
    "ຖ": [["tʰ", "t"], ["th", None]],
    "ທ": [["tʰ", None], ["th", None]],
    "ຈ": [["tɕ", None], ["ch", None]],
    "ວ": [["ʋ", "w"], ["v", "o"]],
    "ຫວ": [["ʋ", None], ["v", None]],
    "ອ": [["", None], ["", None]],
    "ຼ": [["l", None], ["l", None]],
    "ຄຣ": [["kʰl", None], ["khr", None]],
    "ຄລ": [["kʰl", None], ["khl", None]],
    "ຄວ": [["kʷʰ", None], ["khv", None]],
    "ຖວ": [["taʋ", None], ["thv", None]],
    "ຟຣ": [["fl", None], ["fr", None]],
    "ຟຼ": [["fl", None], ["fl", None]],
    "ຝຣ": [["fal", None], ["fr", None]],
    "ຝຮ": [["fal", None], ["fr", None]],
    "ຝຼ": [["fal", None], ["fl", None]],
    "ພຣ": [["pʰl", None], ["phr", None]],
    "ພລ": [["pʰl", None], ["phl", None]],
    "ພຼ": [["pʰl", None], ["phl", None]],
    "ຂວ": [["kʷʰ", None], ["khv", None]],
    "ກວ": [["kʷ", None], ["kv", None]],
    "ກຣ": [["kl", None], ["kr", None]],
    # 'ກຮ': [['kr', None], ['kr', None]],
    "ກຼ": [["kl", None], ["kl", None]],
    "ຄຼ": [["kʰl", None], ["khl", None]],
    "ປຼ": [["pl", None], ["pl", None]],
    "ປຣ": [["pl", None], ["pr", None]],
    "ບຣ": [["bl", None], ["br", None]],
    # 'ບລ': [['bl', None], ['bl', None]],
    "ບຼ": [["bl", None], ["bl", None]],
    "ດຼ": [["dl", None], ["dl", None]],
    "ດຣ": [["dl", None], ["dr", None]],
    "ທຼ": [["tl", None], ["tl", None]],
    "ຕຣ": [["tl", None], ["tr", None]],
    "ທຣ": [["tl", None], ["tr", None]],
    "ຕຼ": [["tl", None], ["tl", None]],
    "ບລ": [["bl", None], ["bl", None]],
    "ສຣ": [["sl", None], ["sr", None]],
    "ສລ": [["sl", None], ["sl", None]],
    "ສວ": [["sʋ", None], ["sv", None]],
    "ສຍ": [["sɲ", None], ["sny", None]],
    "ຊຣ": [["sl", None], ["xr", None]],
    "ຊລ": [["sl", None], ["xl", None]],
    "ຊວ": [["sʋ", None], ["xv", None]],
    "ຊຍ": [["sɲ", None], ["xny", None]],
    "ຈຣ": [["tɕl", None], ["chr", None]],
    "ຈລ": [["tɕl", None], ["chl", None]],
    "ຈວ": [["tɕʷ", None], ["chv", None]],
    "ຈຍ": [["tɕɲ", None], ["chny", None]],
    "ຳ": [["am", None], ["am", None]],
}

# dictionary of Lao vowels and assignments (IPA, MoH2020).
# https://laoconverter.info/moh2020.html
lao_vowel_assignments = {
    # vowel: [ipa assignment, ... other assignments in order based on output dictionary index]
    "ະ": ["a", "a"],
    "ັ": ["a", "a"],
    "ເະ": ["e", "e"],
    "ເັ": ["e", "e"],
    "ແະ": ["ɛ", "e"],  # Also eh if no final
    "ແັ": ["ɛ", "e"],  # Also eh if no final
    "ິ": ["i", "i"],
    "ໂະ": ["o", "o"],
    "ົ": ["o", "o"],
    "ເາະ": ["ɔ", "o"],  # Also oh if no final
    "ັອ": ["ɔ", "o"],  # Also oh if no final
    "ຸ": ["u", "ou"],
    "ຶ": ["ɯ", "u"],  # ue?
    "ເິ": ["ɤ", "eu"],
    "າ": ["aː", "a"],
    "ເ": ["eː", "e"],
    "ແ": ["ɛː", "e"],  # Also eh if no final
    "ີ": ["iː", "i"],
    "ໂ": ["oː", "o"],
    "ໍ": ["ɔː", "o"],  # Also oh if no final
    "ອ": ["ɔː", "o"],  # Also oh if no final
    "ູ": ["uː", "ou"],
    "ື": ["ɯː", "u"],  # ue?
    "ເີ": ["ɤː", "eu"],
    "ເຍ": ["iːə", "ia"],
    "ຽ": ["iːə", "ia"],
    "ົວ": ["uːə", "oua"],
    "ົວະ": ["uə", "oua"],
    "ວ": ["uːə", "oua"],
    "ວາ": ["uːə", "oua"],
    "ເຶອ": ["ɯə", "ua"],
    "ເືອ": ["ɯːə", "ua"],
    "ໃ": ["aj", "ai"],
    "ໄ": ["aj", "ai"],
    "ເົາ": ["aw", "ao"],
    #    "ວາ": ["uːə","oua"],
    "ເັຽ": ["iːə", "ia"],
    "ເັຍ": ["iə", "ia"],
    "ຳ": ["am", "am"],
}

lao_intermediate_vowel_states = {
    "ເ",
    "ແ",
    "ໂ",
    "ເາ",
    "ັ",
    "ົ",
    "ົວ",
    "ເຶ",
    "ເົ",
    "ເັ",
    # 'ວ' intentionally omitted to avoid global merging of 'ວ'+vowel
    "ເື",
}

lao_tone_markers = {"່", "້", "໊", "໋"}

lao_numbers = {
    "໐": "0",
    "໑": "1",
    "໒": "2",
    "໓": "3",
    "໔": "4",
    "໕": "5",
    "໖": "6",
    "໗": "7",
    "໘": "8",
    "໙": "9",
}

# list of Lao vowel characters in Unicode
lao_vowel_characters = {"ະ", "ັ", "າ", "ຳ", "ິ", "ີ", "ຶ", "ື", "ຸ", "ູ", "ົ", "ຽ", "ເ", "ແ", "ໂ", "ໃ", "ໄ", "ໍ", "ວ", "ອ", "ຍ"}
# list of Lao vowels that could come before the first consonant
lao_vowel_characters_pre = {"ເ", "ແ", "ໂ", "ໃ", "ໄ"}
# list of Lao vowels that could come after the first consonant
lao_vowel_characters_post = {"ະ", "ັ", "າ", "ຳ", "ິ", "ີ", "ຶ", "ື", "ຸ", "ູ", "ົ", "ຽ", "ໍ", "ວ", "ອ"}
# consonants that can begin a multi-character onset cluster
lao_start_consonant_pairs = {"ຫ", "ດ", "ບ", "ປ", "ຕ", "ທ", "ກ", "ຂ", "ພ", "ຝ", "ຟ", "ຄ", "ຖ", "ສ", "ຊ", "ຈ"}
# recognized multi-character onset clusters
lao_consonant_pairs = {"ຫມ", "ຝຮ", "ທຣ", "ຖວ", "ດຣ", "ພລ", "ຕຼ", "ຄລ", "ຕຣ", "ບລ", "ຝຼ", "ທຼ", "ດຼ", "ກຼ", "ຟຼ", "ພຼ", "ບຼ", "ກຣ", "ປຣ", "ບຣ", "ປຼ", "ຄຼ", "ຫລ", "ກວ", "ຂວ", "ພຣ", "ຝຣ", "ຟຣ", "ຄວ", "ຄຣ", "ຫວ", "ຫຣ", "ຫຍ", "ຫງ", "ຫນ", "ຫຼ", "ສຣ", "ສລ", "ສວ", "ສຍ", "ຊຣ", "ຊລ", "ຊວ", "ຊຍ", "ຈຣ", "ຈລ", "ຈວ", "ຈຍ"}
# newer clusters whose first consonant may instead start its own syllable
lao_loan_cluster_pairs = {"ສຣ", "ສລ", "ສວ", "ສຍ", "ຊຣ", "ຊລ", "ຊວ", "ຊຍ", "ຈຣ", "ຈລ", "ຈວ", "ຈຍ", "ຄລ"}
# ວ-clusters that can be either labialized onsets or /uːə/ nuclei
lao_labialized_clusters = {"ກວ", "ຂວ", "ຄວ", "ຈວ", "ສວ", "ຊວ"}
# vowels that make a preceding ວ an onset glide instead of a nucleus
lao_labializing_vowels = {"ັ", "ິ", "ີ", "ຶ", "ື", "ເ", "ແ", "ໂ", "ໍ", "ົ"}
# vowels after which ຽ is a variant of final ຍ /j/
lao_final_ya_vowels = {"າ", "ຳ", "ໍ", "ົ", "ໂ"}

# create a set of all Lao characters used in words for searching
lao_characters = set.union(
    set(lao_consonant_assignments.keys()),
    set(lao_vowel_assignments.keys()),
    lao_tone_markers,
)


def transliterate(
    lao_source: str,
    output: str = "ipa",
    ignore_tones: bool = False,
    remove_karan_phonemes: bool = False,
):
    """Top-level pipeline: transliterate a Lao string into the requested output system.

    The input is first split into syllable-sized chunks, then each chunk is
    transliterated independently. This keeps context-sensitive finals (such as
    the vocalic/consonantal role of 'ວ') local to their syllable.

    Args:
        lao_source (str): Input Lao text.
        output (str): Output system key. Valid options (currently): `'ipa'`, `'moh'`.
            Default is `'ipa'`. Additional systems can be added by
            extending the `outputs` mapping and corresponding tables.
        ignore_tones (bool): If True, strip tone markers and skip tone-related steps.
        remove_karan_phonemes (bool): If True, remove consonants silenced by '໌'.

    Returns:
        str: Transliterated string.

    Example:
        >>> transliterate('ສະບາຍດີ')
    """
    if lao_source == "":
        return ""
    if ignore_tones or remove_karan_phonemes:
        # These modes change which characters act as syllable nuclei, so
        # transliterate the whole string instead of splitting it first.
        return _transliterate_core(
            lao_source, output, ignore_tones, remove_karan_phonemes
        )
    chunks = _split_syllables_with_separators(lao_source)
    return "".join(
        _transliterate_core(chunk, output, ignore_tones, remove_karan_phonemes)
        for chunk in chunks
    )


def _tokenize(
    lao_source: str,
    *,
    ignore_tones: bool = False,
    remove_karan_phonemes: bool = False,
    track_spans: bool = False,
):
    """Run the shared token pipeline up to syllable assembly."""
    if track_spans:
        lao_array = [
            _LaoToken(char, position, position + 1)
            for position, char in enumerate(lao_source)
        ]
    else:
        lao_array = list(lao_source)
    if ignore_tones:
        lao_array = remove_tone_markers(lao_array)
    lao_array = remove_karan(lao_array, remove_karan_phonemes)
    lao_array = merge_double_consonants(lao_array)
    lao_array = swap_preorder_vowels(lao_array)
    lao_array = normalize_wa_and_ya(lao_array)
    if not ignore_tones:
        lao_array = swap_tone_markers(lao_array)
    lao_array = merge_vowels(lao_array)
    if not ignore_tones:
        lao_array = create_syllables_on_vowels(lao_array)
        lao_array = absorb_initial_consonants_into_syllables(lao_array)
        lao_array = absorb_tones_into_syllables(lao_array)
        lao_array = absorb_final_consonants_into_syllables(lao_array)
        lao_array = handle_repeater_on_syllables(lao_array)
    return lao_array


def _transliterate_core(
    lao_source: str,
    output: str = "ipa",
    ignore_tones: bool = False,
    remove_karan_phonemes: bool = False,
):
    """Run the token pipeline on one syllable or on the whole input string."""
    if lao_source == "ສ":
        # A lone ສ in archaic spellings is the syllable /sa/.
        lao_source = "ສະ"
    lao_array = _tokenize(
        lao_source,
        ignore_tones=ignore_tones,
        remove_karan_phonemes=remove_karan_phonemes,
    )
    if not ignore_tones:
        lao_array = transliterate_syllables(lao_array, output)
    return "".join(get_naive_transliteration(lao_array, output))


def remove_tone_markers(lao_array: list):
    """Remove tone marker characters from a Lao character array.

    Args:
        lao_array (List[str]): Sequence of Lao characters.

    Returns:
        List[str]: Filtered list without tone markers.
    """
    return [character for character in lao_array if character not in lao_tone_markers]


def _skip_tone_markers(tokens: list, position: int) -> int:
    """Return the index of the first token at or after `position` that is not a tone marker."""
    while position < len(tokens) and tokens[position] in lao_tone_markers:
        position += 1
    return position


def _is_initial_before_tone(tokens: list, position: int) -> bool:
    """Return whether the token before a tone marker begins a syllable."""
    previous = position - 1
    return (
        previous >= 0
        and tokens[previous] in lao_consonant_assignments
        and is_beginning_consonant(tokens[previous:])
    )


def _is_mergeable_pair(tokens: list, position: int) -> bool:
    """Return whether two tokens at `position` form one onset cluster."""
    if position + 1 >= len(tokens):
        return False
    first = tokens[position]
    if first not in lao_start_consonant_pairs:
        return False
    second = tokens[position + 1]
    pair = first + second
    if second != "ຼ" and pair not in lao_consonant_pairs:
        return False
    if pair == "ບລ" and position > 0:
        # ບ is usually the final of the previous syllable or the onset of a
        # short-vowel syllable, not the first member of a /bl/ cluster.
        return False
    if pair == "ສຍ":
        # ສຍ is a spelling variant of ສະຫຍ; ສ is its own syllable.
        return False
    if pair == "ປຣ" and position > 0 and tokens[position - 1] == "ເ":
        # After the short vowel ເ, ປ is the onset of the next syllable
        # (e.g. ໂອເປຣາ), not part of a /pr/ cluster.
        return False
    if pair[-1] == "ຣ":
        previous = tokens[position - 1] if position else None
        if previous in lao_vowel_characters_post:
            # The first consonant closes the previous syllable, so the next
            # ຣ-cluster starts a new syllable (e.g. ໂອຕຣິດ).
            return False
    if pair not in lao_loan_cluster_pairs:
        return True
    if position > 0 and tokens[position - 1] in lao_vowel_characters_pre:
        return False
    if pair[-1] not in {"ວ", "ຍ"}:
        return True
    next_position = _skip_tone_markers(tokens, position + 2)
    return (
        next_position < len(tokens)
        and tokens[next_position] in lao_vowel_characters_post
    )


def merge_double_consonants(lao_source_array: list):
    """Merge adjacent consonant characters into consonant digraphs where appropriate.

    Some Lao orthography forms consonant clusters using two codepoints
    (e.g. 'ຫ' + 'ມ' -> 'ຫມ'). This function scans the character sequence and
    merges recognized pairs into single tokens so downstream logic can
    treat them as unit consonant clusters.

    Args:
        lao_source_array (List[str]): Sequence of Lao characters/segments.

    Returns:
        List[str]: Sequence with valid digraphs merged.
    """
    result_array = []
    position = 0
    while position < len(lao_source_array):
        if _is_mergeable_pair(lao_source_array, position):
            result_array.append(
                lao_source_array[position] + lao_source_array[position + 1]
            )
            position += 2
        else:
            result_array.append(lao_source_array[position])
            position += 1
    return result_array


def swap_preorder_vowels(lao_array: list):
    """Reorder prepended vowels so vowel characters appear after their consonant.

    Lao uses some vowels that are written before the initial consonant but are
    pronounced after it. This helper moves those prepended vowel tokens
    to follow the consonant, simplifying later syllable assembly.

    Args:
        lao_array (List[str]): Sequence of Lao characters/tokens.

    Returns:
        List[str]: Reordered token sequence with all vowel characters following their consonants.
    """
    lao_array = merge_double_vowels(lao_array)
    position = 0
    result_array = []
    while position < len(lao_array):
        if (
            lao_array[position] in lao_vowel_characters_pre
            and position + 1 < len(lao_array)
            and lao_array[position + 1] in lao_consonant_assignments
        ):
            result_array.append(lao_array[position + 1])
            result_array.append(lao_array[position])
            position += 2
        else:
            result_array.append(lao_array[position])
            position += 1
    return result_array


def _resolve_tone_marker(tokens: list, position: int, previous):
    """Return the tokens emitted for a tone marker and the next scan position."""
    tone = tokens[position]
    vowel_position = _skip_tone_markers(tokens, position + 1)
    if (
        _is_initial_before_tone(tokens, position)
        and vowel_position < len(tokens)
        and tokens[vowel_position] in lao_vowel_characters
    ):
        return [tokens[vowel_position], tone], vowel_position + 1

    skipped = []
    test_position = position + 1
    position_diff = 0
    while position_diff < lao_tone_lookahead_limit and test_position < len(tokens):
        test_token = tokens[test_position]
        if test_token not in lao_vowel_characters:
            # A consonant starts a new syllable, so keep the tone before it.
            return skipped + [tone], position + position_diff + 1
        if test_token not in {"ອ", "ວ", "ຍ"}:
            # Keep scanning across ordinary vowels.
            skipped.append(test_token)
            previous = test_token
            test_position += 1
            position_diff += 1
            continue
        if (
            previous == "ົ"
            and test_token == "ວ"
            and test_position + 1 < len(tokens)
            and tokens[test_position + 1] == "ะ"
        ):
            # ົວະ is a compound vowel; the tone follows it.
            return (
                skipped + [test_token, tokens[test_position + 1], tone],
                position + position_diff + 3,
            )
        if (
            previous == "ເ"
            and test_token == "ຍ"
            and not is_beginning_consonant(tokens[test_position:])
        ):
            # ເຍ is a compound vowel; the tone follows it.
            return skipped + [test_token, tone], position + position_diff + 2
        if (
            previous == "ັ"
            and position >= 2
            and tokens[position - 2] == "ເ"
            and test_token == "ຍ"
            and not is_beginning_consonant(tokens[test_position:])
        ):
            # ເ + ັ + tone + ຍ spells the short vowel ເັຍ.
            return skipped + [test_token, tone], position + position_diff + 2
        if previous in lao_vowel_characters and not is_beginning_consonant(
            tokens[test_position:]
        ):
            # A glide after a vowel stays part of the vowel cluster.
            if (
                previous in {"ຶ", "ື"}
                or previous + test_token in lao_vowel_assignments
            ):
                return skipped + [test_token, tone], position + position_diff + 2
            return skipped + [tone], position + position_diff + 1
        if is_beginning_consonant(tokens[test_position:]):
            # The glide starts a new syllable; keep the tone before it.
            return skipped + [tone], position + position_diff + 1
        skipped.append(test_token)
        previous = test_token
        test_position += 1
        position_diff += 1
    return skipped + [tone], position + position_diff + 1


def swap_tone_markers(lao_array: list):
    """Move tone markers to their canonical position relative to vowels/consonants.

    The actual lookahead rules live in `_resolve_tone_marker`, which keeps this
    pass a simple token loop.

    Args:
        lao_array (List[str]): Sequence of Lao characters/tokens.

    Returns:
        List[str]: Token list with tone markers repositioned.
    """
    result_array = []
    position = 0
    while position < len(lao_array):
        if lao_array[position] in lao_tone_markers:
            previous = result_array[-1] if result_array else None
            emitted, position = _resolve_tone_marker(
                lao_array, position, previous
            )
            result_array.extend(emitted)
        else:
            result_array.append(lao_array[position])
            position += 1
    return result_array


def merge_double_vowels(lao_array: list):
    """Merge specific improperly written adjacent vowel characters into single compound vowel tokens.

    Args:
        lao_array (List[str]): Sequence of Lao characters/tokens.

    Returns:
        List[str]: Sequence with certain improperly written vowel pairs combined.
    """
    position = 0
    result_array = []
    while position < len(lao_array):
        if (
            lao_array[position] == "ເ"
            and position + 1 < len(lao_array)
            and lao_array[position + 1] == "ເ"
        ):
            result_array.append(
                _replace_span("ແ", lao_array[position], lao_array[position + 1])
            )
            position += 2
        elif (
            lao_array[position] == "ໍ"
            and position + 1 < len(lao_array)
            and lao_array[position + 1] == "າ"
        ):
            result_array.append(
                _replace_span("ຳ", lao_array[position], lao_array[position + 1])
            )
            position += 2
        else:
            result_array.append(lao_array[position])
            position += 1
    return result_array


def merge_vowels(lao_array: list):
    """Aggregate intermediate vowel states into final vowel tokens.

    This routine combines sequences of intermediate vowel markers into
    compound vowel tokens that appear in `lao_vowel_assignments`.

    Args:
        lao_array (List[str]): Sequence of Lao characters/segments.
    Returns:
        List[str]: Sequence with compound vowels merged.
    """
    position = 0
    result_array = []
    while position < len(lao_array):
        if lao_array[position] in lao_intermediate_vowel_states:
            compound_vowel = lao_array[position]
            while (
                position + 1 < len(lao_array)
                and compound_vowel + lao_array[position + 1]
                in lao_intermediate_vowel_states
            ):
                compound_vowel += lao_array[position + 1]
                position += 1
            if (
                position + 1 < len(lao_array)
                and compound_vowel + lao_array[position + 1] in lao_vowel_assignments
                and not (
                    lao_array[position + 1] == "ຍ"
                    and is_beginning_consonant(lao_array[position + 1:])
                )
            ):
                compound_vowel += lao_array[position + 1]
                position += 1
            result_array.append(compound_vowel)
        else:
            result_array.append(lao_array[position])
        position += 1
    return result_array


def _split_cluster(token):
    """Split a two-character cluster token, preserving source spans."""
    if isinstance(token, _LaoToken):
        split_at = token.start + len(token[0])
        return (
            _LaoToken(token[0], token.start, split_at),
            _LaoToken(token[1], split_at, token.end),
        )
    return token[0], token[1]


def _should_split_wa_cluster(tokens: list, position: int) -> bool:
    """Return whether the ວ-cluster at `position` is a nucleus, not an onset glide."""
    next_position = _skip_tone_markers(tokens, position + 1)
    next_char = tokens[next_position] if next_position < len(tokens) else None
    if position > 0 and tokens[position - 1] in lao_vowel_characters_post:
        return True
    if next_char in lao_labializing_vowels:
        return False
    if next_char in {"ຽ", "ຍ"}:
        after_ya = _skip_tone_markers(tokens, next_position + 1)
        return (
            after_ya >= len(tokens)
            or tokens[after_ya] not in lao_consonant_assignments
        )
    return True


def _reorder_wa_after_vowel(tokens: list, position: int):
    """Recognize C + short vowel + ວ + final as a labialized onset.

    The alternate spelling ຄັວນ is equivalent to ຄວັນ. The merged token is
    given the full syllable span so the splitter keeps the syllable together.
    """
    if position + 3 >= len(tokens):
        return None
    consonant = tokens[position]
    if consonant not in lao_consonant_assignments:
        return None
    if consonant in lao_labialized_clusters:
        return None
    vowel = tokens[position + 1]
    if vowel not in lao_vowel_assignments:
        return None
    if Syllable.get_vowel_length(vowel) != "short":
        return None
    if vowel + "ວ" in lao_vowel_assignments:
        return None
    if tokens[position + 2] != "ວ":
        return None
    final = tokens[position + 3]
    if final not in lao_final_consonants:
        return None
    cluster = consonant + "ວ"
    if cluster not in lao_consonant_assignments:
        return None
    merged = _replace_span(cluster, consonant, final)
    return [merged, vowel, final], position + 4


def normalize_wa_and_ya(lao_array: list) -> list:
    """Normalize ambiguous 'ວ' and 'ຽ' spellings before tone processing.

    A 'ວ' cluster is an onset glide before a front/central vowel (e.g. ຄວັນ)
    and a syllable nucleus otherwise (e.g. ຄວາມ, ສວນ, ຂວດ). 'ຽ' at the end
    of a syllable after a complete vowel is a variant of final 'ຍ' /j/.
    """
    result_array = []
    position = 0
    while position < len(lao_array):
        reordered = _reorder_wa_after_vowel(lao_array, position)
        if reordered is not None:
            emitted, position = reordered
            result_array.extend(emitted)
            continue
        token = lao_array[position]
        if token in lao_labialized_clusters and _should_split_wa_cluster(
            lao_array, position
        ):
            previous = lao_array[position - 1] if position else None
            next_position = _skip_tone_markers(lao_array, position + 1)
            next_char = (
                lao_array[next_position] if next_position < len(lao_array) else None
            )
            initial, wa_part = _split_cluster(token)
            result_array.append(initial)
            if next_char == "າ" and previous not in lao_vowel_characters_post:
                result_array.append(
                    _replace_span("ວາ", wa_part, lao_array[next_position])
                )
                result_array.extend(lao_array[position + 1 : next_position])
                position = next_position + 1
            else:
                result_array.append(wa_part)
                position += 1
            continue
        if token == "ຽ" and _is_final_ya_variant(lao_array, position):
            result_array.append(_replace_span("ຍ", token, token))
            position += 1
            continue
        result_array.append(token)
        position += 1
    return result_array


def _is_final_ya_variant(lao_array: list, position: int) -> bool:
    """Return True when 'ຽ' at `position` is a variant of final 'ຍ'."""
    previous = lao_array[position - 1] if position else None
    if previous in lao_final_ya_vowels:
        return True
    if previous != "ວ":
        return False
    before_wa = position - 2
    if before_wa >= 0 and lao_array[before_wa] in lao_tone_markers:
        before_wa -= 1
    if before_wa < 0 or lao_array[before_wa] not in lao_consonant_assignments:
        return False
    # A consonant preceded by a vowel closes the previous syllable, so this
    # 'ວ' is the onset of a new syllable (e.g. ວັງວຽງ, ຄາວຽກ).
    before_consonant = before_wa - 1
    return before_consonant < 0 or (
        lao_array[before_consonant] not in lao_vowel_characters
        and lao_array[before_consonant] not in lao_tone_markers
    )


def _acts_as_vowel(lao_array: list, index: int) -> bool:
    """Return whether the token at `index` functions as a vowel in context."""
    token = lao_array[index]
    if token not in lao_vowel_assignments:
        return False
    if token in lao_consonant_assignments:
        return not is_beginning_consonant(lao_array[index:])
    return True


def _has_vowel_before(lao_array: list, position: int) -> bool:
    """Return whether a vowel precedes `position`, optionally across a tone marker."""
    previous = position - 1
    if previous < 0:
        return False
    if _acts_as_vowel(lao_array, previous):
        return True
    return (
        lao_array[previous] in lao_tone_markers
        and previous > 0
        and _acts_as_vowel(lao_array, previous - 1)
    )


def create_syllables_on_vowels(lao_array):
    """Replace recognized vowel tokens with `Syllable` objects (initially vowel-only).

    Tokens that are not vowels remain unchanged.

    Args:
        lao_array (List[str]): Token sequence containing characters and intermediate tokens.

    Returns:
        List[Union[str, Syllable]]: Token sequence with `Syllable` objects inserted.
    """
    result_array = []
    for i, token in enumerate(lao_array):
        if token in lao_vowel_assignments and not is_beginning_consonant(
            lao_array[i:]
        ):
            if token in {"ວ", "ຍ"} and _has_vowel_before(lao_array, i):
                result_array.append(token)
            else:
                result_array.append(Syllable(vowel=token))
        else:
            result_array.append(token)
    return result_array


def absorb_initial_consonants_into_syllables(lao_array):
    """Attach preceding consonant tokens as the initial consonant of following Syllable objects.

    Scans the token list and when a consonant is immediately followed by
    a `Syllable` object, the consonant is absorbed into the syllable's
    `initial_consonant` attribute.

    Args:
        lao_array (List[Union[str, Syllable]]): Token list.

    Returns:
        List[Union[str, Syllable]]: Modified token list with initials absorbed.
    """
    result_array = []
    i = 0
    while i < len(lao_array):
        if (
            i + 1 < len(lao_array)
            and lao_array[i] in lao_consonant_assignments.keys()
            and isinstance(lao_array[i + 1], Syllable)
        ):
            syllable_obj: Syllable = lao_array[i + 1]
            syllable_obj.initial_consonant = lao_array[i]
            result_array.append(syllable_obj)
            i += 2
        else:
            result_array.append(lao_array[i])
            i += 1
    return result_array


def absorb_tones_into_syllables(lao_array):
    """Attach tone marker tokens to preceding `Syllable` objects.

    If a tone marker follows a `Syllable` object, it is moved into the
    object's `tone_marker` attribute so tonal computation is centralized.

    Args:
        lao_array (List[Union[str, Syllable]]): Token list.

    Returns:
        List[Union[str, Syllable]]: Token list with tones absorbed into `Syllable` objects.
    """
    result_array = []
    i = 0
    while i < len(lao_array):
        if (
            i + 1 < len(lao_array)
            and isinstance(lao_array[i], Syllable)
            and lao_array[i + 1] in lao_tone_markers
        ):
            syllable_obj: Syllable = lao_array[i]
            syllable_obj.tone_marker = lao_array[i + 1]
            result_array.append(syllable_obj)
            i += 2
        else:
            result_array.append(lao_array[i])
            i += 1
    return result_array


def absorb_final_consonants_into_syllables(lao_array):
    """Attach consonant tokens following a `Syllable` as its final consonant.

    This final absorption step identifies consonants that end syllables
    and moves them into the `Syllable.final_consonant` attribute.

    Args:
        lao_array (List[Union[str, Syllable]]): Token list.

    Returns:
        List[Union[str, Syllable]]: Token list with final consonants absorbed.
    """
    result_array = []
    i = 0
    while i < len(lao_array):
        if (
            i + 1 < len(lao_array)
            and isinstance(lao_array[i], Syllable)
            and lao_array[i + 1] in lao_consonant_assignments.keys()
        ):
            syllable_obj: Syllable = lao_array[i]
            syllable_obj.final_consonant = lao_array[i + 1]
            result_array.append(syllable_obj)
            i += 2
        else:
            result_array.append(lao_array[i])
            i += 1
    return result_array


# to add a new romanization system, add its index in the vowel and consonant value lists, default 1
outputs = {"ipa": 0, "moh": 1}


def transliterate_syllables(lao_array, output):
    """Flatten `Syllable` objects into transliterated strings.

    Args:
        lao_array (List[Union[str, Syllable]]): Token list.
        output (str): Output system key. Valid options (currently): `'ipa'`, `'moh'`.

    Returns:
        List[str]: List with `Syllable` objects replaced by transliterated strings.
    """
    result_array = []
    for item in lao_array:
        if isinstance(item, Syllable):
            result_array.append(item.get_transliteration(output))
        else:
            result_array.append(item)
    return result_array


def get_naive_transliteration(lao_array: list, output: str = "ipa"):
    """Rule-based transliteration for token lists using assignment tables.

    Args:
        lao_array (List[str|Syllable]): Token list to transliterate.
        output (str): Output system key. Valid options (currently): `'ipa'`, `'moh'`.

    Returns:
        List[str]: Transliteration parts to join into final string.
    """
    output_index = outputs[output]
    result_array = []
    for index, segment in enumerate(lao_array):
        if segment is None:
            continue
        to_append = ""
        # explicit string handling
        if isinstance(segment, str) and segment in lao_characters:
            # vowel handling first
            if segment in lao_vowel_assignments:
                if segment in {"ອ", "ວ"}:
                    try:
                        if (
                            lao_array[index - 1] in lao_consonant_assignments
                            and lao_array[index + 1] in lao_consonant_assignments
                        ):
                            to_append = lao_vowel_assignments[segment][output_index]
                    except IndexError:
                        pass
                else:
                    to_append = lao_vowel_assignments[segment][output_index]
            # consonant handling
            if to_append == "" and segment in lao_consonant_assignments:
                cons_entry = lao_consonant_assignments[segment][output_index]
                # Decision order: if a vowel follows the consonant (start of
                # a syllable) or there is no distinct final-form mapping,
                # use the initial-form (onset). Otherwise use the final-form.
                if (
                    index + 1 < len(lao_array)
                    and lao_array[index + 1] in lao_vowel_assignments
                ) or cons_entry[1] is None:
                    to_append = cons_entry[0]
                else:
                    to_append = cons_entry[1]
        # fallback: segment may be a multi-char string not listed in lao_characters (e.g., unexpected combos)
        elif (
            isinstance(segment, str)
            and len(segment) > 0
            and segment[0] in lao_consonant_assignments
        ):
            result_string = ""
            for character in segment:
                if character in lao_consonant_assignments:
                    result_string += lao_consonant_assignments[character][output_index][0]
                else:
                    result_string += character
            to_append = result_string
        elif (
            isinstance(segment, str)
            and len(segment) > 0
            and segment[0] in lao_vowel_assignments
        ):
            result_string = ""
            for character in segment:
                if character in lao_vowel_assignments:
                    result_string += lao_vowel_assignments[character][output_index]
                else:
                    result_string += character
            to_append = result_string
        else:
            # Handle punctuation, numerals, and other special cases.
            to_append = process_special_characters(segment)
        result_array.append(to_append)
    return result_array


def process_special_characters(char):
    """Handle isolated special Lao characters (abbreviation sign, numerals).

    Args:
        char (str): Single character/token.

    Returns:
        str: Replacement string (possibly empty).
    """
    # Lao abbreviation sign (U+0EF1) -> remove
    if char == "ຯ":
        return ""
    elif char in lao_numbers:
        return lao_numbers[char]
    else:
        return char


def handle_repeater_on_syllables(lao_array: list, repeater_char: str = "ໆ"):
    """Handle Lao repeater mark by duplicating previous syllable when present.

    When the `lao_array` contains `Syllable` objects, duplicate the previous
    `Syllable` object wherever the Lao repeater mark `repeater_char` appears.
    If no previous `Syllable` exists at a repeater position, the repeater is
    removed.

    NOTE: Non-syllable repeater handling (when the pipeline has already flattened
    to strings) is currently a noop (repeater removed). Fixing repeater behavior
    after syllable flattening is TODO.

    Args:
        lao_array (List[Union[str, Syllable]]): Token list containing string tokens and/or `Syllable` objects.
        repeater_char (str): The Lao iteration mark to handle (default 'ໆ').

    Returns:
        List[Union[str, Syllable]]: Token list with repeaters expanded into duplicated `Syllable` objects when possible.
    """
    result = []
    saw_syllable = False
    for item in lao_array:
        if item == repeater_char:
            if saw_syllable and result:
                prev = result[-1]
                if isinstance(prev, Syllable):
                    # duplicate by creating a fresh Syllable with same components
                    dup = Syllable(
                        vowel=prev.vowel,
                        initial_consonant=prev.initial_consonant,
                        final_consonant=prev.final_consonant,
                        tone_marker=prev.tone_marker,
                    )
                    result.append(dup)
                else:
                    # previous not a Syllable — ignore repeater for now
                    pass
            else:
                # nothing to repeat, drop the repeater
                pass
        else:
            result.append(item)
            if isinstance(item, Syllable):
                saw_syllable = True
    return result


def _source_span(item):
    """Return the original character range covered by a pipeline item."""
    if isinstance(item, Syllable):
        components = [
            component
            for component in (
                item.vowel,
                item.initial_consonant,
                item.final_consonant,
                item.tone_marker,
            )
            if isinstance(component, _LaoToken)
        ]
        if not components:
            return None
        return (
            min(component.start for component in components),
            max(component.end for component in components),
        )
    if isinstance(item, _LaoToken):
        return item.start, item.end
    return None


def _split_syllables_with_separators(lao_source: str):
    """Split text into syllables while preserving whitespace and separators."""
    lao_array = _tokenize(lao_source, track_spans=True)

    chunks = []
    cursor = 0
    previous_span = None
    for item in lao_array:
        span = _source_span(item)
        if span is None:
            continue
        start, end = span
        if span == previous_span:
            # Repeater expansion: emit the preceding syllable again.
            chunks.append(lao_source[start:end])
            continue
        # Tone markers can be moved across a syllable boundary; clamp spans
        # so chunks never overlap and every source character is used once.
        start = max(start, cursor)
        if end <= start:
            continue
        chunks.append(lao_source[start:end])
        cursor = end
        previous_span = span
    return chunks


def split_syllables(lao_source: str):
    """Split Lao text into syllable-sized chunks.

    Repeater marks ('ໆ') are expanded into a duplicate of the preceding
    syllable. Whitespace is omitted, while punctuation and other separators
    are kept as their own chunks.

    Args:
        lao_source (str): Input Lao text.

    Returns:
        List[str]: Syllable and separator chunks in reading order.

    Example:
        >>> split_syllables('ສຣີລັງກາ')
        ['ສຣີ', 'ລັງ', 'ກາ']
    """
    if lao_source == "":
        return []
    return [
        chunk
        for chunk in _split_syllables_with_separators(lao_source)
        if chunk.strip()
    ]


def remove_karan(array: list, remove_karan_phonemes: bool):
    """Remove karan (silencer) characters and optionally the consonant before them.

    Args:
        array (List[str]): Token list.
        remove_karan_phonemes (bool): If True, remove consonants silenced by karan as well.

    Returns:
        List[str]: List of characters with karan and optionally silenced consonants removed.
    """
    result_array = []
    for i in range(len(array)):
        if array[i] != "໌" and (
            not remove_karan_phonemes or i + 1 >= len(array) or array[i + 1] != "໌"
        ):
            result_array.append(array[i])
    return result_array


def is_beginning_consonant(lao_array):
    """Return whether the token sequence represents a consonant that begins a syllable.

    The function inspects the first token (after removing tone markers) and
    looks ahead to determine whether it is followed by a vowel-like token.

    Args:
        lao_array (List[str]): Token sequence starting at candidate consonant.

    Returns:
        bool: True if the first token is a consonant beginning a syllable.

    Examples:
        >>> is_beginning_consonant(list('ກາ'))  # ກ followed by vowel -> True
        >>> is_beginning_consonant(['ກ'])       # single consonant -> False
    """
    lao_array = remove_tone_markers(lao_array)
    possible_beginning = lao_array[0]
    if possible_beginning not in lao_consonant_assignments.keys():
        return False
    try:
        next_char = lao_array[1]
        if next_char in {"ວ", "ອ"}:
            return (
                lao_array[2] == "ຍ"
                or lao_array[2] not in lao_vowel_assignments
            )
        elif next_char == "ຍ" or next_char not in lao_vowel_assignments:
            return False
        else:
            return True
    except IndexError:
        return False


def check_vowel_lists():
    """Debug helper: check intermediate vowel decomposition consistency.

    Scans `lao_vowel_assignments` and prints any intermediate forms that are
    not present in `lao_intermediate_vowel_states`. Intended for debugging
    and validation of vowel decomposition logic.

    Returns:
        None
    """
    for vowel in lao_vowel_assignments:
        short_vowel = vowel.rstrip(vowel[len(vowel) - 1])
        if short_vowel != "" and short_vowel not in lao_intermediate_vowel_states:
            print(short_vowel)


if __name__ == "__main__":
    user_input = ""
    while user_input != "quit":
        user_input = input("Phrase: ").replace("\u200b", "")
        print(transliterate(user_input, "ipa", False))
