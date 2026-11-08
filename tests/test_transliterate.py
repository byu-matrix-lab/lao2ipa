import os
import csv

from lao2ipa import transliterate, remove_karan, merge_double_consonants, split_syllables


def test_basic_consonant_mapping():
    out = transliterate('ກ', 'ipa')
    assert out != ''
    assert out.startswith('k')


def test_long_vowel_includes_vowel_symbol_and_tone():
    out = transliterate('ກາ', 'ipa')
    assert 'aː' in out
    assert any(t in out for t in ['˦', '˥', '˨', '˧', '˩'])


def test_repeater_duplicates_previous_syllable():
    a = transliterate('ກາໆ', 'ipa')
    b = transliterate('ກາກາ', 'ipa')
    assert a == b


def test_remove_karan_removes_previous_consonant_when_flag_true():
    arr = ['ກ','໌','າ']
    assert remove_karan(arr, remove_karan_phonemes=True) == ['າ']
    assert remove_karan(arr, remove_karan_phonemes=False) == ['ກ','າ']


def test_preposed_vowel_swap_equivalence():
    # preposed vowel should be re-ordered so transliteration equals the reordered form
    assert transliterate('ເກ', 'ipa') == transliterate('ກເ', 'ipa')


def test_merge_double_consonant_digraph_equivalence():
    # digraph ຫມ should behave like ມ for initial mapping
    assert transliterate('ຫມາ', 'ipa') == transliterate('ໝາ', 'ipa')


def test_missing_loanword_onsets_are_merged():
    # ສຣ is a valid loanword onset and should be treated as one cluster
    assert 'ສຣ' in merge_double_consonants(list('ສຣີລັງກາ'))
    # ຫວ and ຄວ are valid onsets in native words
    assert 'ຫວ' in merge_double_consonants(list('ປະຫວັດ'))
    assert 'ຄວ' in merge_double_consonants(list('ຄວາມ'))


def test_cluster_merging_does_not_consume_vocalic_wa():
    # ວ is the syllable nucleus (or a final), not a glide, in these words
    for word in ['ສວນ', 'ຊວງ', 'ສວຍ']:
        tokens = merge_double_consonants(list(word))
        assert 'ສວ' not in tokens and 'ຊວ' not in tokens


def test_wa_is_long_vowel_before_final_or_open_syllable():
    assert transliterate('ຄວາມ', 'ipa').startswith('kʰuːəm')
    assert transliterate('ກວາງ', 'ipa').startswith('kuːəŋ')
    assert transliterate('ຂວດ', 'ipa').startswith('kʰuːət')
    assert transliterate('ຄວນ', 'ipa').startswith('kʰuːən')
    assert transliterate('ສວນ', 'ipa').startswith('suːən')
    assert transliterate('ຊວງ', 'ipa').startswith('suːəŋ')


def test_wa_is_labialization_before_front_vowel():
    assert transliterate('ຄວັນ', 'ipa').startswith('kʷʰan')
    assert transliterate('ຄວີນ', 'ipa').startswith('kʷʰiːn')
    assert transliterate('ແຂວງ', 'ipa').startswith('kʷʰɛːŋ')
    assert transliterate('ກວຽນ', 'ipa').startswith('kʷiːən')


def test_wa_cluster_does_not_cross_syllable_boundary():
    out = transliterate('ນັກວິທະຍາສາດ', 'ipa')
    assert 'kʷi' not in out
    assert 'ʋi' in out
    out = transliterate('ພາກວິຊາ', 'ipa')
    assert 'kʷi' not in out
    assert 'ʋi' in out


def test_ya_variant_after_vowel_is_final_j():
    assert transliterate('ມວຽ', 'ipa').startswith('muːəj')
    assert transliterate('ກ້ວຽ', 'ipa').startswith('kuːəj')
    assert 'moːj' in transliterate('ກະໂມຽ', 'ipa')
    assert 'baːj' in transliterate('ສະບາຽ', 'ipa')
    assert transliterate('ຫຼາຽ', 'ipa').startswith('laːj')
    assert 'haːj' in transliterate('ຜູ້ຮ້າຽ', 'ipa')


def test_ya_vowel_is_kept_after_onset():
    assert transliterate('ວຽງ', 'ipa').startswith('ʋiːə')
    assert transliterate('ວຽກ', 'ipa').startswith('ʋiːə')
    assert transliterate('ກ່ຽວ', 'ipa').startswith('kiːə')
    assert transliterate('ຂຽນ', 'ipa').startswith('kʰiːə')
    assert transliterate('ສຽງ', 'ipa').startswith('siːə')


