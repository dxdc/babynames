"""Tests for CSV output format and integrity."""

from pathlib import Path

import polars as pl
import pytest

from src.babynames import (
    add_palindromes,
    aggregate_by_name,
    build_alt_spellings,
    classify_unisex,
    compute_features,
    compute_popular_years,
    deduplicate_by_pronunciation,
    export_csvs,
    extract_phonetics,
    load_biblical_names,
    load_ssa_data,
)


@pytest.fixture
def generated_csvs(ssa_dir, biblical_path, tmp_path):
    """Run the full pipeline and return the output directory."""
    df = load_ssa_data(ssa_dir)
    df_bible = load_biblical_names(biblical_path)
    popular_years = compute_popular_years(df)
    df = aggregate_by_name(df)
    df = df.join(df_bible.select("name", "biblical"), on="name", how="left")
    df = extract_phonetics(df)
    df = build_alt_spellings(df)
    df = df.join(popular_years, on=["name", "sex"], how="left")
    df = add_palindromes(df)
    df = deduplicate_by_pronunciation(df)
    df = compute_features(df)
    df = classify_unisex(df, min_count=100, min_year=2019)
    export_csvs(df, tmp_path)
    return tmp_path


class TestOutputFiles:
    def test_all_files_created(self, generated_csvs):
        assert (generated_csvs / "all-names.csv").exists()
        assert (generated_csvs / "boys.csv").exists()
        assert (generated_csvs / "girls.csv").exists()

    def test_boys_csv_nonempty(self, generated_csvs):
        df = pl.read_csv(generated_csvs / "boys.csv")
        assert df.height > 0

    def test_girls_csv_nonempty(self, generated_csvs):
        df = pl.read_csv(generated_csvs / "girls.csv")
        assert df.height > 0


class TestBoysCSVSchema:
    def test_has_rank_column(self, generated_csvs):
        df = pl.read_csv(generated_csvs / "boys.csv")
        assert "rank" in df.columns

    def test_has_n_percent_column(self, generated_csvs):
        df = pl.read_csv(generated_csvs / "boys.csv")
        assert "n_percent" in df.columns

    def test_rank_starts_at_1(self, generated_csvs):
        df = pl.read_csv(generated_csvs / "boys.csv")
        assert df["rank"].min() == 1

    def test_ranks_are_ordered(self, generated_csvs):
        df = pl.read_csv(generated_csvs / "boys.csv")
        ranks = df["rank"].to_list()
        assert ranks == sorted(ranks)

    def test_n_percent_increases(self, generated_csvs):
        df = pl.read_csv(generated_csvs / "boys.csv")
        pcts = df["n_percent"].to_list()
        for i in range(1, len(pcts)):
            assert pcts[i] >= pcts[i - 1]


class TestAllNamesCSV:
    def test_has_sex_column(self, generated_csvs):
        df = pl.read_csv(generated_csvs / "all-names.csv")
        assert "sex" in df.columns

    def test_has_both_sexes(self, generated_csvs):
        df = pl.read_csv(generated_csvs / "all-names.csv")
        sexes = df["sex"].unique().sort().to_list()
        assert sexes == ["F", "M"]

    def test_no_rank_column(self, generated_csvs):
        df = pl.read_csv(generated_csvs / "all-names.csv")
        assert "rank" not in df.columns
