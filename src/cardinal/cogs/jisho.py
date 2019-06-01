from urllib.parse import quote_plus

from aiohttp import ClientSession
from discord.ext.commands import command

from ..utils import maybe_send
from .basecog import BaseCog

JISHO_API_URL = "https://jisho.org/api/v1/search/words"
JISHO_WEB_BASE = "https://jisho.org/search/{}"
comma_join = ', '.join
newline_join = '\n'.join


def _build_web_link(term):
    """
    Build a URL string that links to the web search page for the
    given term. The term is escaped before being embedded into the
    URL template.

    Args:
        term (str): Term to generate link for.

    Returns:
        str: URL for looking up the term in Jisho's web interface.
    """
    return JISHO_WEB_BASE.format(quote_plus(term))


def _format_word(word):
    kanji = word['word']
    reading = word['reading']

    if kanji and reading:
        return f'**{kanji}** - {reading}'  # Both defined => output both
    elif kanji or reading:
        return f'**{kanji or reading}**'  # Just one defined => output whichever is


def _format_sense(sense):
    text = comma_join(sense['english_definitions'])

    if sense['parts_of_speech']:
        text += f' ({comma_join(map(str.lower, sense["parts_of_speech"]))})'

    return text


def _build_text_response(result):
    """
    Build a text response from a single Jisho API result.

    Args:
        result (dict): Result data to textualize.

    Returns:
        str: Human-readable Markdown string representing the result.
    """
    text = comma_join(_format_word(word) for word in result['japanese'])
    text += '\n'
    text += newline_join(f'• {_format_sense(sense)}' for sense in result['senses'])
    return text


class Jisho(BaseCog):
    """
    Look up terms on Jisho (https://jisho.org),
    a Japanese-English dictionary.
    """

    def __init__(self, bot):
        super().__init__(bot)
        # See Anilist cog
        self.http = ClientSession(loop=self.bot.loop, raise_for_status=True)

    async def _lookup_term(self, term):
        """
        Look up a given term with Jisho's API.

        Args:
            term (str): Term to look up.

        Returns:
            typing.List[dict]: Results returned by the API.
        """
        query_params = {'keyword': quote_plus(term)}

        async with self.http.get(JISHO_API_URL, params=query_params) as resp:
            body = await resp.json()

        return body['data']

    @command(aliases=['jp', 'jpdict', 'japanese'])
    async def jisho(self, ctx, *, term: str):
        async with ctx.typing():
            results = await self._lookup_term(term)

        if not results:
            await maybe_send(ctx, f'Could not find any results for `{term}`.')
            return

        result, *_ = results
        result_text = _build_text_response(result)
        result_text += f'\n\nSee also: <{_build_web_link(term)}>'
        await ctx.send(result_text)
