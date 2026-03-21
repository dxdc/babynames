"""Tests for phonetic helper functions."""

from src.babynames import (
    alliteration_in_word,
    alliteration_in_word_first_letter,
    phones_in_word,
    stresses_in_word,
    syllable_count,
    syllables_in_word,
)


class TestPhonesInWord:
    def test_common_name(self):
        phones = phones_in_word("Mary")
        assert len(phones) >= 1
        assert all(isinstance(p, str) for p in phones)
        # Mary should have phonemes
        assert any("M" in p for p in phones)

    def test_unknown_name_wordbreak(self):
        # A name that might not be in CMU dict directly
        phones = phones_in_word("Zzyzx")
        # Should return a list (possibly empty for very unusual words)
        assert isinstance(phones, list)

    def test_john(self):
        phones = phones_in_word("John")
        assert len(phones) >= 1
        assert any("JH" in p for p in phones)

    def test_case_insensitive(self):
        phones_upper = phones_in_word("MARY")
        phones_lower = phones_in_word("mary")
        assert phones_upper == phones_lower


class TestStressesInWord:
    def test_monosyllabic(self):
        phones = ["JH AA1 N"]  # John
        stresses = stresses_in_word(phones)
        assert stresses == ["1"]

    def test_multisyllabic(self):
        phones = ["M EH1 R IY0"]  # Mary
        stresses = stresses_in_word(phones)
        assert stresses == ["10"]

    def test_empty(self):
        assert stresses_in_word([]) == []


class TestSyllableCount:
    def test_monosyllabic(self):
        assert syllable_count("JH AA1 N") == 1

    def test_disyllabic(self):
        assert syllable_count("M EH1 R IY0") == 2

    def test_empty(self):
        assert syllable_count("") == 0


class TestSyllablesInWord:
    def test_monosyllabic(self):
        assert syllables_in_word(["JH AA1 N"]) == 1

    def test_disyllabic(self):
        assert syllables_in_word(["M EH1 R IY0"]) == 2

    def test_empty(self):
        assert syllables_in_word([]) == 0

    def test_multiple_pronunciations(self):
        # Average of pronunciations
        result = syllables_in_word(["M EH1 R IY0", "M AA1 R IY0"])
        assert result == 2


class TestAlliteration:
    def test_no_alliteration(self):
        assert alliteration_in_word(["JH AA1 N"]) is None

    def test_alliteration(self):
        # A phone where some element repeats
        assert alliteration_in_word(["B AE1 B"]) == 1

    def test_first_letter_alliteration(self):
        # First phoneme repeats
        assert alliteration_in_word_first_letter(["B AE1 B"]) == 2

    def test_first_letter_no_alliteration(self):
        assert alliteration_in_word_first_letter(["JH AA1 N"]) is None
