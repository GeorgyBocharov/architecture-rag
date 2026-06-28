#!/usr/bin/env python3
"""
Script to copy files from smeshariki-fandom to knowledge_base with term replacement.
Uses terms_map.json for base terms and terms_series_map.json for series titles.

Replacement logic
------------------
* Single-word source -> single-word target:
  both words are declined (heuristic Russian noun morphology) and matched
  case-by-case, so "Кроша" -> "Джависта", "Крошем" -> "Джавистом", etc.
* Single-word source -> multi-word target (e.g. "дом" -> "рабочее место"):
  every inflected form of the SOURCE is mapped to the target's nominative
  form. No case endings are appended to the multi-word target, which avoids
  garbage like "рабочее местоа".
* Multi-word / hyphenated / quoted source (episode titles, "кар-карыч",
  "пин-код"): exact case-insensitive match, replacement preserved as-is.

Capitalization of the match is preserved: if the matched text starts with an
uppercase letter, the replacement's first letter is upper-cased too.
"""

import json
import re
from pathlib import Path

# Cyrillic/Latin word-boundary guards so we only replace whole words.
_BOUND_L = r'(?<![а-яА-ЯёЁA-Za-z])'
_BOUND_R = r'(?![а-яА-ЯёЁA-Za-z])'

# Consonants that take soft endings (-ем in instr., -ей in gen.pl., -и in nom.pl.)
_HUSH = ('ч', 'ш', 'щ', 'ж')
_VELAR = ('к', 'г', 'х')


def _masc(w: str) -> dict[str, str]:
    """Decline a masculine noun ending in a consonant."""
    soft = w.endswith(_HUSH) or w.endswith('ц')
    return {
        'nom': w,
        'gen': w + 'а', 'dat': w + 'у', 'acc': w + 'а',
        'ins': w + ('ем' if soft else 'ом'),
        'pre': w + 'е',
        'pl_nom': w + 'и',
        'pl_gen': w + ('ей' if w.endswith(_HUSH) else 'ов'),
        'pl_dat': w + 'ам', 'pl_ins': w + 'ами', 'pl_pre': w + 'ах',
    }


def _fem_a(w: str) -> dict[str, str]:
    """Decline a feminine noun ending in -а."""
    s = w[:-1]
    gen = s + ('и' if s.endswith(_VELAR + _HUSH) else 'ы')
    ins = s + ('ей' if s.endswith(_HUSH + ('ц',)) else 'ой')  # нюша -> нюшей, not нюшой
    return {
        'nom': w, 'gen': gen, 'dat': s + 'е', 'acc': s + 'у',
        'ins': ins, 'pre': s + 'е',
        'pl_nom': gen, 'pl_gen': s,
        'pl_dat': s + 'ам', 'pl_ins': s + 'ами', 'pl_pre': s + 'ах',
    }


def _fem_ya(w: str) -> dict[str, str]:
    """Decline a feminine noun ending in -я / -ья (e.g. совунья)."""
    s = w[:-1]
    return {
        'nom': w, 'gen': s + 'и', 'dat': s + 'е', 'acc': s + 'ю',
        'ins': s + 'ей', 'pre': s + 'е',
        'pl_nom': s + 'и', 'pl_gen': s,
        'pl_dat': s + 'ям', 'pl_ins': s + 'ями', 'pl_pre': s + 'ях',
    }


def _neut(w: str) -> dict[str, str]:
    """Decline a neuter noun ending in -о / -е."""
    s = w[:-1]
    return {
        'nom': w, 'gen': s + 'а', 'dat': s + 'у', 'acc': w,
        'ins': s + 'ом', 'pre': s + 'е',
        'pl_nom': s + 'а', 'pl_gen': s,
        'pl_dat': s + 'ам', 'pl_ins': s + 'ами', 'pl_pre': s + 'ах',
    }


def _pl_i(w: str) -> dict[str, str]:
    """Decline a plural noun ending in -и (e.g. смешарики)."""
    s = w[:-1]
    d = _masc(s)          # singular forms: смешарик, смешарика, ...
    d['nom'] = w          # plural nominative: смешарики
    d['pl_nom'] = w
    return d


def decline(word: str) -> dict[str, str]:
    """Return a {case_key: form} dict for a Russian noun (heuristic)."""
    w = word.lower()
    if w.endswith(('ья', 'я')):
        return _fem_ya(w)
    if w.endswith('а'):
        return _fem_a(w)
    if w.endswith(('о', 'е')):
        return _neut(w)
    if w.endswith('и'):
        return _pl_i(w)
    return _masc(w)


