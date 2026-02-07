import sys
import os
import csv

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
    csv_path = os.path.join(repo_root, 'tests', 'wiktionary_vectors.csv')
    if os.path.exists(csv_path):
        with open(csv_path, newline='', encoding='utf-8') as fh:
            reader = csv.DictReader(fh)
            for row in reader:
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
    for lao_word, wiki_ipa in combined_expected.items():
        out = ref.lao2ipa(lao_word, 'ipa')
        out_norm = out
        expected_norm = _normalize_for_test(wiki_ipa)
        assert out_norm == expected_norm, f"{lao_word}: expected {wiki_ipa!r} (norm {expected_norm!r}), got {out!r} (norm {out_norm!r})"
