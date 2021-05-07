import re
from dataclasses import dataclass
from logging import getLogger
from typing import List, Optional

from aiohttp import ClientError, ClientSession
from aioitertools import chain as achain
from discord import Colour, Embed
from discord.ext.commands import Cog, Context, command

# from ..utils import maybe_send

_SAUCENAO_URL = 'https://saucenao.com/search.php'
# "In-depth" explanation available at https://saucenao.com/user.php?page=search-api
_SAUCENAO_PARAMS_BASE = {
    'output_type': 2,  # Set response type to JSON
    'db': 999,  # Search all available indexes
    'numres': 1  # Return exactly one result
}
# Dumbed-down URL RE
# Cheapo trimming of <> embed prevention or bars from spoiler tags
# Doing it "correctly" would require copy-pasting the pattern multiple times
# or building a full-on CFG, which seemed a tad overkill
_URL_RE = re.compile(r'https?://[^\s>|]+')

_logger = getLogger(__name__)


def _extract_urls_from_message(msg):
    match_iter = _URL_RE.finditer(msg.content)
    yield from (match.group(0) for match in match_iter)
    yield from (attachment.url for attachment in msg.attachments)


@dataclass
class _ResultMeta:
    links: List[str]
    artist: Optional[str] = None


_PIXIV_SOURCE_TEMPLATE = '[Pixiv](https://www.pixiv.net/en/artworks/{pixiv_id})'
_PIXIV_MEMBER_TEMPLATE = '[{member_name}](https://www.pixiv.net/en/users/{member_id})'


def _handle_pixiv(data: dict) -> _ResultMeta:
    image = _PIXIV_SOURCE_TEMPLATE.format_map(data)
    artist = _PIXIV_MEMBER_TEMPLATE.format_map(data)
    return _ResultMeta([image], artist)


_DANBOORU_POST_TEMPLATE = '[Danbooru](https://danbooru.donmai.us/post/show/{danbooru_id})'
_GELBOORU_POST_TEMPLATE = \
    '[Gelbooru](https://gelbooru.com/index.php?page=post&s=view&id={gelbooru_id})'


def _handle_danbooru(data: dict) -> _ResultMeta:
    links = [_DANBOORU_POST_TEMPLATE.format_map(data)]
    if (gelbooru_id := data.get('gelbooru_id')) is not None:
        links.append(_GELBOORU_POST_TEMPLATE.format(gelbooru_id=gelbooru_id))
    # TODO: Is this really useful? It just 403s for many things.
    # Generally, the URLs on the booru pages are far more useful
    # This can actually be an empty string in some cases, so exclude all falsy values
    if source := data.get('source'):
        links.append(f'[Source]({source})')

    artist = data.get('creator')
    return _ResultMeta(links, artist)


def _handle_unspecified(data: dict) -> _ResultMeta:
    return _ResultMeta(data.get('ext_urls', []))


# Mapping from SauceNAO index ID to handler function
# TODO: Add handlers for other indices
_DATA_HANDLERS = {
    5: _handle_pixiv, 9: _handle_danbooru
}


def _extract_meta_from_sauce_result(result: dict) -> _ResultMeta:
    data_handler = _DATA_HANDLERS.get(result['header']['index_id'], _handle_unspecified)
    return data_handler(result['data'])


@dataclass
class _SauceResult:
    similarity: str
    thumbnail: str
    meta: _ResultMeta

    def as_embed(self) -> Embed:
        int_similarity = int(self.similarity.split('.')[0])
        # Visually indicate match likelihood by changing the color based on similarity percentage
        # 85% is arbitrarily chosen and I might adjust this in future if I think it's too low or too
        # high
        color = Colour.green() if int_similarity >= 85 else Colour.light_grey()

        # TODO: Set proper title from meta object
        embed = Embed(title='Found potential source.', colour=color)
        embed.set_thumbnail(url=self.thumbnail)
        embed.set_footer(text='Powered by SauceNAO.')

        # At least one entry should always exist
        # If it somehow turns out that's not the case,
        # I can always add a `if links else 'None found' later
        embed.add_field(name='Links', value=' | '.join(self.meta.links), inline=False)
        if self.meta.artist:
            embed.add_field(name='Artist', value=self.meta.artist, inline=True)

        embed.add_field(name='Similarity', value=f'{self.similarity}%', inline=True)

        return embed


