from calendar import month_name
from datetime import datetime

from aiohttp import ClientResponseError, ClientSession
from discord import Embed
from discord.ext.commands import Cog, command
from markdownify import markdownify as md

from ..utils import maybe_send

ANILIST_GRAPHQL_URL = "https://graphql.anilist.co"
FORMAT_REPR = {
    "TV": "TV",
    "TV_SHORT": "TV Short",
    "MOVIE": "Movie",
    "SPECIAL": "Special",
    "OVA": "OVA",
    "ONA": "ONA",
    "MUSIC": "Music",
    "MANGA": "Manga",
    "NOVEL": "Light Novel",
    "ONE_SHOT": "One Shot",
}
QUERY = """
query(
    $isAnime: Boolean!,
    $format: [MediaFormat],
    $search: String!
) {
    anime: Media(
        type: ANIME,
        search: $search,
        sort: SEARCH_MATCH
    ) @include(if: $isAnime) {
        ...baseFields
        ...animeFields
    }

    manga: Media(
        type: MANGA,
        format_in: $format,
        search: $search,
        sort: SEARCH_MATCH
    ) @skip(if: $isAnime) {
        ...baseFields
        ...mangaFields
    }
}

fragment baseFields on Media {
    title { english romaji }
    coverImage { large }
    meanScore
    genres
    description

    format
    source

    status
    startDate { year month day }
    nextAiringEpisode { airingAt }
    endDate { year month day }

    idMal
    siteUrl
}

fragment animeFields on Media {
    episodes
}

fragment mangaFields on Media {
    chapters
    volumes
}
"""


class FuzzyDate:
    def __init__(self, **kwargs):
        self.year = kwargs.get("year")

        if self.year:
            self.month = kwargs.get("month")

            if self.month:
                self.day = kwargs.get("day")

    def __bool__(self):
        return bool(self.year)

    def __str__(self):
        if hasattr(self, "day") and self.day:
            return f"{month_name[self.month]} {self.day}, {self.year}"

        if hasattr(self, "month") and self.month:
            return f"{month_name[self.month]} {self.year}"

        if self.year:
            return str(self.year)

        return "unknown"


def normalize_ssc(name):
    """
    Convert a name in SCREAMING_SNAKE_CASE to regular notation,
    e.g. "Screaming snake case".

    Args:
        name: Name to convert.

    Returns:
        str: Converted name.
    """
    if not name:
        return

    return " ".join(part for part in name.split("_")).capitalize()


def truncate_field(content):
    """
    Truncate a string to Discord's requirement for embed fields,
    i.e. a maximum length of 1024.

    Args:
        content (str): String to truncate.

    Returns:
        str: Possibly truncated string, with ellipsis if truncated.

    Todo:
        This currently uses a naive string truncation,
        which might damage the underlying Markdown.
    """
    return content if len(content) <= 1024 else content[:1021] + "..."


def make_embed(item):
    titles = item["title"]
    title_english = titles["english"]
    title_romaji = titles["romaji"]
    if title_english and title_romaji and (title_english != title_romaji):
        title = f"{title_english} (_{title_romaji}_)"

    else:
        title = (
            title_english or title_romaji
        )  # At least one of these should be non-empty

    embed = Embed(
        title=title,
        colour=0x02A9FF,
        description="[AniList]({siteUrl}) | "
        "[MyAnimeList](https://myanimelist.net/anime/{idMal})".format_map(item),
    )

    embed.set_thumbnail(url=item["coverImage"]["large"])
    embed.set_footer(
        text="Powered by AniList",
        icon_url="https://anilist.co/img/icons/favicon-32x32.png",
    )

    score = f'{item["meanScore"]} %' if item["meanScore"] else "-"
    embed.add_field(name="Mean Score", value=score, inline=False)

    embed.add_field(name="Format", value=FORMAT_REPR[item["format"]])
    embed.add_field(name="Source", value=normalize_ssc(item["source"]))

    if "episodes" in item:
        length_key = "episodes"
    elif item["format"] == "NOVEL":
        length_key = "volumes"
    else:
        length_key = "chapters"

    embed.add_field(name=length_key.capitalize(), value=item[length_key] or "unknown")

    embed.add_field(name="Status", value=normalize_ssc(item["status"]) or "unknown")

    embed.add_field(name="Start", value=str(FuzzyDate(**item["startDate"])))
    if item["status"] == "RELEASING" and (next_ep := item["nextAiringEpisode"]):
        embed.add_field(
            name="Next Episode",
            value=datetime.utcfromtimestamp(int(next_ep["airingAt"])).strftime("%c"),
        )
    else:
        embed.add_field(name="End", value=str(FuzzyDate(**item["endDate"])))

    embed.add_field(name="Genres", value=", ".join(item["genres"]), inline=False)
    embed.add_field(
        name="Description", value=truncate_field(md(item["description"])), inline=False
    )

    return embed


class Anilist(Cog):
    """
    Anilist lookup commands.
    """

    def __init__(self, http: ClientSession):
        self._http = http

    async def _execute_graphql(self, **variables):
        body = {"query": QUERY, "variables": variables}

        async with self._http.post(ANILIST_GRAPHQL_URL, json=body) as resp:
            res_body = await resp.json()

        return res_body["data"]

    async def _lookup_series(self, ctx, search: str, is_anime: bool, *formats: str):
        async with ctx.typing():
            try:
                data = await self._execute_graphql(
                    isAnime=is_anime, format=list(formats), search=search
                )
            except ClientResponseError as e:
                if e.status == 404:
                    await maybe_send(ctx, "No results found.")
                elif e.status >= 500:
                    await maybe_send(
                        ctx,
                        "Got an error from AniList. "
                        "Try again in a bit or with a different term.",
                    )
                else:
                    raise

                return

        await ctx.send(embed=make_embed(data["anime" if is_anime else "manga"]))

    @command(aliases=["ani", "al", "anilist"])
    async def anime(self, ctx, *, search: str):
        """
        Look up an anime on Anilist.

        Arguments:
             - search: Term to search for.
        """

        await self._lookup_series(ctx, search, True)

    @command()
    async def manga(self, ctx, *, search: str):
        """
        Look up a manga on Anilist.

        Arguments:
            - search: Term to search for.
        """

        await self._lookup_series(ctx, search, False, "MANGA", "ONE_SHOT")

    @command(aliases=["lightnovel", "novel"])
    async def ln(self, ctx, *, search: str):
        """
        Look up a light novel on Anilist.

        Arguments:
            - search: Term to search for.
        """

        await self._lookup_series(ctx, search, False, "NOVEL")