def test_ipa_output_has_no_r():
    for word in ['ຣົຖ', 'ພຣະ', 'ອາຟຣິກກາ', 'ບໍຣິການ']:
        assert 'r' not in transliterate(word, 'ipa')


def test_final_l_is_realized_as_n():
    assert 'mɛːn' in transliterate('ອີແມລ', 'ipa')


def test_initial_o_with_tone_before_vowel():
    assert transliterate('ອ່ອນ', 'ipa') == 'ɔːn˧'
    assert transliterate('ອ້ອຍ', 'ipa') == 'ɔːj˥˨'
    assert transliterate('ອ່ວຍ', 'ipa') == 'uːəj˧'


def test_initial_ya_with_tone_before_vowel():
    assert transliterate('ຍ່ອງ', 'ipa') == 'ɲɔːŋ˧'


def test_karan_can_silence_the_preceding_consonant():
    assert transliterate('ໄຟລ໌', 'ipa', remove_karan_phonemes=True) == 'faj˧˥'


def test_loanword_clusters_do_not_cross_syllables():
    assert 'lop' in transliterate('ລົບລ້າງ', 'ipa')
    assert 'blaːŋ' not in transliterate('ລົບລ້າງ', 'ipa')
    assert 'beː' in transliterate('ຊີເບລີ', 'ipa')
    assert 'bl' not in transliterate('ຊີເບລີ', 'ipa')
    assert 'oːt' in transliterate('ໂອຕຣິດ', 'ipa')
    assert 'tlit' not in transliterate('ໂອຕຣິດ', 'ipa')


def test_checked_finals_use_dead_syllable_tones():
    assert transliterate('ຣົຖ', 'ipa') == 'lot˧'
    assert transliterate('ເທປ', 'ipa') == 'tʰeːp˥˨'
    assert transliterate('ເບັຽ', 'ipa') == 'biːə˩˧'
    assert transliterate('ສັຕວ໌', 'ipa', remove_karan_phonemes=True) == 'sat˧˥'


def test_reordered_wa_after_short_vowel():
    assert transliterate('ຄັວນ', 'ipa') == 'kʷʰan˧˥'


def test_lone_s_before_another_syllable_is_sa():
    assert transliterate('ສນາມບິນ', 'ipa').startswith('sa˧˥naːm')
    assert transliterate('ສຍາມ', 'ipa').startswith('sa˧˥ɲaːm')


def test_short_ya_vowel_after_e():
    assert transliterate('ເຂັ່ຍ', 'ipa') == 'kʰiə˧'


def test_pra_after_short_e_splits():
    out = transliterate('ໂອເປຣາ', 'ipa')
    assert 'peː' in out and 'laː' in out
    assert 'pleː' not in out


def test_issue_cluster_syllable_boundaries():
    boundaries = {
        'ສຣີລັງກາ': ['ສຣີ', 'ລັງ', 'ກາ'],
        'ເທັກໂນ': ['ເທັກ', 'ໂນ'],
        'ປະຫວັດ': ['ປະ', 'ຫວັດ'],
    }
    for word, parts in boundaries.items():
        assert transliterate(word, 'ipa') == ''.join(
            transliterate(part, 'ipa') for part in parts
        )


def test_split_syllables_issue_words():
    expected = {
        'ສຣີລັງກາ': ['ສຣີ', 'ລັງ', 'ກາ'],
        'ເທັກໂນ': ['ເທັກ', 'ໂນ'],
        'ປະຫວັດ': ['ປະ', 'ຫວັດ'],
        'ຄວາມ': ['ຄວາມ'],
        'ຂະບວນ': ['ຂະ', 'ບວນ'],
        'ຄຳນວນ': ['ຄຳ', 'ນວນ'],
        'ສຳນຽງ': ['ສຳ', 'ນຽງ'],
        'ລະບຽບ': ['ລະ', 'ບຽບ'],
        'ຄາວຽກ': ['ຄາ', 'ວຽກ'],
        'ໄຊຍະບູລີ': ['ໄຊ', 'ຍະ', 'ບູ', 'ລີ'],
    }
    for word, parts in expected.items():
        assert split_syllables(word) == parts


def test_split_syllables_keeps_separators_and_expands_repeater():
    assert split_syllables('ພາສາລາວ, ດີ!') == [
        'ພາ', 'ສາ', 'ລາວ', ',', 'ດີ', '!'
    ]
    assert split_syllables('ຊ້າໆ') == ['ຊ້າ', 'ຊ້າ']


def test_standalone_preposed_vowel_with_wa_is_a_consonant():
    assert split_syllables('ເວັນ') == ['ເວັນ']
    assert transliterate('ເວັນ', 'ipa').startswith('ʋ')


