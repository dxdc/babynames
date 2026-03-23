"""Tests for phonetic helper functions."""

import pytest
import src.babynames as babynames_mod
from src.babynames import (
    _VALID_ARPABET,
    count_syllables,
    estimate_syllables_from_spelling,
    extract_stress_pattern,
    get_grouping_pronunciations,
    get_pronunciations,
    get_stress_patterns,
    get_syllable_count,
    has_initial_phoneme_repeat,
    has_repeated_phoneme,
    load_pronunciation_overrides,
    split_into_subwords,
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

    def test_empty_pronunciation_list(self) -> None:
        assert not has_repeated_phoneme([])
        assert not has_initial_phoneme_repeat([])


class TestSplitIntoSubwords:
    def test_known_word(self) -> None:
        # "john" is in CMU dict — should return directly
        result = split_into_subwords("john")
        assert len(result) >= 1

    def test_unknown_word_splits(self) -> None:
        # A compound name that can be split into known parts
        result = split_into_subwords("sunfire")
        assert isinstance(result, list)

    def test_completely_unknown(self) -> None:
        result = split_into_subwords("zzzzz")
        assert result == []

    def test_min_subword_length(self) -> None:
        # Single-char splits should be avoided
        result = split_into_subwords("ax")
        # "a" + "x" would be too short — ensure no garbage splits
        assert isinstance(result, list)


class TestEstimateSyllablesFromSpelling:
    def test_single_syllable(self) -> None:
        assert estimate_syllables_from_spelling("Kate") == 1

    def test_two_syllables(self) -> None:
        assert estimate_syllables_from_spelling("Mary") == 2

    def test_three_syllables(self) -> None:
        assert estimate_syllables_from_spelling("Danielle") == 3  # -ielle has 2 vowel groups

    def test_consonant_le(self) -> None:
        assert estimate_syllables_from_spelling("Maple") == 2

    def test_minimum_one(self) -> None:
        # Even weird inputs should return at least 1
        assert estimate_syllables_from_spelling("Brn") == 1

    def test_ie_ending_not_silent(self) -> None:
        # "ie" ending is exempt from silent-e rule, counts as 2 syllables
        assert estimate_syllables_from_spelling("Marie") == 2

    def test_short_names(self) -> None:
        assert estimate_syllables_from_spelling("Al") == 1
        assert estimate_syllables_from_spelling("Jo") == 1
        assert estimate_syllables_from_spelling("Ed") == 1


class TestPronunciationOverrides:
    @pytest.fixture(autouse=True)
    def _reset_overrides(self):
        original = babynames_mod._pronunciation_overrides.copy()
        yield
        babynames_mod._pronunciation_overrides = original

    def test_override_takes_precedence(self, pronunciation_overrides_path) -> None:
        load_pronunciation_overrides(pronunciation_overrides_path)
        prons = get_pronunciations("Jere")
        assert prons == ["JH IH1 R"]

    def test_override_in_grouping(self, pronunciation_overrides_path) -> None:
        load_pronunciation_overrides(pronunciation_overrides_path)
        prons = get_grouping_pronunciations("Jere")
        assert prons == ["JH IH1 R"]

    def test_non_overridden_unchanged(self, pronunciation_overrides_path) -> None:
        load_pronunciation_overrides(pronunciation_overrides_path)
        prons = get_pronunciations("John")
        # John should still come from CMU dict
        assert len(prons) >= 1
        assert any("JH" in p for p in prons)

    def test_invalid_arpabet_warns(self, tmp_path, caplog) -> None:
        import logging

        bad = tmp_path / "bad_overrides.csv"
        bad.write_text("name,pronunciation\ntest,FAKE99 PHONEME\n")
        with caplog.at_level(logging.WARNING):
            load_pronunciation_overrides(bad)
        assert any("unknown ARPABET phoneme" in r.message for r in caplog.records)


class TestG2pFallback:
    def test_subword_fallback_without_g2p(self) -> None:
        """When g2p_en is unavailable, get_pronunciations should still work via subwords."""
        original = babynames_mod._g2p_model
        try:
            babynames_mod._g2p_model = None
            # "Sunfire" is not in CMU dict but can be split into "sun" + "fire"
            prons = get_pronunciations("Sunfire")
            assert isinstance(prons, list)
            # Should get at least one pronunciation from subword splitting
            assert len(prons) >= 1
        finally:
            babynames_mod._g2p_model = original


class TestValidArpabetSet:
    def test_common_phonemes_present(self) -> None:
        for phoneme in ["AA0", "AA1", "AH0", "B", "CH", "D", "EH1", "IY0", "K", "M", "N", "R"]:
            assert phoneme in _VALID_ARPABET, f"{phoneme} should be in valid ARPABET set"

    def test_set_nonempty(self) -> None:
        assert len(_VALID_ARPABET) > 30
