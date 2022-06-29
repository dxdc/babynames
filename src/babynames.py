import re
from functools import lru_cache
from itertools import chain
from itertools import product as iterprod
from pathlib import Path
from statistics import mean
from typing import Callable, List, Optional

import nltk
import pandas as pd
import swifter
from pronouncing import phones_for_word, syllable_count

try:
    arpabet = nltk.corpus.cmudict.dict()
except LookupError:
    nltk.download("cmudict")
    arpabet = nltk.corpus.cmudict.dict()


@lru_cache()
def wordbreak(s: str) -> List[str]:
    s = s.lower()
    if s in arpabet:
        return arpabet[s]
    middle = len(s) / 2
    partition = sorted(list(range(len(s))), key=lambda x: (x - middle) ** 2 - x)
    for i in partition:
        pre, suf = (s[:i], s[i:])
        if pre in arpabet and wordbreak(suf) is not None:
            return [x + y for x, y in iterprod(arpabet[pre], wordbreak(suf))]
    return []


def phones_in_word(word: str) -> List[str]:
    phones: List[str] = phones_for_word(word)
    if phones:
        return phones

    return [" ".join(x) for x in wordbreak(word)]


def stresses_in_word(phones: List[str]) -> List[str]:
    return [re.sub(r"[^0-2]", "", phone) for phone in phones]


def syllables_in_word(phones: List[str]) -> int:
    if len(phones) > 0:
        mean_syllables: float = mean([syllable_count(phone) for phone in phones])
        return int(round(mean_syllables, 1))

    return 0


def alliteration_in_word(phones: List[str]) -> Optional[int]:
    if any(
        any(phone.split().count(element) > 1 for element in phone.split())
        for phone in phones
    ):
        return 1


def alliteration_with_last(phones: List[str]) -> Optional[str]:
    # last_name_phones = "K AE1 S P IY0"

    if any(phone.startswith("K ") for phone in phones):
        return "first"
    elif any(re.match(r".* IY\d$", phone) for phone in phones):
        return "last"
    elif any(re.match(r".*(K|AH\d|AE\d|S P|IY\d)( |$)", phone) for phone in phones):
        return "partial"


def main():
    ## load SSA data
    ## see: https://www.ssa.gov/oact/babynames/limits.html

    source_files = sorted(Path("data/babynames").glob("*.txt"))
    dataframes = []
    for file in source_files:
        df = pd.read_csv(file, header=None, names=["name", "sex", "n"])
        df["year"] = int(file.stem.replace("yob", ""))
        dataframes.append(df)

    df = pd.concat(dataframes)

    ## load biblical names

    df_bible = pd.read_csv("data/biblical_names.csv")
    df_bible["biblical"] = 1

    ## determine most popular year for each name

    popular_years = (
        df.merge(
            df.groupby(["name", "sex"], as_index=False)["n"].max(),
            how="inner",
            on=["name", "sex", "n"],
        )
        .groupby(["name", "sex"], as_index=False)["year"]
        .max()
        .rename(columns={"year": "year_pop"}, inplace=False)
    )

    ## aggregate names by sex, n occurences

    df = (
        df.groupby(["name", "sex"], as_index=False)
        .agg({"year": ["min", "max"], "n": "sum"})
        .sort_values(by=["sex", ("n", "sum"), "name"], ascending=[True, False, True])
    )

    df.columns = df.columns.to_flat_index().map(lambda x: "_".join(x).strip("_"))

    ## find matching biblical names

    df = df.join(df_bible.set_index("name"), on=("name")).reset_index(drop=True)

    ## extract phonetic pronunciation (phones) for each name

    df["phones"] = df["name"].swifter.progress_bar(False).apply(phones_in_word)
    phones_map = (
        df.explode("phones")
        .groupby(["phones"])
        .agg({"name": lambda row: " ".join(set(row))})["name"]
        .to_dict()
    )

    ## develop complete list of alternative spellings based on phonetic pronunctiation

    full_alt_spellings_lambda: Callable[[List[str]], str] = lambda row: " ".join(
        list(set(" ".join([phones_map[phone] for phone in row]).split(" ")))
    )
    df["full_alt_spellings"] = (
        df["phones"].swifter.progress_bar(False).apply(full_alt_spellings_lambda)
    )

    alt_spellings_lambda: Callable[[List[str]], str] = lambda row: " ".join(
        [x for x in row["full_alt_spellings"].split(" ") if x != row["name"]]
    )
    alt_spellings = (
        df[["full_alt_spellings", "name"]]
        .swifter.progress_bar(False)
        .apply(
            alt_spellings_lambda,
            axis=1,
        )
    )

    df.insert(1, "alt_spellings", alt_spellings)

    ## merge in  the most popular year for each name

    df = df.merge(
        popular_years, how="left", left_on=["name", "sex"], right_on=["name", "sex"]
    )

    ## combine all names:
    ## keep the most popular spelling of the name as primary
    ## use min / max as appropriate (e.g., popular years, etc.)

    df = (
        df.groupby(["full_alt_spellings", "sex"], as_index=False)
        .agg(
            {
                "name": "first",
                "alt_spellings": "first",
                "n_sum": "sum",
                "year_min": "min",
                "year_max": "max",
                "year_pop": "max",
                "biblical": "max",
                "phones": lambda x: list(set(list(chain(*x)))),
            }
        )
        .drop("full_alt_spellings", 1)
        .sort_values(by=["sex", "n_sum", "name"], ascending=[True, False, True])
    )

    ## few other name based "calculations", including
    ## - stress patterns
    ## - syllables
    ## - alliteration with first and last name (if supplied)

    df["first_letter"] = df["name"].swifter.progress_bar(False).apply(lambda x: x[0])
    df["stresses"] = df["phones"].swifter.progress_bar(False).apply(stresses_in_word)
    df["syllables"] = df["phones"].swifter.progress_bar(False).apply(syllables_in_word)
    df["alliteration_first"] = (
        df["phones"].swifter.progress_bar(False).apply(alliteration_in_word)
    )

    # TODO: Can be customized for specific last name choices as well
    # df["alliteration_last"] = (
    #     df["phones"].swifter.progress_bar(False).apply(alliteration_with_last)
    # )

    ## use arbitary cut off to calculate as a "unisex" name:
    ## - minimum of 15000 babies named in both genders
    ## - name must be used after 1970

    unisex_map = {
        k: 1
        for k, v in df[(df["year_max"] > 1970) & (df["n_sum"] > 15000)]["name"]
        .value_counts()
        .to_dict()
        .items()
        if v > 1
    }
    df["unisex"] = df["name"].map(unisex_map)

    ## save all names to csv

    df.to_csv("all-names.csv", index=False)

    ## split by gender (M, F), assign n_percent, which represents the cumulative percentage of names

    for sex in ["M", "F"]:
        gender = df[df["sex"] == sex].drop("sex", 1)
        gender.insert(
            3,
            "n_percent",
            100 * (gender["n_sum"].cumsum() / gender["n_sum"].sum()).round(3),
        )
        gender.insert(0, "rank", gender["n_sum"].rank(method="dense", ascending=False))
        gender.to_csv("{}.csv".format("boys" if sex == "M" else "girls"), index=False)


if __name__ == "__main__":
    main()
