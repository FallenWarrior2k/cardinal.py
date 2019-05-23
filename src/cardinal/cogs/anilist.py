from calendar import month_name

from aiohttp import ClientSession
from discord import Embed
from discord.ext import commands
from markdownify import markdownify as md

from .basecog import BaseCog

format_repr = {
    'TV': 'TV',
    'TV_SHORT': 'TV Short',
    'MOVIE': 'Movie',
    'SPECIAL': 'Special',
    'OVA': 'OVA',
    'ONA': 'ONA',
    'MUSIC': 'Music',
    'MANGA': 'Manga',
    'NOVEL': 'Light Novel',
    'ONE_SHOT': 'One Shot',
}


class FuzzyDate:
    def __init__(self, **kwargs):
        self.year = kwargs.get('year')

        if self.year:
            self.month = kwargs.get('month')

            if self.month:
                self.day = kwargs.get('day')

    def __bool__(self):
        return bool(self.year)

    def __str__(self):
        if hasattr(self, 'day') and self.day:
            return '{} {}, {}'.format(month_name[self.month], self.day, self.year)

        if hasattr(self, 'month') and self.month:
            return '{} {}'.format(month_name[self.month], self.year)

        if self.year:
            return str(self.year)

        return 'unknown'


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

    return ' '.join(part for part in name.split('_')).capitalize()


def make_embed(item):
    titles = item['title']
    title_english = titles['english']
    title_romaji = titles['romaji']
    if title_english and title_romaji and (title_english != title_romaji):
        title = '{} (_{}_)'.format(title_english, title_romaji)

    else:
        title = title_english or title_romaji  # At least one of these should be non-empty

    embed = Embed(
        title=title,
        colour=0x02A9FF,
        description='[AniList]({siteUrl}) | '
                    '[MyAnimeList](https://myanimelist.net/anime/{idMal})'.format_map(item)
    )

    embed.set_thumbnail(url=item['coverImage']['large'])
    embed.set_footer(
        text='Powered by AniList',
        icon_url='https://anilist.co/img/icons/favicon-32x32.png'
    )

    score = '{} %'.format(item['averageScore']) if item['averageScore'] else '-'
    embed.add_field(name='Average Score', value=score, inline=False)

    embed.add_field(name='Format', value=format_repr[item['format']])
    embed.add_field(name='Source', value=normalize_ssc(item['source']))

    if 'episodes' in item:
        length_key = 'episodes'
    elif item['format'] == 'NOVEL':
        length_key = 'volumes'
    else:
        length_key = 'chapters'

    embed.add_field(name=length_key.capitalize(), value=item[length_key] or 'unknown')

    embed.add_field(name='Status',
                    value=normalize_ssc(item['status']) or 'unknown')

    embed.add_field(name='Start', value=str(FuzzyDate(**item['startDate'])))
    embed.add_field(name='End', value=str(FuzzyDate(**item['endDate'])))

    embed.add_field(name='Genres', value=', '.join(item['genres']), inline=False)
    embed.add_field(name='Description', value=md(item['description']), inline=False)

    return embed


class Anilist(BaseCog):
    """
    Anilist lookup commands.
    """

    def __init__(self, bot):
        super().__init__(bot)
        self.http = ClientSession(loop=self.bot.loop)

    query = """
    query(
        $isAnime: Boolean!,
        $format: [MediaFormat],
        $search: String!
    ) {
        anime: Media(
            type: ANIME,
            search: $search,
            sort: POPULARITY_DESC
        ) @include(if: $isAnime) {
            ...baseFields
            ...animeFields
        }

        manga: Media(
            type: MANGA,
            format_in: $format,
            search: $search,
            sort: POPULARITY_DESC
        ) @skip(if: $isAnime) {
                ...baseFields
                ...mangaFields
        }
    }

    fragment baseFields on Media {
        title { english romaji }
        coverImage { large }
        averageScore
        genres
        description

        format
        source

        status
        startDate { year month day }
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

    async def execute_graphql(self, **variables):
        body = {
            'query': self.query,
            'variables': variables
        }

        async with self.http.post('https://graphql.anilist.co', json=body) as res:
            res_body = await res.json()

        return res_body['data']

    @commands.command(aliases=['ani', 'al', 'anilist'])
    async def anime(self, ctx, *, search: str):
        """
        Look up an anime on Anilist.

        Arguments:
             - search: Term to search for.
        """

        async with ctx.typing():
            data = await self.execute_graphql(isAnime=True, search=search)

        await ctx.send(embed=make_embed(data['anime']))

    @commands.command()
    async def manga(self, ctx, *, search: str):
        """
        Look up a manga on Anilist.

        Arguments:
             - search: Term to search for.
        """

        async with ctx.typing():
            data = await self.execute_graphql(isAnime=False,
                                              format=['MANGA', 'ONE_SHOT'],
                                              search=search)

        await ctx.send(embed=make_embed(data['manga']))

    @commands.command(aliases=['lightnovel', 'novel'])
    async def ln(self, ctx, *, search: str):
        """
        Look up a light novel on Anilist.

        Arguments:
            - search: Term to search for.
        """

        async with ctx.typing():
            data = await self.execute_graphql(isAnime=False,
                                              format=['NOVEL'],
                                              search=search)

        await ctx.send(embed=make_embed(data['manga']))
