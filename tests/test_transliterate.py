import sys
import os

# ensure src is on path
repo_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(repo_root, 'src'))

from transliterate import lao_to_ipa_ref as ref


def test_basic_consonant_mapping():
    out = ref.lao2ipa('ກ', 'ipa')
    assert out != ''
    assert out.startswith('k')


def test_long_vowel_includes_vowel_symbol_and_tone():
    out = ref.lao2ipa('ກາ', 'ipa')
    assert 'aː' in out
    assert any(t in out for t in ['˦', '˥', '˨', '˧', '˩'])


def test_repeater_duplicates_previous_syllable():
    a = ref.lao2ipa('ກາໆ', 'ipa')
    b = ref.lao2ipa('ກາກາ', 'ipa')
    assert a == b


def test_remove_karan_removes_previous_consonant_when_flag_true():
    arr = ['ກ','໌','າ']
    assert ref.remove_karan(arr, remove_karan_phonemes=True) == ['າ']
    assert ref.remove_karan(arr, remove_karan_phonemes=False) == ['ກ','າ']


def test_preposed_vowel_swap_equivalence():
    # preposed vowel should be re-ordered so transliteration equals the reordered form
    assert ref.lao2ipa('ເກ', 'ipa') == ref.lao2ipa('ກເ', 'ipa')


def test_merge_double_consonant_digraph_equivalence():
    # digraph ຫມ should behave like ມ for initial mapping
    assert ref.lao2ipa('ຫມາ', 'ipa') == ref.lao2ipa('ໝາ', 'ipa')


def test_moh_vs_ipa_different_outputs():
    ipa = ref.lao2ipa('ກາ', 'ipa')
    moh = ref.lao2ipa('ກາ', 'moh')
    assert ipa != moh


def test_numerals_and_abbreviation_handling():
    # abbreviation sign 'ຯ' should be removed; Lao numerals converted to ASCII
    out = ref.lao2ipa('ສະບາຍດີຯ໑', 'ipa')
    assert '1' in out
    assert 'ຯ' not in out


def test_multi_syllable_phrase_returns_string():
    out = ref.lao2ipa('ສະບາຍດີ', 'ipa')
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
        'ພຣະ': 'pʰraʔ˧',
        'ຄວາມ': 'kʰuːəm˧˥',
        'ກາ': 'kaː˩(˧)',
        'ຮູບ': 'huːp˥˨',
        'ຫວັງ': 'ʋaŋ˩(˧)',
        'ຫຍັງ': 'ɲaŋ˩(˧)',
        'ດີ': 'diː˩(˧)'
    }

    def _normalize_for_test(s: str) -> str:
        # remove parentheses, glottal stop, dots and tone diacritics for loose matching
        for ch in ['(',')','.', 'ʔ', ' ']:
            s = s.replace(ch, '')
        return s

    for lao_word, wiki_ipa in expected.items():
        out = ref.lao2ipa(lao_word, 'ipa')
        assert _normalize_for_test(out) == _normalize_for_test(wiki_ipa), f"{lao_word}: expected {wiki_ipa!r}, got {out!r}"