def possessives(word: str) -> list[str]:
    """Possessive-adjective forms of a feminine name (нюша -> нюшин, нюшина, ...).

    Russian forms a possessive adjective from a name (Нюшин утюг = "Nyusha's
    iron"); these are not noun cases so they are handled separately. Only
    feminine -а / -я names are covered, which is where the corpus needs it.
    """
    w = word.lower()
    if w.endswith(('а', 'я')):
        base = w[:-1] + 'ин'
    else:
        return []
    endings = ['', 'а', 'о', 'ы', 'ым', 'ой', 'ого', 'ому', 'ом', 'ыми', 'ых', 'у']
    return [base + e for e in endings]


def _cap_repl(replacement: str):
    """Build a re.sub callback that mirrors the match's leading capitalization."""
    def fn(m: re.Match) -> str:
        matched = m.group(0)
        if matched[:1].isupper():
            return replacement[:1].upper() + replacement[1:]
        return replacement
    return fn


def load_mapping(*mapping_paths) -> dict[str, str]:
    """Load and merge term mappings from multiple JSON files."""
    combined: dict[str, str] = {}
    for path in mapping_paths:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                mapping = json.load(f).get('mapping', {})
                combined.update(mapping)
                print(f"  Loaded {len(mapping)} mappings from {path}")
        except FileNotFoundError:
            print(f"  Warning: {path} not found, skipping...")
    return combined


def build_replacement_patterns(mapping: dict[str, str]) -> list[tuple[re.Pattern, object]]:
    """Build (compiled_pattern, replacement) tuples, longest match first."""
    # Collect candidate (matchable_string, is_exact, replacement) triples,
    # de-duplicated by (is_exact, matchable_string) keeping the longest source.
    candidates: dict[tuple[bool, str], str] = {}

    def add(form: str, repl: str, exact: bool):
        # First write wins: source cases are added nominative-first, so when two
        # cases collapse to the same surface form (neuter nom==prep, plural nom),
        # the nominative replacement is kept instead of a declined one.
        if len(form) < 2:
            return
        candidates.setdefault((exact, form), repl)

    for original, replacement in mapping.items():
        o = original.lower()
        is_phrase = '«' in original or original.startswith('"') or ' ' in o or '-' in o

        if is_phrase:
            # Exact match for titles / hyphenated / quoted terms.
            add(original, replacement, exact=True)
            continue

        src = decline(o)
        if ' ' in replacement or '-' in replacement:
            # Multi-word target: map every source form to the target as given.
            for form in set(src.values()):
                add(form, replacement.lower(), exact=False)
            for form in possessives(o):
                add(form, replacement.lower(), exact=False)
        else:
            # Single-word target: decline both, align by grammatical case.
            tgt = decline(replacement.lower())
            for case, form in src.items():
                add(form, tgt.get(case, tgt['nom']), exact=False)
            # Possessive of the name -> genitive of the target ("X's" ≈ "of X").
            for form in possessives(o):
                add(form, tgt.get('gen', tgt['nom']), exact=False)

    # Longest matchable string first to avoid partial replacements.
    ordered = sorted(candidates.items(), key=lambda kv: len(kv[0][1]), reverse=True)

    patterns: list[tuple[re.Pattern, object]] = []
    for (exact, form), repl in ordered:
        if exact:
            pattern = re.compile(re.escape(form), re.IGNORECASE)
        else:
            pattern = re.compile(_BOUND_L + re.escape(form) + _BOUND_R, re.IGNORECASE)
        patterns.append((pattern, _cap_repl(repl)))
    return patterns


def replace_terms(text: str, patterns: list[tuple[re.Pattern, object]]) -> str:
    """Replace all terms in text using the compiled patterns."""
    for pattern, replacement in patterns:
        text = pattern.sub(replacement, text)
    return text


def process_files(source_dir: str, dest_dir: str, *mapping_paths):
    """Process all markdown files from source to destination with replacement."""
    mapping = load_mapping(*mapping_paths)
    print(f"\nTotal: {len(mapping)} term mappings loaded")

    patterns = build_replacement_patterns(mapping)
    print(f"Built {len(patterns)} replacement patterns")

    Path(dest_dir).mkdir(parents=True, exist_ok=True)
    md_files = list(Path(source_dir).glob('*.md'))
    print(f"Found {len(md_files)} markdown files to process\n")

    for src_file in md_files:
        content = src_file.read_text(encoding='utf-8')
        new_content = replace_terms(content, patterns)
        new_filename = replace_terms(src_file.name, patterns)

        (Path(dest_dir) / new_filename).write_text(new_content, encoding='utf-8')
        print(f"  {src_file.name} -> {new_filename}")

    print(f"\n✅ Processed {len(md_files)} files successfully!")


if __name__ == '__main__':
    SOURCE_DIR = 'smeshariki-fandom'
    DEST_DIR = 'knowledge_base'
    BASE_MAPPING = 'terms_map.json'
    SERIES_MAPPING = 'terms_series_map.json'

    process_files(SOURCE_DIR, DEST_DIR, BASE_MAPPING, SERIES_MAPPING)