class SauceNAO(Cog):
    """
    Look up images in the image reverse search database SauceNAO
    (https://saucenao.com/).
    """

    def __init__(self, http: ClientSession, api_key: str):
        # TODO: Add some kind of SauceNAO API wrapper that keeps track of the rate limit
        # That also requires figuring out when resets happen, i.e. if they happen in set intervals
        # or X time after the first request for that bucket.
        self._http = http
        # TODO: Handle case when no API key is provided
        # A proper solution probably has to wait until command disabling gets implemented, as I
        # can't think of a sensible response to that case beyond just disabling the command and
        # emitting a warning.
        self.params = {
            **_SAUCENAO_PARAMS_BASE, 'api_key': api_key
        }

    async def _is_image(self, url: str) -> bool:
        """
        Tests if a URL points to an image by means of a HEAD request.

        Args:
            url: URL to check.

        Returns:
            True, if the content type starts with 'image/', False otherwise.
        """
        # One extra request for us, but potentially one fewer wasted request against the quota
        try:
            async with self._http.head(url) as resp:
                return resp.content_type.startswith('image/')
        except ClientError:
            # If we can't reach the given URL (if it even is one) for some reason, it's not worth
            # trying to pass it to SauceNAO.
            return False

    async def _url_candidates_from_context(self, ctx: Context):
        # Can't `yield from` in async functions
        async for msg in achain([ctx.message], ctx.history(limit=5, before=ctx.message)):
            for url in _extract_urls_from_message(msg):
                if await self._is_image(url):
                    yield url

    async def _lookup_url(self, url: str) -> Optional[_SauceResult]:
        """
        Look up a given image URL on SauceNAO.

        Args:
            url: URL to look up using SauceNAO.

        Returns:
            An object describing the result if there was one, or None if not.
        """
        # This whole shebang kinda assumes SauceNAO doesn't give us garbage data
        # If it does, it'll most likely result in a KeyError bubbling up into the command.
        # I don't have any hard sources for what fields are supposed to be present either,
        # so even some "good" responses might cause issues.
        # Tying in with that, I should probably add proper logging at some point.
        _logger.info('Querying SauceNAO for URL "%s".', url)
        params = {**self.params, 'url': url}
        async with self._http.get(_SAUCENAO_URL, params=params) as resp:
            resp_data = await resp.json()
            # 0 indicates success, as described on the API page linked at the top of the module
            if not (resp_data['header']['status'] == 0 and resp_data.get('results')):
                return None

            result_json = resp_data['results'][0]
            header = result_json['header']
            return _SauceResult(similarity=header['similarity'],
                                thumbnail=header['thumbnail'],
                                meta=_extract_meta_from_sauce_result(result_json))

    @command(aliases=['sauce', 'source'])
    async def saucenao(self, ctx: Context, url: str = None):
        """
        Look up an URL using SauceNAO.
        If no URL is provided, attachments are checked,
        and then up to five messages before the current one are each
        checked for URLs and then attachments.
        """
        result: Optional[_SauceResult] = None

        async with ctx.typing():
            if url is not None:
                if not await self._is_image(url):
                    await ctx.send(f'"{url}" does not point to a valid image.')
                    return

                result = await self._lookup_url(url)
            else:
                # Sentinel value to test if loop ran at all later
                # Taken from
                # https://python-notes.curiousefficiency.org/en/latest/python_concepts/break_else.html#but-how-do-i-check-if-my-loop-never-ran-at-all
                url = _sentinel = object()
                async for url in self._url_candidates_from_context(ctx):
                    if (result := await self._lookup_url(url)) is not None:
                        break

                if url is _sentinel:
                    await ctx.send('No suitable URLs found.')
                    return

        if result:
            await ctx.send(embed=result.as_embed())
        else:
            await ctx.send('No results found.')
