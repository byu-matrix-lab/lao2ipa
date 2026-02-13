# lao2ipa

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

- Run tests with `pytest -q`.
- Code lives in `src/lao2ipa.py`.

## Contributing

Please open an issue or PR if you find incorrect mappings or wish to
improve heuristics (tone assignment and vowel clusters are the most
likely areas to require refinement).

## License

See the `LICENSE` file in the repository root.

