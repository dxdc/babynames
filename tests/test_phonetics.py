"""Tests for phonetic helper functions."""

from src.babynames import (
    count_syllables,
    extract_stress_pattern,
    get_pronunciations,
    get_stress_patterns,
    get_syllable_count,
    has_initial_phoneme_repeat,
    has_repeated_phoneme,
)


class TestGetPronunciations:
    def test_common_name(self) -> None:
        pronunciations = get_pronunciations("Mary")
        assert len(pronunciations) >= 1
        assert all(isinstance(p, str) for p in pronunciations)
        assert any("M" in p for p in pronunciations)

    def test_compound_name_fallback(self) -> None:
        pronunciations = get_pronunciations("Zzyzx")
        assert isinstance(pronunciations, list)

    def test_john(self) -> None:
        pronunciations = get_pronunciations("John")
        assert len(pronunciations) >= 1
        assert any("JH" in p for p in pronunciations)

    def test_case_insensitive(self) -> None:
        assert get_pronunciations("MARY") == get_pronunciations("mary")


class TestStressPatterns:
    def test_monosyllabic(self) -> None:
        assert extract_stress_pattern("JH AA1 N") == "1"

    def test_disyllabic(self) -> None:
        assert extract_stress_pattern("M EH1 R IY0") == "10"

    def test_empty(self) -> None:
        assert extract_stress_pattern("") == ""

    def test_multiple_pronunciations(self) -> None:
        patterns = get_stress_patterns(["JH AA1 N", "M EH1 R IY0"])
        assert patterns == ["1", "10"]


class TestSyllableCounting:
    def test_monosyllabic(self) -> None:
        assert count_syllables("JH AA1 N") == 1

    def test_disyllabic(self) -> None:
        assert count_syllables("M EH1 R IY0") == 2

    def test_empty(self) -> None:
        assert count_syllables("") == 0

    def test_average_across_pronunciations(self) -> None:
        assert get_syllable_count(["M EH1 R IY0", "M AA1 R IY0"]) == 2

    def test_empty_list(self) -> None:
        assert get_syllable_count([]) == 0


class TestAlliteration:
    def test_no_repeated_phoneme(self) -> None:
        assert not has_repeated_phoneme(["JH AA1 N"])

    def test_repeated_phoneme(self) -> None:
        assert has_repeated_phoneme(["B AE1 B"])

    def test_initial_repeat(self) -> None:
        assert has_initial_phoneme_repeat(["B AE1 B"])

    def test_no_initial_repeat(self) -> None:
        assert not has_initial_phoneme_repeat(["JH AA1 N"])