def test_transliterate_matches_per_syllable_transliteration():
    for word in ['ສຣີລັງກາ', 'ເທັກໂນ', 'ປະຫວັດ', 'ໄຊຍະບູລີ']:
        parts = split_syllables(word)
        assert transliterate(word, 'ipa') == ''.join(
            transliterate(part, 'ipa') for part in parts
        )


def test_moh_vs_ipa_different_outputs():
    ipa = transliterate('ກາ', 'ipa')
    moh = transliterate('ກາ', 'moh')
    assert ipa != moh


def test_numerals_and_abbreviation_handling():
    # abbreviation sign 'ຯ' should be removed; Lao numerals converted to ASCII
    out = transliterate('ສະບາຍດີຯ໑', 'ipa')
    assert '1' in out
    assert 'ຯ' not in out


def test_multi_syllable_phrase_returns_string():
    out = transliterate('ສະບາຍດີ', 'ipa')
    assert isinstance(out, str)
    assert len(out) > 0


def test_authoritative_ipa_vectors_from_wiktionary():
    # Authoritative Vientiane IPA strings sourced from Wiktionary (square brackets removed)
    expected = {
        'ສະບາຍດີ': 'sa(ʔ˧˥).baːj˩(˧).diː˩(˧)',
        'ໄມ້': 'maj˥˨',
        'ເມືອງ': 'mɯːəŋ˧˥',
        'ສີ': 'siː˩(˧)',
        'ຍິງ': 'ɲiŋ˧˥',
        'ບໍ່': 'bɔː˧',
        'ເປັນ': 'pen˩(˧)',
        'ແມ່': 'mɛː˧',
        'ເຮັດ': 'het˧',
        'ຊາ': 'saː˧˥',
        'ພຣະ': 'pʰlaʔ˧',
        'ຄວາມ': 'kʰuːəm˧˥',
        'ກາ': 'kaː˩(˧)',
        'ຮູບ': 'huːp˥˨',
        'ຫວັງ': 'ʋaŋ˩(˧)',
        'ຫຍັງ': 'ɲaŋ˩(˧)',
        'ດີ': 'diː˩(˧)'
    }

    def _normalize_for_test(s: str) -> str:
        # remove parentheses, punctuation, glottal stop, unreleased-stop diacritic, and spaces
        import re
        # remove parentheses, dots, commas, semicolons, colons, question/exclaim, quotes, hyphens
        s = re.sub(r"[\\/\(\)\.,;:\?!\"'\-]", '', s)
        # remove IPA glottal stop and unreleased stop diacritic
        s = s.replace('ʔ', '')
        s = s.replace('\u031A', '')
        # remove tie-bar used for affricates (e.g. 't͡ɕ' -> 'tɕ')
        s = s.replace('\u0361', '')
        # remove combining mark under schwa (e.g. 'ə̯' -> 'ə')
        s = s.replace('\u032F', '')
        # remove spaces and dots
        s = s.replace(' ', '')
        s = s.replace('.', '')
        return s

    # load vectors harvested from Wiktionary CSV (if present)
    wiktionary_expected = {}
    repo_root = os.path.dirname(os.path.dirname(__file__))
    csv_path = os.path.join(repo_root, 'tests', 'wiktionary_vectors.csv')
    if os.path.exists(csv_path):
        with open(csv_path, newline='', encoding='utf-8') as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                if row.get('note', '').strip():
                    continue
                lao = row.get('lao_in', '').strip()
                ipa = row.get('ipa_out', '').strip()
                if lao.startswith("'") and lao.endswith("'"):
                    lao = lao[1:-1]
                if ipa.startswith("'") and ipa.endswith("'"):
                    ipa = ipa[1:-1]
                if lao:
                    wiktionary_expected[lao] = ipa

    # merge hard-coded expected with vectors fetched from Wiktionary
    combined_expected = {**expected, **wiktionary_expected}
    mismatches = []
    for lao_word, wiki_ipa in combined_expected.items():
        out = transliterate(
            lao_word,
            'ipa',
            remove_karan_phonemes='໌' in lao_word,
        )
        out_norm = _normalize_for_test(out)
        # Lao has no /r/; Wiktionary sometimes keeps 'r' in loanwords and
        # obsolete spellings, so compare against the expected /l/ realization.
        expected_norm = _normalize_for_test(wiki_ipa).replace('r', 'l')
        if out_norm != expected_norm:
            mismatches.append((lao_word, wiki_ipa, out, expected_norm, out_norm))

    details = [
        f"{w}: expected {exp!r} (norm {exp_norm!r}), got {got!r} (norm {got_norm!r})"
        for w, exp, got, exp_norm, got_norm in mismatches
    ]
    assert not mismatches, (
        f"Mismatches: {len(mismatches)}\n" + "\n".join(details)
    )
