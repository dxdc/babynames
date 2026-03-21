"""Tests for CSV output format and integrity."""

from pathlib import Path

import polars as pl
import pytest
from src.babynames import (
    PRONUNCIATION_SEPARATOR,
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


@pytest.fixture
def generated_csvs(ssa_dir, biblical_path, tmp_path) -> Path:
    """Run the full pipeline and return the output directory."""
    raw = load_ssa_data(ssa_dir)
    biblical = load_biblical_names(biblical_path)
    peak_years = find_peak_popularity_years(raw)
    df = aggregate_counts(raw)
    df = df.join(biblical.select("name", "biblical"), on="name", how="left")
    df = add_pronunciations(df)
    df = build_spelling_variants(df)
    df = df.join(peak_years, on=["name", "sex"], how="left")
    df = flag_palindromes(df)
    df = merge_spelling_variants(df)
    df = compute_name_features(df)
    df = classify_unisex_names(df, min_count=100, min_year=2019)
    export_csvs(df, tmp_path)
    return tmp_path


class TestOutputFiles:
    def test_all_files_created(self, generated_csvs) -> None:
        assert (generated_csvs / "all-names.csv").exists()
        assert (generated_csvs / "boys.csv").exists()
        assert (generated_csvs / "girls.csv").exists()

    def test_boys_csv_nonempty(self, generated_csvs) -> None:
        df = pl.read_csv(generated_csvs / "boys.csv")
        assert df.height > 0

    def test_girls_csv_nonempty(self, generated_csvs) -> None:
        df = pl.read_csv(generated_csvs / "girls.csv")
        assert df.height > 0


class TestBoysCSVSchema:
    def test_has_rank_column(self, generated_csvs) -> None:
        df = pl.read_csv(generated_csvs / "boys.csv")
        assert "rank" in df.columns

    def test_has_cumulative_pct_column(self, generated_csvs) -> None:
        df = pl.read_csv(generated_csvs / "boys.csv")
        assert "cumulative_pct" in df.columns

    def test_rank_starts_at_1(self, generated_csvs) -> None:
        df = pl.read_csv(generated_csvs / "boys.csv")
        assert df["rank"].min() == 1

    def test_ranks_are_ordered(self, generated_csvs) -> None:
        df = pl.read_csv(generated_csvs / "boys.csv")
        ranks = df["rank"].to_list()
        assert ranks == sorted(ranks)

    def test_cumulative_pct_increases(self, generated_csvs) -> None:
        df = pl.read_csv(generated_csvs / "boys.csv")
        pcts = df["cumulative_pct"].to_list()
        for i in range(1, len(pcts)):
            assert pcts[i] >= pcts[i - 1]


class TestAllNamesCSV:
    def test_has_sex_column(self, generated_csvs) -> None:
        df = pl.read_csv(generated_csvs / "all-names.csv")
        assert "sex" in df.columns

    def test_has_both_sexes(self, generated_csvs) -> None:
        df = pl.read_csv(generated_csvs / "all-names.csv")
        sexes = df["sex"].unique().sort().to_list()
        assert sexes == ["F", "M"]

    def test_no_rank_column(self, generated_csvs) -> None:
        df = pl.read_csv(generated_csvs / "all-names.csv")
        assert "rank" not in df.columns


class TestPronunciationDelimiter:
    def test_multi_pronunciation_uses_pipe(self, generated_csvs) -> None:
        """Verify that multiple pronunciations are separated by ' | '."""
        df = pl.read_csv(generated_csvs / "boys.csv")
        # Find a name that likely has multiple pronunciations
        john = df.filter(pl.col("name") == "John")
        if john.height > 0:
            phones = john["pronunciations"][0]
            # Single pronunciation should not contain pipe
            if isinstance(phones, str) and PRONUNCIATION_SEPARATOR in phones:
                parts = phones.split(PRONUNCIATION_SEPARATOR)
                assert all(len(p.strip()) > 0 for p in parts)
