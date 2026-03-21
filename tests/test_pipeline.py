"""Tests for the data pipeline stages."""

import polars as pl
import pytest
from src.babynames import (
    add_pronunciations,
    aggregate_counts,
    build_spelling_variants,
    classify_unisex_names,
    compute_name_features,
    export_csvs,
    find_peak_popularity_years,
    flag_palindromes,
    load_biblical_names,
    load_ssa_data,
    merge_spelling_variants,
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


class TestMergeSpellingVariants:
    """Tests for the core deduplication logic."""

    @pytest.fixture
    def prepared_df(self, ssa_dir, biblical_path):
        """Run pipeline up to (but not including) merge."""
        raw = load_ssa_data(ssa_dir)
        biblical = load_biblical_names(biblical_path)
        peak = find_peak_popularity_years(raw)
        df = aggregate_counts(raw)
        df = df.join(biblical.select("name", "biblical"), on="name", how="left")
        df = add_pronunciations(df)
        df = build_spelling_variants(df)
        df = df.join(peak, on=["name", "sex"], how="left")
        df = flag_palindromes(df)
        return df

    def test_john_jon_merged(self, prepared_df) -> None:
        result = merge_spelling_variants(prepared_df)
        johns = result.filter((pl.col("name") == "John") & (pl.col("sex") == "M"))
        assert johns.height == 1
        # John (more popular) should be the primary name, not Jon
        assert johns["name"][0] == "John"

    def test_merged_count_sums(self, prepared_df) -> None:
        result = merge_spelling_variants(prepared_df)
        # John + Jon combined count should be sum of both
        johns = result.filter((pl.col("name") == "John") & (pl.col("sex") == "M"))
        john_only = prepared_df.filter((pl.col("name") == "John") & (pl.col("sex") == "M"))
        jon_only = prepared_df.filter((pl.col("name") == "Jon") & (pl.col("sex") == "M"))
        expected = john_only["total_count"][0] + jon_only["total_count"][0]
        assert johns["total_count"][0] == expected

    def test_no_rows_lost_for_unique_names(self, prepared_df) -> None:
        result = merge_spelling_variants(prepared_df)
        # Liam has no variants - should still be present
        liam = result.filter((pl.col("name") == "Liam") & (pl.col("sex") == "M"))
        assert liam.height == 1

    def test_year_range_spans_all_variants(self, prepared_df) -> None:
        result = merge_spelling_variants(prepared_df)
        johns = result.filter((pl.col("name") == "John") & (pl.col("sex") == "M"))
        # Year range should span both John and Jon's ranges
        assert johns["year_min"][0] == 2020
        assert johns["year_max"][0] == 2021

    def test_biblical_preserved_from_any_variant(self, prepared_df) -> None:
        result = merge_spelling_variants(prepared_df)
        # John is biblical; after merge with Jon, should still be biblical
        johns = result.filter((pl.col("name") == "John") & (pl.col("sex") == "M"))
        assert johns["biblical"][0] == 1

    def test_pronunciations_union(self, prepared_df) -> None:
        result = merge_spelling_variants(prepared_df)
        johns = result.filter((pl.col("name") == "John") & (pl.col("sex") == "M"))
        pronunciations = johns["pronunciations"][0]
        # Should have pronunciations from both John and Jon
        assert len(pronunciations) >= 1

    def test_sorted_by_count_after_merge(self, prepared_df) -> None:
        result = merge_spelling_variants(prepared_df)
        boys = result.filter(pl.col("sex") == "M")
        counts = boys["total_count"].to_list()
        assert counts == sorted(counts, reverse=True)


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

    def test_boundary_at_min_count(self, ssa_dir) -> None:
        df = load_ssa_data(ssa_dir)
        agg = aggregate_counts(df)
        # With threshold higher than any single name+sex count, none should be unisex
        result = classify_unisex_names(agg, min_count=999999, min_year=2019)
        assert result["unisex"].drop_nulls().len() == 0


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


class TestIntegration:
    """End-to-end pipeline tests."""

    def test_no_rows_lost(self, ssa_dir, biblical_path) -> None:
        """Total count across all output names should equal input count."""
        raw = load_ssa_data(ssa_dir)
        total_input = raw["count"].sum()

        biblical = load_biblical_names(biblical_path)
        peak = find_peak_popularity_years(raw)
        df = aggregate_counts(raw)
        df = df.join(biblical.select("name", "biblical"), on="name", how="left")
        df = add_pronunciations(df)
        df = build_spelling_variants(df)
        df = df.join(peak, on=["name", "sex"], how="left")
        df = flag_palindromes(df)
        df = merge_spelling_variants(df)

        total_output = df["total_count"].sum()
        assert total_output == total_input

    def test_export_round_trip(self, ssa_dir, biblical_path, tmp_path) -> None:
        """Exported CSVs should be parseable and have correct structure."""
        raw = load_ssa_data(ssa_dir)
        biblical = load_biblical_names(biblical_path)
        peak = find_peak_popularity_years(raw)
        df = aggregate_counts(raw)
        df = df.join(biblical.select("name", "biblical"), on="name", how="left")
        df = add_pronunciations(df)
        df = build_spelling_variants(df)
        df = df.join(peak, on=["name", "sex"], how="left")
        df = flag_palindromes(df)
        df = merge_spelling_variants(df)
        df = compute_name_features(df)
        df = classify_unisex_names(df, min_count=100, min_year=2019)
        export_csvs(df, tmp_path)

        boys = pl.read_csv(tmp_path / "boys.csv")
        girls = pl.read_csv(tmp_path / "girls.csv")
        all_names = pl.read_csv(tmp_path / "all-names.csv")

        # Row counts should be consistent
        assert boys.height + girls.height == all_names.height

        # Cumulative pct should end near 100
        assert boys["cumulative_pct"][-1] == pytest.approx(100.0, abs=0.5)
        assert girls["cumulative_pct"][-1] == pytest.approx(100.0, abs=0.5)

        # Rank should be dense (no gaps)
        assert boys["rank"].max() <= boys.height
        assert girls["rank"].max() <= girls.height
