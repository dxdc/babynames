"""Tests for the data pipeline stages."""

import polars as pl
import pytest

from src.babynames import (
    add_pronunciations,
    aggregate_counts,
    build_spelling_variants,
    classify_unisex_names,
    compute_name_features,
    find_peak_popularity_years,
    flag_palindromes,
    load_biblical_names,
    load_ssa_data,
)


class TestLoadSSAData:
    def test_loads_files(self, ssa_dir) -> None:
        df = load_ssa_data(ssa_dir)
        assert df.height > 0
        assert set(df.columns) == {"name", "sex", "count", "year"}

    def test_has_expected_names(self, ssa_dir) -> None:
        df = load_ssa_data(ssa_dir)
        names = df["name"].unique().to_list()
        assert "Liam" in names
        assert "Olivia" in names

    def test_has_both_years(self, ssa_dir) -> None:
        df = load_ssa_data(ssa_dir)
        years = df["year"].unique().sort().to_list()
        assert years == [2020, 2021]

    def test_missing_dir_raises(self, tmp_path) -> None:
        with pytest.raises(FileNotFoundError):
            load_ssa_data(tmp_path / "nonexistent")


class TestLoadBiblicalNames:
    def test_loads(self, biblical_path) -> None:
        df = load_biblical_names(biblical_path)
        assert "name" in df.columns
        assert "biblical" in df.columns
        assert df.height > 0

    def test_has_expected_names(self, biblical_path) -> None:
        df = load_biblical_names(biblical_path)
        names = df["name"].to_list()
        assert "John" in names
        assert "Mary" in names


class TestFindPeakPopularityYears:
    def test_returns_year_peak(self, ssa_dir) -> None:
        df = load_ssa_data(ssa_dir)
        peak = find_peak_popularity_years(df)
        assert "year_peak" in peak.columns
        liam = peak.filter((pl.col("name") == "Liam") & (pl.col("sex") == "M"))
        assert liam["year_peak"][0] == 2021


class TestAggregateCounts:
    def test_aggregation(self, ssa_dir) -> None:
        df = load_ssa_data(ssa_dir)
        agg = aggregate_counts(df)
        assert "total_count" in agg.columns
        assert "year_min" in agg.columns
        assert "year_max" in agg.columns

        liam = agg.filter((pl.col("name") == "Liam") & (pl.col("sex") == "M"))
        assert liam["total_count"][0] == 19659 + 20272
        assert liam["year_min"][0] == 2020
        assert liam["year_max"][0] == 2021

    def test_sorted_by_count_desc(self, ssa_dir) -> None:
        df = load_ssa_data(ssa_dir)
        agg = aggregate_counts(df)
        boys = agg.filter(pl.col("sex") == "M")
        counts = boys["total_count"].to_list()
        assert counts == sorted(counts, reverse=True)


class TestAddPronunciations:
    def test_adds_column(self, ssa_dir) -> None:
        df = load_ssa_data(ssa_dir)
        agg = aggregate_counts(df)
        result = add_pronunciations(agg)
        assert "pronunciations" in result.columns

    def test_john_has_pronunciations(self, ssa_dir) -> None:
        df = load_ssa_data(ssa_dir)
        agg = aggregate_counts(df)
        result = add_pronunciations(agg)
        john = result.filter(pl.col("name") == "John")
        pronunciations = john["pronunciations"][0]
        assert len(pronunciations) > 0


class TestBuildSpellingVariants:
    def test_john_jon_are_variants(self, ssa_dir) -> None:
        df = load_ssa_data(ssa_dir)
        agg = aggregate_counts(df)
        with_pron = add_pronunciations(agg)
        result = build_spelling_variants(with_pron)
        john = result.filter((pl.col("name") == "John") & (pl.col("sex") == "M"))
        variants = john["spelling_variants"][0]
        assert "Jon" in variants


class TestFlagPalindromes:
    def test_hannah_is_palindrome(self, ssa_dir) -> None:
        df = load_ssa_data(ssa_dir)
        agg = aggregate_counts(df)
        result = flag_palindromes(agg)
        hannah = result.filter(pl.col("name") == "Hannah")
        assert hannah["is_palindrome"][0] == 1

    def test_john_not_palindrome(self, ssa_dir) -> None:
        df = load_ssa_data(ssa_dir)
        agg = aggregate_counts(df)
        result = flag_palindromes(agg)
        john = result.filter((pl.col("name") == "John") & (pl.col("sex") == "M"))
        assert john["is_palindrome"][0] is None


class TestClassifyUnisexNames:
    def test_jordan_is_unisex(self, ssa_dir) -> None:
        df = load_ssa_data(ssa_dir)
        agg = aggregate_counts(df)
        result = classify_unisex_names(agg, min_count=100, min_year=2019)
        jordan = result.filter(pl.col("name") == "Jordan")
        assert any(v == 1 for v in jordan["unisex"].to_list())

    def test_liam_not_unisex(self, ssa_dir) -> None:
        df = load_ssa_data(ssa_dir)
        agg = aggregate_counts(df)
        result = classify_unisex_names(agg, min_count=100, min_year=2019)
        liam = result.filter(pl.col("name") == "Liam")
        assert liam["unisex"][0] is None


class TestComputeNameFeatures:
    def test_adds_all_feature_columns(self, ssa_dir) -> None:
        df = load_ssa_data(ssa_dir)
        agg = aggregate_counts(df)
        with_pron = add_pronunciations(agg)
        result = compute_name_features(with_pron)
        expected = {"first_letter", "stresses", "syllables", "alliteration", "alliteration_first"}
        assert expected.issubset(set(result.columns))

    def test_first_letter_correct(self, ssa_dir) -> None:
        df = load_ssa_data(ssa_dir)
        agg = aggregate_counts(df)
        with_pron = add_pronunciations(agg)
        result = compute_name_features(with_pron)
        john = result.filter((pl.col("name") == "John") & (pl.col("sex") == "M"))
        assert john["first_letter"][0] == "J"
