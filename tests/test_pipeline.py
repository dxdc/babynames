"""Tests for the data pipeline stages."""

import logging

import polars as pl
import pytest
from src.babynames import (
    EXCLUDED_NAMES,
    add_nickname_columns,
    add_pronunciations,
    aggregate_counts,
    apply_forced_merges,
    build_spelling_variants,
    classify_unisex_names,
    compute_name_features,
    export_csvs,
    find_peak_popularity_years,
    flag_palindromes,
    load_biblical_names,
    load_nicknames,
    load_pronunciation_overrides,
    load_ssa_data,
    load_territory_data,
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

    def test_excludes_junk_names(self, ssa_dir) -> None:
        df = load_ssa_data(ssa_dir)
        names = set(df["name"].unique().to_list())
        for blocked in EXCLUDED_NAMES:
            assert blocked not in names, f"{blocked} should be excluded"


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
        # Jon should appear in the spelling variants
        assert "Jon" in johns["spelling_variants"][0]

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
        assert johns["biblical"][0] is not None

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
        result = classify_unisex_names(agg, min_count=100, recency_years=2)
        jordan = result.filter(pl.col("name") == "Jordan")
        pcts = [v for v in jordan["unisex_pct"].to_list() if v is not None]
        assert len(pcts) > 0
        for v in pcts:
            assert 0 < v <= 50, f"unisex_pct should be in (0, 50], got {v}"

    def test_liam_not_unisex(self, ssa_dir) -> None:
        df = load_ssa_data(ssa_dir)
        agg = aggregate_counts(df)
        result = classify_unisex_names(agg, min_count=100, recency_years=2)
        liam = result.filter(pl.col("name") == "Liam")
        assert liam["unisex_pct"][0] is None

    def test_boundary_at_min_count(self, ssa_dir) -> None:
        df = load_ssa_data(ssa_dir)
        agg = aggregate_counts(df)
        # With threshold higher than any single name+sex count, none should have a ratio
        result = classify_unisex_names(agg, min_count=999999, recency_years=2)
        assert result["unisex_pct"].drop_nulls().len() == 0


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


class TestApplyForcedMerges:
    def test_merges_groups(self, ssa_dir, forced_merges_path) -> None:
        raw = load_ssa_data(ssa_dir)
        agg = aggregate_counts(raw)
        with_pron = add_pronunciations(agg)
        with_variants = build_spelling_variants(with_pron)

        result = apply_forced_merges(with_variants, forced_merges_path)
        jon_after = result.filter((pl.col("name") == "Jon") & (pl.col("sex") == "M"))
        john_after = result.filter((pl.col("name") == "John") & (pl.col("sex") == "M"))

        # After merge, they should share the same variant_group
        assert jon_after["variant_group"][0] == john_after["variant_group"][0]

    def test_nonexistent_pair_ignored(self, ssa_dir, tmp_path) -> None:
        raw = load_ssa_data(ssa_dir)
        agg = aggregate_counts(raw)
        with_pron = add_pronunciations(agg)
        with_variants = build_spelling_variants(with_pron)

        merges_file = tmp_path / "merges.csv"
        merges_file.write_text("source,target\nXXXXX,YYYYY\n")

        result = apply_forced_merges(with_variants, merges_file)
        assert result.height == with_variants.height


class TestLoadBiblicalCategories:
    def test_category_mapping(self, biblical_path) -> None:
        df = load_biblical_names(biblical_path)
        john = df.filter(pl.col("name") == "John")
        assert john["biblical"][0] == "Person"

    def test_place_category(self, biblical_path) -> None:
        df = load_biblical_names(biblical_path)
        jordan = df.filter(pl.col("name") == "Jordan")
        assert jordan["biblical"][0] == "Place"


class TestLoadNicknames:
    def test_loads_mappings(self, nicknames_path) -> None:
        nick_to_formal, formal_to_nick = load_nicknames(nicknames_path)
        assert "Johnny" in nick_to_formal
        assert "John" in nick_to_formal["Johnny"]
        assert "John" in formal_to_nick
        assert "Johnny" in formal_to_nick["John"]

    def test_multi_mapping(self, nicknames_path) -> None:
        nick_to_formal, _ = load_nicknames(nicknames_path)
        # Jack maps to John
        assert "John" in nick_to_formal["Jack"]

    def test_nonexistent_file(self, tmp_path) -> None:
        nick_to_formal, formal_to_nick = load_nicknames(tmp_path / "nonexistent.csv")
        assert len(nick_to_formal) == 0
        assert len(formal_to_nick) == 0


class TestAddNicknameColumns:
    def test_adds_columns(self, nicknames_path) -> None:
        nick_to_formal, formal_to_nick = load_nicknames(nicknames_path)
        df = pl.DataFrame({"name": ["John", "Johnny", "James", "Jim", "Liam"]})
        result = add_nickname_columns(df, nick_to_formal, formal_to_nick)
        assert "nickname_of" in result.columns
        assert "nicknames" in result.columns

    def test_nickname_of_populated(self, nicknames_path) -> None:
        nick_to_formal, formal_to_nick = load_nicknames(nicknames_path)
        df = pl.DataFrame({"name": ["John", "Johnny", "James", "Jim"]})
        result = add_nickname_columns(df, nick_to_formal, formal_to_nick)
        johnny = result.filter(pl.col("name") == "Johnny")
        assert johnny["nickname_of"][0] is not None
        assert "John" in johnny["nickname_of"][0]

    def test_nicknames_populated(self, nicknames_path) -> None:
        nick_to_formal, formal_to_nick = load_nicknames(nicknames_path)
        df = pl.DataFrame({"name": ["John", "Johnny", "James", "Jim", "Jack"]})
        result = add_nickname_columns(df, nick_to_formal, formal_to_nick)
        john = result.filter(pl.col("name") == "John")
        assert john["nicknames"][0] is not None
        assert "Johnny" in john["nicknames"][0]

    def test_only_existing_names(self, nicknames_path) -> None:
        nick_to_formal, formal_to_nick = load_nicknames(nicknames_path)
        # Jim maps to James, but James isn't in the data
        df = pl.DataFrame({"name": ["Jim"]})
        result = add_nickname_columns(df, nick_to_formal, formal_to_nick)
        jim = result.filter(pl.col("name") == "Jim")
        # James doesn't exist in data, so nickname_of should be None
        assert jim["nickname_of"][0] is None


class TestJrSuffixStripping:
    def test_jr_suffix_removed(self, tmp_path) -> None:
        """Names ending in 'jr' are removed when base name exists."""
        ssa_dir = tmp_path / "ssa"
        ssa_dir.mkdir()
        (ssa_dir / "yob2020.txt").write_text("Martin,M,500\nMartinjr,M,10\n")
        df = load_ssa_data(ssa_dir)
        names = df["name"].to_list()
        assert "Martin" in names
        assert "Martinjr" not in names

    def test_fajr_kept(self, tmp_path) -> None:
        """Names ending in 'jr' are kept when base name doesn't exist."""
        ssa_dir = tmp_path / "ssa"
        ssa_dir.mkdir()
        (ssa_dir / "yob2020.txt").write_text("Fajr,F,50\n")
        df = load_ssa_data(ssa_dir)
        names = df["name"].to_list()
        assert "Fajr" in names


class TestExcludedNames:
    def test_infantof_excluded(self, tmp_path) -> None:
        ssa_dir = tmp_path / "ssa"
        ssa_dir.mkdir()
        (ssa_dir / "yob2020.txt").write_text("Infantof,M,100\nJohn,M,500\n")
        df = load_ssa_data(ssa_dir)
        names = set(df["name"].to_list())
        assert "Infantof" not in names
        assert "John" in names

    def test_boy_and_girl_not_excluded(self, tmp_path) -> None:
        """Boy and Girl are legitimate names, not excluded."""
        ssa_dir = tmp_path / "ssa"
        ssa_dir.mkdir()
        (ssa_dir / "yob2020.txt").write_text("Boy,M,100\nGirl,F,80\nJohn,M,500\n")
        df = load_ssa_data(ssa_dir)
        names = set(df["name"].to_list())
        assert "Boy" in names
        assert "Girl" in names

    def test_wm_excluded(self, tmp_path) -> None:
        ssa_dir = tmp_path / "ssa"
        ssa_dir.mkdir()
        (ssa_dir / "yob2020.txt").write_text("Wm,M,100\nWilliam,M,500\n")
        df = load_ssa_data(ssa_dir)
        names = set(df["name"].to_list())
        assert "Wm" not in names
        assert "William" in names


class TestLoadTerritoryData:
    def test_loads_files(self, territory_dir) -> None:
        df = load_territory_data(territory_dir)
        assert df is not None
        assert df.height > 0
        assert set(df.columns) == {"name", "sex", "year", "count"}

    def test_territory_column_dropped(self, territory_dir) -> None:
        df = load_territory_data(territory_dir)
        assert "territory" not in df.columns

    def test_excludes_junk_names(self, territory_dir) -> None:
        df = load_territory_data(territory_dir)
        names = set(df["name"].to_list())
        assert "Unknown" not in names
        assert "Boy" in names  # Boy is a legitimate name, not excluded

    def test_returns_none_for_empty_dir(self, tmp_path) -> None:
        empty = tmp_path / "empty"
        empty.mkdir()
        assert load_territory_data(empty) is None

    def test_concatenates_multiple_files(self, territory_dir) -> None:
        df = load_territory_data(territory_dir)
        names = set(df["name"].to_list())
        # PR.TXT has Paola, TR.TXT has Gabrielle
        assert "Paola" in names
        assert "Gabrielle" in names

    def test_has_both_sexes(self, territory_dir) -> None:
        df = load_territory_data(territory_dir)
        sexes = set(df["sex"].to_list())
        assert sexes == {"F", "M"}


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
        df = classify_unisex_names(df, min_count=100, recency_years=2)
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


class TestMalformedCSVInputs:
    def test_empty_pronunciation_overrides(self, tmp_path) -> None:
        empty = tmp_path / "empty.csv"
        empty.write_text("")
        result = load_pronunciation_overrides(empty)
        assert result == {}

    def test_malformed_forced_merges_lines(self, ssa_dir, tmp_path) -> None:
        """Lines with no comma should be silently skipped."""
        raw = load_ssa_data(ssa_dir)
        agg = aggregate_counts(raw)
        with_pron = add_pronunciations(agg)
        with_variants = build_spelling_variants(with_pron)

        merges_file = tmp_path / "bad.csv"
        merges_file.write_text("source,target\nNOCOMMA\nJohn,Jon\n")
        result = apply_forced_merges(with_variants, merges_file)
        assert result.height == with_variants.height

    def test_nicknames_missing_columns(self, tmp_path) -> None:
        """Lines with no comma should be silently skipped."""
        bad = tmp_path / "bad.csv"
        bad.write_text("nickname,formal_name\nNOCOMMA\nJohnny,John\n")
        nick_to_formal, formal_to_nick = load_nicknames(bad)
        assert "Johnny" in nick_to_formal
        assert len(nick_to_formal) == 1  # NOCOMMA was skipped


class TestForcedMergeConflicts:
    def test_warns_on_conflicting_sources(self, ssa_dir, tmp_path, caplog) -> None:
        """A source mapping to multiple different targets should log a warning."""
        raw = load_ssa_data(ssa_dir)
        agg = aggregate_counts(raw)
        with_pron = add_pronunciations(agg)
        with_variants = build_spelling_variants(with_pron)

        merges_file = tmp_path / "conflict.csv"
        merges_file.write_text("source,target\nJon,John\nJon,James\n")
        with caplog.at_level(logging.WARNING):
            apply_forced_merges(with_variants, merges_file)
        assert any("conflict" in r.message.lower() for r in caplog.records)

    def test_circular_merge_no_crash(self, ssa_dir, tmp_path) -> None:
        """Circular merges (A→B, B→A) should not crash."""
        raw = load_ssa_data(ssa_dir)
        agg = aggregate_counts(raw)
        with_pron = add_pronunciations(agg)
        with_variants = build_spelling_variants(with_pron)

        merges_file = tmp_path / "circular.csv"
        merges_file.write_text("source,target\nJohn,Jon\nJon,John\n")
        result = apply_forced_merges(with_variants, merges_file)
        assert result.height == with_variants.height


class TestUnisexEdgeCases:
    def test_single_gender_returns_none(self, ssa_dir) -> None:
        """Names that exist for only one gender should have null unisex_pct."""
        df = load_ssa_data(ssa_dir)
        agg = aggregate_counts(df)
        result = classify_unisex_names(agg, min_count=100, recency_years=2)
        liam = result.filter((pl.col("name") == "Liam") & (pl.col("sex") == "M"))
        assert liam["unisex_pct"][0] is None
        assert liam["unisex_dominant"][0] is None


class TestAdditionalPalindromes:
    def test_bob_is_palindrome(self, ssa_dir) -> None:
        df = load_ssa_data(ssa_dir)
        agg = aggregate_counts(df)
        result = flag_palindromes(agg)
        bob = result.filter((pl.col("name") == "Bob") & (pl.col("sex") == "M"))
        assert bob.height == 1
        assert bob["is_palindrome"][0] == 1

    def test_anna_is_palindrome(self, ssa_dir) -> None:
        df = load_ssa_data(ssa_dir)
        agg = aggregate_counts(df)
        result = flag_palindromes(agg)
        anna = result.filter((pl.col("name") == "Anna") & (pl.col("sex") == "F"))
        assert anna.height == 1
        assert anna["is_palindrome"][0] == 1


class TestOOVNames:
    def test_zaylen_gets_pronunciation_attempt(self, ssa_dir) -> None:
        """Names not in CMU dict should still get a pronunciation list (possibly empty)."""
        df = load_ssa_data(ssa_dir)
        agg = aggregate_counts(df)
        result = add_pronunciations(agg)
        zaylen = result.filter((pl.col("name") == "Zaylen") & (pl.col("sex") == "M"))
        assert zaylen.height == 1
        # pronunciations column should exist and be a list type
        assert result["pronunciations"].dtype == pl.List(pl.String)
