"""Tests for the data pipeline stages."""

import polars as pl
import pytest

from src.babynames import (
    add_palindromes,
    aggregate_by_name,
    build_alt_spellings,
    classify_unisex,
    compute_features,
    compute_popular_years,
    extract_phonetics,
    load_biblical_names,
    load_ssa_data,
)


class TestLoadSSAData:
    def test_loads_files(self, ssa_dir):
        df = load_ssa_data(ssa_dir)
        assert df.height > 0
        assert set(df.columns) == {"name", "sex", "n", "year"}

    def test_has_expected_names(self, ssa_dir):
        df = load_ssa_data(ssa_dir)
        names = df["name"].unique().to_list()
        assert "Liam" in names
        assert "Olivia" in names

    def test_has_both_years(self, ssa_dir):
        df = load_ssa_data(ssa_dir)
        years = df["year"].unique().sort().to_list()
        assert years == [2020, 2021]

    def test_missing_dir_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_ssa_data(tmp_path / "nonexistent")


class TestLoadBiblicalNames:
    def test_loads(self, biblical_path):
        df = load_biblical_names(biblical_path)
        assert "name" in df.columns
        assert "biblical" in df.columns
        assert df.height > 0

    def test_has_expected_names(self, biblical_path):
        df = load_biblical_names(biblical_path)
        names = df["name"].to_list()
        assert "John" in names
        assert "Mary" in names


class TestComputePopularYears:
    def test_returns_year_pop(self, ssa_dir):
        df = load_ssa_data(ssa_dir)
        popular = compute_popular_years(df)
        assert "year_pop" in popular.columns
        # Liam's most popular year should be 2021 (higher count)
        liam = popular.filter(
            (pl.col("name") == "Liam") & (pl.col("sex") == "M")
        )
        assert liam["year_pop"][0] == 2021


class TestAggregateByName:
    def test_aggregation(self, ssa_dir):
        df = load_ssa_data(ssa_dir)
        agg = aggregate_by_name(df)
        assert "n_sum" in agg.columns
        assert "year_min" in agg.columns
        assert "year_max" in agg.columns

        # Liam across 2020+2021
        liam = agg.filter((pl.col("name") == "Liam") & (pl.col("sex") == "M"))
        assert liam["n_sum"][0] == 19659 + 20272
        assert liam["year_min"][0] == 2020
        assert liam["year_max"][0] == 2021

    def test_sorted_by_count_desc(self, ssa_dir):
        df = load_ssa_data(ssa_dir)
        agg = aggregate_by_name(df)
        boys = agg.filter(pl.col("sex") == "M")
        counts = boys["n_sum"].to_list()
        assert counts == sorted(counts, reverse=True)


class TestExtractPhonetics:
    def test_adds_phones_column(self, ssa_dir):
        df = load_ssa_data(ssa_dir)
        agg = aggregate_by_name(df)
        result = extract_phonetics(agg)
        assert "phones" in result.columns

    def test_john_has_phonetics(self, ssa_dir):
        df = load_ssa_data(ssa_dir)
        agg = aggregate_by_name(df)
        result = extract_phonetics(agg)
        john = result.filter(pl.col("name") == "John")
        phones = john["phones"][0]
        assert len(phones) > 0


class TestBuildAltSpellings:
    def test_john_jon_are_alternates(self, ssa_dir):
        df = load_ssa_data(ssa_dir)
        agg = aggregate_by_name(df)
        phonetic = extract_phonetics(agg)
        result = build_alt_spellings(phonetic)
        john = result.filter((pl.col("name") == "John") & (pl.col("sex") == "M"))
        alts = john["alt_spellings"][0]
        assert "Jon" in alts


class TestAddPalindromes:
    def test_hannah_is_palindrome(self, ssa_dir):
        df = load_ssa_data(ssa_dir)
        agg = aggregate_by_name(df)
        result = add_palindromes(agg)
        hannah = result.filter(pl.col("name") == "Hannah")
        assert hannah["palindrome"][0] == 1

    def test_john_not_palindrome(self, ssa_dir):
        df = load_ssa_data(ssa_dir)
        agg = aggregate_by_name(df)
        result = add_palindromes(agg)
        john = result.filter((pl.col("name") == "John") & (pl.col("sex") == "M"))
        assert john["palindrome"][0] is None


class TestClassifyUnisex:
    def test_jordan_is_unisex(self, ssa_dir):
        df = load_ssa_data(ssa_dir)
        agg = aggregate_by_name(df)
        # Use very low thresholds for test data
        result = classify_unisex(agg, min_count=100, min_year=2019)
        jordan = result.filter(pl.col("name") == "Jordan")
        # Jordan appears in both M and F
        unisex_vals = jordan["unisex"].to_list()
        assert any(v == 1 for v in unisex_vals)

    def test_liam_not_unisex(self, ssa_dir):
        df = load_ssa_data(ssa_dir)
        agg = aggregate_by_name(df)
        result = classify_unisex(agg, min_count=100, min_year=2019)
        liam = result.filter(pl.col("name") == "Liam")
        assert liam["unisex"][0] is None


class TestComputeFeatures:
    def test_adds_all_feature_columns(self, ssa_dir):
        df = load_ssa_data(ssa_dir)
        agg = aggregate_by_name(df)
        phonetic = extract_phonetics(agg)
        result = compute_features(phonetic)
        expected_cols = {"first_letter", "stresses", "syllables", "alliteration", "alliteration_first"}
        assert expected_cols.issubset(set(result.columns))

    def test_first_letter_correct(self, ssa_dir):
        df = load_ssa_data(ssa_dir)
        agg = aggregate_by_name(df)
        phonetic = extract_phonetics(agg)
        result = compute_features(phonetic)
        john = result.filter((pl.col("name") == "John") & (pl.col("sex") == "M"))
        assert john["first_letter"][0] == "J"
