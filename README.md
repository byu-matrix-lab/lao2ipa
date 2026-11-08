# lao2ipa

[![Tests](https://github.com/byu-matrix-lab/lao2ipa/actions/workflows/tests.yml/badge.svg)](https://github.com/byu-matrix-lab/lao2ipa/actions/workflows/tests.yml)

Lightweight rule-based Lao → IPA transliteration utilities.

This package tokenizes Lao text into orthographic units, groups characters into syllables, applies tone-placement heuristics, and renders IPA transliterations (with optional alternate outputs).

## Quickstart

Install (from PyPI):

```bash
pip install lao2ipa
```

Install (from source):

```bash
pip install -e .
```

Basic usage (Python):

```python
from lao2ipa import transliterate

print(transliterate('ສະບາຍດີ'))  # example output: IPA transliteration
```

Function signature:
- `transliterate(lao_source: str, output: str = 'ipa', ignore_tones: bool = False, remove_karan_phonemes: bool = False)`

Output keys (valid `output` values):
- `ipa` — Unicode IPA transliteration (default)
- `moh` — Ministry of Health (MoH 2020) romanization mapping

## Development

Requires Python >=3.10.

Install development dependencies and run the test suite:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

CI runs the same tests on Python 3.10–3.14 via
`.github/workflows/tests.yml`.

### Test data

`tests/wiktionary_vectors.csv` contains Lao/IPA pairs with the columns
`lao_in`, `ipa_out`, and `note`. Rows with a non-empty `note` are known
exceptions (Wiktionary quirks, obsolete spellings, etc.) and are ignored by
the authoritative-vector test.

## Contributing

Please open an issue or PR if you find incorrect mappings or wish to
improve heuristics (tone assignment and vowel clusters are the most
likely areas to require refinement).

## License

See the `LICENSE` file in the repository root.

