# -*- coding: utf-8 -*-
"""
This module provides the default implementation of the `compute_score` parameter in
:meth:`~subliminal.api.ProviderPool.download_best_subtitles` and :func:`~subliminal.api.download_best_subtitles`.

.. note::

    To avoid unnecessary dependency on `sympy <http://www.sympy.org/>`_ and boost subliminal's import time, the
    resulting scores are hardcoded here and manually updated when the set of equations change.

Available matches:

  * hash
  * title
  * year
  * series
  * season
  * episode
  * release_group
  * format
  * audio_codec
  * resolution
  * hearing_impaired
  * video_codec
  * imdb_id
  * tvdb_id

"""
from __future__ import division, print_function
import logging

from .video import Episode, Movie

logger = logging.getLogger(__name__)


#: Scores for episodes
episode_scores = {'hash': 371, 'series': 186, 'year': 93, 'season': 31, 'episode': 31, 'release_group': 15,
                  'format': 7, 'audio_codec': 3, 'resolution': 2, 'hearing_impaired': 2, 'video_codec': 2, 'title': 1}

#: Scores for movies
movie_scores = {'hash': 71, 'title': 36, 'year': 18, 'release_group': 9,
                'format': 4, 'audio_codec': 2, 'resolution': 1, 'hearing_impaired': 1, 'video_codec': 1}


def get_scores(video):
    """Get the scores dict for the given `video`.

    This will return either :data:`episode_scores` or :data:`movie_scores` based on the type of the `video`.

    :param video: the video to compute the score against.
    :type video: :class:`~subliminal.video.Video`
    :return: the scores dict.
    :rtype: dict

    """
    if isinstance(video, Episode):
        return episode_scores
    elif isinstance(video, Movie):
        return movie_scores

    raise ValueError('video must be an instance of Episode or Movie')


def compute_score(subtitle, video, hearing_impaired=None):
    """Compute the score of the `subtitle` against the `video` with `hearing_impaired` preference.

    :func:`compute_score` uses the :meth:`Subtitle.get_matches <subliminal.subtitle.Subtitle.get_matches>` method and
    applies the scores (either from :data:`episode_scores` or :data:`movie_scores`) after some processing.

    :param subtitle: the subtitle to compute the score of.
    :type subtitle: :class:`~subliminal.subtitle.Subtitle`
    :param video: the video to compute the score against.
    :type video: :class:`~subliminal.video.Video`
    :param bool hearing_impaired: hearing impaired preference.
    :return: score of the subtitle.
    :rtype: int

    """
    logger.info('Computing score of %r for video %r with %r', subtitle, video, dict(hearing_impaired=hearing_impaired))

    # get the scores dict
    scores = get_scores(video)
    logger.debug('Using scores %r', scores)

    # get the matches
    matches = subtitle.get_matches(video)
    logger.debug('Found matches %r', matches)

    # on hash match, discard everything else
    if 'hash' in matches:
        logger.debug('Keeping only hash match')
        matches &= {'hash'}

    # handle equivalent matches
    if isinstance(video, Episode):
        if 'imdb_id' in matches:
            logger.debug('Adding imdb_id match equivalents')
            matches |= {'series', 'year', 'season', 'episode', 'title'}
        if 'tvdb_id' in matches:
            logger.debug('Adding tvdb_id match equivalents')
            matches |= {'series', 'year'}

    # handle hearing impaired
    if hearing_impaired is not None and subtitle.hearing_impaired == hearing_impaired:
        logger.debug('Matched hearing_impaired')
        matches.add('hearing_impaired')

    # compute the score
    score = sum((scores.get(match, 0) for match in matches))
    logger.info('Computed score %r with final matches %r', score, matches)

    # ensure score is within valid bounds
    assert 0 <= score <= scores['hash'] + scores['hearing_impaired']

    return score


def solve_episode_equations():
    from sympy import Eq, solve, symbols

    hash, series, year, season, episode, release_group = symbols('hash series year season episode release_group')
    format, audio_codec, resolution, video_codec = symbols('format audio_codec resolution video_codec')
    title, hearing_impaired = symbols('title hearing_impaired')

    equations = [
        # hash is best
        Eq(hash, series + year + season + episode + release_group + format + audio_codec + resolution + video_codec +
           title),

        # series counts for the most part in the total score
        Eq(series, year + season + episode + release_group + format + audio_codec + resolution + video_codec + title +
           1),

        # year is the second most important part
        Eq(year, season + episode + release_group + format + audio_codec + resolution + video_codec + title + 1),

        # season is important too
        Eq(season, release_group + format + audio_codec + resolution + video_codec + title + 1),

        # episode is equally important to season
        Eq(episode, season),

        # release group is the next most wanted match
        Eq(release_group, format + audio_codec + resolution + video_codec + 1),

        # format counts as much as audio_codec, resolution and video_codec
        Eq(format, audio_codec + resolution + video_codec),

        # audio_codec is more valuable than video_codec
        Eq(audio_codec, video_codec + 1),

        # resolution counts as much as video_codec
        Eq(resolution,  video_codec),

        # hearing impaired is as much as resolution
        Eq(hearing_impaired, resolution),

        # video_codec counts more than the title
        Eq(video_codec,  title + 1),

        # title is that little extra boost
        Eq(title, 1),
    ]

    return solve(equations, [hash, series, year, season, episode, release_group, format, audio_codec, resolution,
                             hearing_impaired, video_codec, title])


def solve_movie_equations():
    from sympy import Eq, solve, symbols

    hash, title, year, release_group = symbols('hash title year release_group')
    format, audio_codec, resolution, video_codec = symbols('format audio_codec resolution video_codec')
    hearing_impaired = symbols('hearing_impaired')

    equations = [
        # hash is best
        Eq(hash, title + year + release_group + format + audio_codec + resolution + video_codec),

        # title counts for the most part in the total score
        Eq(title, year + release_group + format + audio_codec + resolution + video_codec + 1),

        # year is the second most important part
        Eq(year, release_group + format + audio_codec + resolution + video_codec + 1),

        # release group is the next most wanted match
        Eq(release_group, format + audio_codec + resolution + video_codec + 1),

        # format counts as much as audio_codec, resolution and video_codec
        Eq(format, audio_codec + resolution + video_codec),

        # audio_codec is more valuable than video_codec
        Eq(audio_codec, video_codec + 1),

        # resolution counts as much as video_codec
        Eq(resolution,  video_codec),

        # hearing impaired is as much as resolution
        Eq(hearing_impaired, resolution),

        # video_codec counts more than the title
        Eq(video_codec,  1),
    ]

    return solve(equations, [hash, title, year, release_group, format, audio_codec, resolution, hearing_impaired,
                             video_codec])
