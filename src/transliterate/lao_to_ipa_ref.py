#TODO: Add module docstring, abbreviations like 'ກມ','kɔː˩(˧).mɔː˧˥'

class Syllable:
    LAO_SPECIAL_VOWELS = {'ຳ','ເົາ','ໃ','ໄ'}

    def __init__(self, vowel, initial_consonant=None, final_consonant=None, tone_marker=None):
        self.vowel = vowel
        self.initial_consonant = initial_consonant
        self.final_consonant = final_consonant
        self.tone_marker = tone_marker
        self.letter_class = None
        self.vowel_length = Syllable.get_vowel_length(vowel)
        # Treat certain special vowels (am/ao/ai) as live for tone purposes
        self.dead_syllable = self.final_consonant in {"ກ","ດ","ບ"} or (self.final_consonant is None and self.vowel_length == 'short' and vowel not in Syllable.LAO_SPECIAL_VOWELS)

    def __str__(self):
        return self.get_transliteration('ipa')
    
    def __repr__(self):
        return self.get_transliteration('ipa')

    # Reference: https://seasite.niu.edu/lao/LaoLanguage/IntroAlphabet/tonemarks/tonechart.htm
    def get_tone(self):
        # Tone class is determined by the first initial consonant character (even when 'ຫ' modifies following consonant).
        first_letter = self.initial_consonant[0] if self.initial_consonant is not None else None
        self.letter_class = Syllable.get_letter_class(first_letter)
        # Recompute dead_syllable taking into account special vowels as live
        self.dead_syllable = self.final_consonant in {"ກ","ດ","ບ"} or (self.final_consonant is None and self.vowel_length == 'short' and self.vowel not in Syllable.LAO_SPECIAL_VOWELS)
        # Tone mappings adjusted to match Wiktionary (Vientiane) IPA contours.
        tone_mapping_thoo = {
            # letter class: tone (for marker "້")
            'high': "˧˩",
            'middle': "˥˨",
            'low': "˥˨",
            None: None
        }
        tone_mapping_live = {
            # letter class: tone for live (smooth) syllables
            'high': "˩˧",
            'middle': "˩˧",
            'low': "˧˥",
            None: None
        }
        tone_mapping_dead = {
            # (letter class, vowel length): tone for checked (dead) syllables
            ('high','long'): "˧˩",
            ('middle','long'): "˧˩",
            ('low','long'): "˥˨",
            ('high','short'): "˧˥",
            ('middle','short'): "˧˥",
            ('low','short'): "˧",
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
            tone = tone_mapping_dead[(self.letter_class, self.vowel_length)] if self.letter_class is not None and self.vowel_length is not None else None
        return tone if tone is not None else ""

    def get_transliteration(self, system):
        transliterated_list = []
        # Prefer explicit initial-form mapping for initial consonants so we don't
        # accidentally select final-form mapping when transliterate() is called
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
                transliterated_list.extend(transliterate([self.initial_consonant], system))

        # Vowel handling: when using direct table lookup append the string,
        # otherwise extend the transliterate() result (a list).
        if self.vowel is not None:
            try:
                vowel_entry = lao_vowel_assignments[self.vowel][outputs[system]]
                transliterated_list.append(vowel_entry)
            except KeyError:
                transliterated_list.extend(transliterate([self.vowel], system))

        if self.final_consonant is not None:
            try:
                final_cons_entry = lao_consonant_assignments[self.final_consonant][outputs[system]]
                transliterated_list.append(final_cons_entry[1] if final_cons_entry[1] is not None else final_cons_entry[0])
            except KeyError:
                transliterated_list.extend(transliterate([self.final_consonant], system))
        transliterated_list.append(self.get_tone())
        return "".join(transliterated_list)

    @staticmethod
    def get_letter_class(letter):
        if letter in {"ຂ","ສ","ຖ","ຜ","ຝ","ຫ","ໜ","ໝ"}:
            return 'high'
        elif letter in {"ກ","ຈ","ດ","ຕ","ບ","ປ","ຢ","ອ"}:
            return 'middle'
        elif letter in {"ຄ","ງ","ຊ","ຍ","ທ","ນ","ພ","ຟ","ມ","ຣ","ລ","ວ","ຮ"}:
            return 'low'
        else:
            return None
        
    @staticmethod
    def get_vowel_length(vowel):
        if vowel in {"ະ","ັ","ເະ","ເັ","ແະ","ແັ","ິ","ໂະ","ົ","ເາະ","ັອ","ຸ","ຶ","ເິ","ົວະ","ເຶອ","ໃ","ໄ","ເົາ","ເັຽ","ເັຍ","ຳ"}:
            return 'short'
        elif vowel in {"າ","ເ","ແ","ີ","ໂ","ໍ","ອ","ູ","ື","ເີ","ເຍ","ຽ","ົວ","ວ","ເືອ"}:
            return 'long'
        else:
            return None
        
# dictionary of Lao consonants and assignments (IPA, MoH2020). 
# https://laoconverter.info/moh2020.html
lao_consonant_assignments = {
    # cons: [ipa sound list [beginning sound, final sound], ... other sound lists in same format]
    'ບ': [['b', 'p'], ['b', 'p']], 
    'ດ': [['d', 't'], ['d', 't']], 
    'ຝ': [['f', None], ['f', None]], 
    'ຟ': [['f', None], ['f', None]], 
    'ຫ': [['h', None], ['h', None]], 
    'ຮ': [['h', None], ['h', None]], 
    'ຢ': [['j', None], ['y', None]], 
    'ກ': [['k', None], ['k', None]], 
    'ຂ': [['kʰ', None], ['kh', None]], 
    'ຄ': [['kʰ', None], ['kh', None]], 
    'ລ': [['l', None], ['l', None]], 
    'ຫຼ': [['l', None], ['l', None]], 
    'ຫລ': [['l', None], ['l', None]], 
    'ມ': [['m', None], ['m', None]], 
    'ຫມ': [['m', None], ['m', None]], 
    'ໝ': [['m', None], ['m', None]], 
    'ນ': [['n', None], ['n', None]], 
    'ຫນ': [['n', None], ['n', None]], 
    'ໜ': [['n', None], ['n', None]], 
    'ງ': [['ŋ', None], ['ng', None]], 
    'ຫງ': [['ŋ', None], ['ng', None]], 
    'ຍ': [['ɲ', 'j'], ['ny', 'y']], 
    'ຫຍ': [['ɲ', None], ['ny', None]], 
    'ປ': [['p', None], ['p', None]], 
    'ຜ': [['pʰ', None], ['ph', None]], 
    'ພ': [['pʰ', None], ['ph', None]], 
    'ຣ': [['r', 'n'], ['r', None]], 
    'ຫຣ': [['r', None], ['r', None]], 
    'ສ': [['s', None], ['s', None]], 
    'ຊ': [['s', None], ['x', None]], 
    'ຕ': [['t', None], ['t', None]], 
    'ຖ': [['tʰ', 't'], ['th', None]], 
    'ທ': [['tʰ', None], ['th', None]], 
    'ຈ': [['tɕ', None], ['ch', None]], 
    'ວ': [['ʋ', 'w'], ['v', 'o']], 
    'ຫວ': [['ʋ', None], ['v', None]], 
    'ອ': [['', None], ['', None]], 
    'ຼ': [['l', None], ['l', None]], 
    'ຄຣ': [['kʰr', None], ['khr', None]], 
    'ຄລ': [['kʰl', None], ['khl', None]], 
    'ຄວ': [['kʰʋ', None], ['khv', None]], 
    'ຖວ': [['taʋ', None], ['thv', None]], 
    'ຟຣ': [['fr', None], ['fr', None]], 
    'ຟຼ': [['fl', None], ['fl', None]], 
    'ຝຣ': [['far', None], ['fr', None]], 
    'ຝຮ': [['far', None], ['fr', None]], 
    'ຝຼ': [['fal', None], ['fl', None]], 
    'ພຣ': [['pʰr', None], ['phr', None]], 
    'ພລ': [['pʰl', None], ['phl', None]], 
    'ພຼ': [['pʰl', None], ['phl', None]], 
    'ຂວ': [ ['kʰʋ', None], ['khv', None]], 
    'ກວ': [['kʷ', None], ['kv', None]],
    'ກຣ': [['kr', None], ['kr', None]], 
    # 'ກຮ': [['kr', None], ['kr', None]], 
    'ກຼ': [['kl', None], ['kl', None]], 
    'ຄຼ': [['kʰl', None], ['khl', None]], 
    'ປຼ': [['pl', None], ['pl', None]], 
    'ປຣ': [['pr', None], ['pr', None]], 
    'ບຣ': [['br', None], ['br', None]], 
    # 'ບລ': [['bl', None], ['bl', None]], 
    'ບຼ': [['bl', None], ['bl', None]], 
    'ດຼ': [['dr', None], ['dl', None]], 
    'ດຣ': [['dr', None], ['dr', None]], 
    'ທຼ': [['tr', None], ['tl', None]], 
    'ຕຣ': [['tr', None], ['tr', None]], 
    'ທຣ': [['tr', None], ['tr', None]], 
    'ຕຼ': [['tr', None], ['tl', None]],
    "ຳ": [["am", None], ["am", None]],
    }

# dictionary of Lao vowels and assignments (IPA, MoH2020). 
# https://laoconverter.info/moh2020.html
lao_vowel_assignments = {
    # vowel: [ipa assignment, ... other assignments in order based on output dictionary index]
    "ະ": ["a","a"],
    "ັ": ["a","a"],
    "ເະ": ["e","e"],
    "ເັ": ["e","e"],
    "ແະ": ["ɛ","e"], # Also eh if no final
    "ແັ": ["ɛ","e"], # Also eh if no final
    "ິ": ["i", "i"],
    "ໂະ": ["o", "o"],
    "ົ": ["o", "o"],
    "ເາະ": ["ɔ", "o"], # Also oh if no final
    "ັອ": ["ɔ", "o"], # Also oh if no final
    "ຸ": ["u", "ou"],
    "ຶ": ["ɯ","u"], # ue?
    "ເິ": ["ɤ","eu"],
    "າ": ["aː","a"],
    "ເ": ["eː","e"],
    "ແ": ["ɛː","e"], # Also eh if no final
    "ີ": ["iː","i"],
    "ໂ": ["oː","o"],
    "ໍ": ["ɔː","o"], # Also oh if no final
    "ອ": ["ɔː","o"], # Also oh if no final
    "ູ": ["uː","ou"],
    "ື": ["ɯː","u"], # ue?
    "ເີ": ["ɤː","eu"],
    "ເຍ": ["iːə","ia"],
    "ຽ": ["iːə", "ia"],
    "ົວ": ["uːə","oua"],
    "ົວະ": ["uə","oua"],
    "ວ": ["uːə","oua"],
    "ເຶອ": ["ɯə","ua"],
    "ເືອ": ["ɯːə","ua"],
    "ໃ": ["aj","ai"],
    "ໄ": ["aj","ai"],
    "ເົາ": ["aw","ao"],
#    "ວາ": ["uːə","oua"],
    "ເັຽ": ["iːə", "ia"],
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

lao_tone_markers = {"່","້","໊","໋"}

lao_numbers = {
    '໐': '0',
    '໑': '1',
    '໒': '2',
    '໓': '3',
    '໔': '4',
    '໕': '5',
    '໖': '6',
    '໗': '7',
    '໘': '8',
    '໙': '9'
}

# list of Lao vowel characters in Unicode
lao_vowel_characters = {"ະ","ັ","າ","ຳ","ິ","ີ","ຶ","ື","ຸ","ູ","ົ","ຽ","ເ","ແ","ໂ","ໃ","ໄ","ໍ","ວ","ອ","ຍ"}
# list of Lao vowels that could come before the first consonant
lao_vowel_characters_pre = {"ເ","ແ","ໂ","ໃ","ໄ"}
# list of Lao vowels that could come after the first consonant
lao_vowel_characters_post = {"ະ","ັ","າ","ຳ","ິ","ີ","ຶ","ື","ຸ","ູ","ົ","ຽ","ໍ","ວ","ອ"}

# create a set of all Lao characters used in words for searching
lao_characters = set.union(set(lao_consonant_assignments.keys()),set(lao_vowel_assignments.keys()), lao_tone_markers)

def lao2ipa(lao_source: str, output: str = 'ipa', ignore_tones: bool = False, remove_karan_phonemes: bool = False):
    if lao_source == '':
        return ''
    # Convert string to list
    lao_array = list(lao_source)
    if ignore_tones:
        # Remove tone markers
        lao_array = remove_tone_markers(lao_array)
    # Remove silenced characters
    lao_array = remove_karan(lao_array, remove_karan_phonemes)
    # Merge double consonants
    lao_array = merge_double_consonants(lao_array)
    # Move pre vowels to post/update vowels set
    lao_array = swap_preorder_vowels(lao_array)
    if not ignore_tones:
        lao_array = swap_tone_markers(lao_array)
    lao_array = merge_vowels(lao_array)
    if not ignore_tones:
        lao_array = create_syllables_on_vowels(lao_array)
        lao_array = absorb_initial_consonants_into_syllables(lao_array)
        lao_array = absorb_tones_into_syllables(lao_array)
        lao_array = absorb_final_consonants_into_syllables(lao_array)
        # Handle repeater character logic while objects are grouped by Syllable.
        # If Syllable objects are present, duplicate the previous Syllable when 'ໆ' appears.
        # If no Syllable objects are present (non-syllable processing), simply remove 'ໆ' for now.
        lao_array = handle_repeater_on_syllables(lao_array)
        lao_array = transliterate_syllables(lao_array, output)
    # Iterate through string and replace valid syllables with ipa
    # Rule-based convert remaining characters
    # Process special characters
    transliterated_array = transliterate(lao_array, output)
    return "".join(transliterated_array)

def remove_tone_markers(lao_array: list):
    result_array = []
    for character in lao_array:
        if character not in lao_tone_markers:
            result_array.append(character)
    return result_array

def merge_double_consonants(lao_source_array: list):
    # list of consonants that can have consonant pairs
    lao_start_consonant_pairs = {"ຫ","ດ","ບ","ປ","ຕ","ທ","ກ","ຂ","ພ","ຝ","ຟ","ຄ","ຖ"}
    # list of Lao consonant pairs
    lao_consonant_pairs = {"ຫມ","ຝຮ","ທຣ","ຖວ","ດຣ","ພລ","ຕຼ","ຄລ","ຕຣ","ບລ","ຝຼ","ທຼ","ດຼ","ກຼ","ຟຼ","ພຼ","ບຼ","ກຣ","ປຣ","ບຣ","ປຼ","ຄຼ","ຫລ","ກວ","ຂວ","ພຣ","ຝຣ","ຟຣ","ຄວ","ຄຣ","ຫວ","ຫຣ","ຫຍ","ຫງ","ຫນ","ຫຼ"} # Removed gh
    position = 0
    result_array = []
    while position < len(lao_source_array):
        if (lao_source_array[position] in lao_start_consonant_pairs and position + 1 < len(lao_source_array) and (lao_source_array[position] + lao_source_array[position + 1] in lao_consonant_pairs or lao_source_array[position + 1] == 'ຼ')):
            result_array.append(lao_source_array[position] + lao_source_array[position + 1])
            position += 2
        else:
            result_array.append(lao_source_array[position])
            position += 1
    return result_array

def swap_preorder_vowels(lao_array: list):
    lao_array = merge_double_vowels(lao_array)
    position = 0
    result_array = []
    while position < len(lao_array):
        if (lao_array[position] in lao_vowel_characters_pre and position + 1 < len(lao_array) and lao_array[position + 1] in lao_consonant_assignments):
            result_array.append(lao_array[position + 1])
            result_array.append(lao_array[position])
            position += 2
        else:
            result_array.append(lao_array[position])
            position += 1
    return result_array

def swap_tone_markers(lao_array: list):
    position = 0
    result_array = []
    while position < len(lao_array):
        if lao_array[position] in lao_tone_markers:
            test_position = position + 1
            position_diff = 0
            while position_diff < 7 and test_position < len(lao_array):
                if lao_array[test_position] in lao_vowel_characters:
                    if lao_array[test_position] in {"ອ","ວ","ຍ"}:
                        if result_array != [] and result_array[len(result_array) - 1] == "ົ" and lao_array[test_position] == "ວ" and test_position + 1 < len(lao_array) and lao_array[test_position + 1] == "ะ":
                            result_array.append(lao_array[test_position])
                            result_array.append(lao_array[test_position + 1])
                            result_array.append(lao_array[position])
                            position += (position_diff + 3)
                            break
                        elif result_array != [] and result_array[len(result_array) - 1] == "ເ" and lao_array[test_position] == "ຍ" and not(is_beginning_consonant(lao_array[test_position:])):
                            result_array.append(lao_array[test_position])
                            result_array.append(lao_array[position])
                            position += (position_diff + 2)
                            break
                        elif result_array != [] and result_array[len(result_array) - 1] in lao_vowel_characters and not(is_beginning_consonant(lao_array[test_position:])):
                            if result_array[len(result_array) - 1] in {"ຶ","ື"} or result_array[len(result_array) - 1] + lao_array[test_position] in lao_vowel_assignments.keys():
                                result_array.append(lao_array[test_position])
                                result_array.append(lao_array[position])
                                position += (position_diff + 2)
                                break
                            else:
                                result_array.append(lao_array[position])
                                position += (position_diff + 1)
                                break
                        elif is_beginning_consonant(lao_array[test_position:]):
                            result_array.append(lao_array[position])
                            position += (position_diff + 1)
                            break
                        else:
                            result_array.append(lao_array[test_position])
                            test_position += 1
                            position_diff += 1
                    else:
                        result_array.append(lao_array[test_position])
                        test_position += 1
                        position_diff += 1
                else:
                    result_array.append(lao_array[position])
                    position += (position_diff + 1)
                    break
            if test_position >= len(lao_array):
                result_array.append(lao_array[position])
                position += (position_diff + 1)
        else:
            result_array.append(lao_array[position])
            position += 1
    return result_array


def merge_double_vowels(lao_array: list):
    position = 0
    result_array = []
    while position < len(lao_array):
        if (lao_array[position] == "ເ" and position + 1 < len(lao_array) and lao_array[position + 1] == "ເ"):
            result_array.append("ແ")
            position += 2
        elif (lao_array[position] == "ໍ" and position + 1 < len(lao_array) and lao_array[position + 1] == "າ"):
            result_array.append("ຳ")
            position += 2
        else:
            result_array.append(lao_array[position])
            position += 1
    return result_array

def merge_vowels(lao_array: list):
    position = 0
    result_array = []
    while position < len(lao_array):
        if (lao_array[position] in lao_intermediate_vowel_states):
            compound_vowel = lao_array[position]
            while(position + 1 < len(lao_array) and compound_vowel + lao_array[position + 1] in lao_intermediate_vowel_states):
                compound_vowel += lao_array[position + 1]
                position += 1
            if(position + 1 < len(lao_array) and compound_vowel + lao_array[position + 1] in lao_vowel_assignments):
                if not(lao_array[position + 1] == "ຍ" and is_beginning_consonant(lao_array[position + 1:])):
                    compound_vowel += lao_array[position + 1]
                    position += 1
            result_array.append(compound_vowel)
        else:
            result_array.append(lao_array[position])
        position += 1
    return result_array

def create_syllables_on_vowels(lao_array):
    result_array = []
    for i in range(len(lao_array)):
        if lao_array[i] in lao_vowel_assignments.keys() and not(is_beginning_consonant(lao_array[i:])):
            if lao_array[i] in {"ວ","ຍ"} and (i - 1 >= 0 and (lao_array[i - 1] in lao_vowel_assignments or (lao_array[i - 1] in lao_tone_markers and i - 2 >= 0 and lao_array[i - 2] in lao_vowel_assignments))):
                result_array.append(lao_array[i])
            else:
                result_array.append(Syllable(vowel=lao_array[i]))
        else:
            result_array.append(lao_array[i])
    return result_array

def absorb_initial_consonants_into_syllables(lao_array):
    result_array = []
    i = 0
    while i < len(lao_array):
        if i + 1 < len(lao_array) and lao_array[i] in lao_consonant_assignments.keys() and isinstance(lao_array[i + 1], Syllable):
            syllable_obj: Syllable = lao_array[i + 1]
            syllable_obj.initial_consonant = lao_array[i]
            result_array.append(syllable_obj)
            i += 2
        else:
            result_array.append(lao_array[i])
            i += 1
    return result_array

def absorb_tones_into_syllables(lao_array):
    result_array = []
    i = 0
    while i < len(lao_array):
        if i + 1 < len(lao_array) and isinstance(lao_array[i], Syllable) and lao_array[i + 1] in lao_tone_markers:
            syllable_obj: Syllable = lao_array[i]
            syllable_obj.tone_marker = lao_array[i + 1]
            result_array.append(syllable_obj)
            i += 2
        else:
            result_array.append(lao_array[i])
            i += 1
    return result_array

def absorb_final_consonants_into_syllables(lao_array):
    result_array = []
    i = 0
    while i < len(lao_array):
        if i + 1 < len(lao_array) and isinstance(lao_array[i], Syllable) and lao_array[i + 1] in lao_consonant_assignments.keys():
            syllable_obj: Syllable = lao_array[i]
            syllable_obj.final_consonant = lao_array[i + 1]
            result_array.append(syllable_obj)
            i += 2
        else:
            result_array.append(lao_array[i])
            i += 1
    return result_array
    
# to add a new romanization system, add its index in the vowel and consonant value lists, default 1
outputs = {
    "ipa": 0,
    "moh": 1
}

def transliterate_syllables(lao_array, output):
    result_array = []
    for item in lao_array:
        if isinstance(item, Syllable):
            result_array.append(item.get_transliteration(output))
        else:
            result_array.append(item)
    return result_array

def transliterate(lao_array: list, output: str = 'ipa'):
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
                if segment in {"ອ","ວ"}:
                    try:
                        if lao_array[index - 1] in lao_consonant_assignments and lao_array[index + 1] in lao_consonant_assignments:
                            to_append = lao_vowel_assignments[segment][output_index]
                    except IndexError:
                        pass
                else:
                    to_append = lao_vowel_assignments[segment][output_index]
            # consonant handling
            if to_append == "" and segment in lao_consonant_assignments:
                cons_entry = lao_consonant_assignments[segment][output_index]
                # if vowel follows or there is no distinct final form, use initial form, otherwise use final form
                if (index + 1 < len(lao_array) and lao_array[index + 1] in lao_vowel_assignments) or cons_entry[1] is None:
                    to_append = cons_entry[0]
                else:
                    to_append = cons_entry[1]
        # fallback: segment may be a multi-char string not listed in lao_characters (e.g., unexpected combos)
        elif isinstance(segment, str) and len(segment) > 0 and segment[0] in lao_consonant_assignments:
            result_string = ""
            for character in segment:
                if character in lao_consonant_assignments:
                    result_string += lao_consonant_assignments[character][output_index][0]
                else:
                    result_string += character
            to_append = result_string
        elif isinstance(segment, str) and len(segment) > 0 and segment[0] in lao_vowel_assignments:
            result_string = ""
            for character in segment:
                if character in lao_vowel_assignments:
                    result_string += lao_vowel_assignments[character][output_index]
                else:
                    result_string += character
            to_append = result_string
        else:
            to_append = process_special_characters(segment)
        result_array.append(to_append)
    return result_array

def process_special_characters(char):
    # Lao abbreviation sign (U+0EF1) -> remove
    if char == "ຯ":
        return ''
    elif char in lao_numbers:
        return lao_numbers[char]
    else:
        return char

def handle_repeater_on_syllables(lao_array: list, repeater_char: str = 'ໆ'):
    """
    When the lao_array contains Syllable objects, duplicate the previous Syllable object
    wherever the Lao iteration mark 'ໆ' appears. If no previous Syllable exists at a
    repeater position, the repeater is simply removed.

    NOTE: Non-syllable repeater handling (when the pipeline has already flattened to
    strings) is currently a noop (repeater removed). Fixing repeater behavior after
    syllable flattening is TODO.
    """
    result = []
    saw_syllable = False
    for item in lao_array:
        if item == repeater_char:
            if saw_syllable and result:
                prev = result[-1]
                if isinstance(prev, Syllable):
                    # duplicate by creating a fresh Syllable with same components
                    dup = Syllable(vowel=prev.vowel, initial_consonant=prev.initial_consonant, final_consonant=prev.final_consonant, tone_marker=prev.tone_marker)
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

def remove_karan(array: list, remove_karan_phonemes: bool):
    result_array = []
    for i in range(len(array)):
        if array[i] != '໌' and (not remove_karan_phonemes or i + 1 >= len(array) or array[i + 1] != '໌'):
                result_array.append(array[i])
    return result_array

def is_beginning_consonant(lao_array):
    """
    Returns True if the character at index 0 is a beginning consonant (consonant followed by a vowel).
    """
    lao_array = remove_tone_markers(lao_array)
    possible_beginning = lao_array[0]
    if possible_beginning not in lao_consonant_assignments.keys():
        return False
    try:
        next_char = lao_array[1]
        if next_char in {"ວ","ອ"}:
            return lao_array[2] == "ຍ" or lao_array[2] not in lao_vowel_characters
        elif next_char == "ຍ" or next_char not in lao_vowel_characters:
            return False
        else:
            return True
    except IndexError:
        return False

    
def check_vowel_lists():
    for vowel in lao_vowel_assignments:
        short_vowel = vowel.rstrip(vowel[len(vowel) - 1])
        if short_vowel != "" and short_vowel not in lao_intermediate_vowel_states:
            print(short_vowel)
    
if __name__ == "__main__":
    user_input = ""
    while user_input != "quit":
        user_input = input("Phrase: ").replace("\u200b","")
        print(lao2ipa(user_input, 'ipa', False))
    
