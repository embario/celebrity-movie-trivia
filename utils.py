import os
import logging
import requests
import random
import ipdb
from models import db, Movie, MoviePerson, TriviaScore

logger = logging.getLogger(__name__)

API_KEY = os.getenv("TMDB_API_KEY")
GAME_NUM_OPTIONS = int(os.getenv("GAME_NUM_OPTIONS", 5))
TMDB_API_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_URL = "https://image.tmdb.org/t/p/w500"
TMDB_URLS = {
    'movie_search': f"{TMDB_API_URL}/search/movie",
    'get_movie_by_id': f"{TMDB_API_URL}/movie/{{movie_id}}",
    "get_movie_recs": f"{TMDB_API_URL}/movie/{{movie_id}}/recommendations",
    'get_cast_by_movie': f"{TMDB_API_URL}/movie/{{movie_id}}/credits",
    'get_profile_pic': f"{TMDB_IMAGE_URL}{{image_path}}",
}


def make_tmdb_request(url, data):
    if url == TMDB_URLS['movie_search']:
        url = f"{url}?query={data}&page=1&include_adult=false"
    elif url in [TMDB_URLS['get_movie_recs'], TMDB_URLS['get_movie_by_id'], TMDB_URLS['get_cast_by_movie']]:
        url = f"{url.format(movie_id=data)}"
    elif url == TMDB_URLS['get_profile_pic']:
        url = f"{url.format(image_path=data)}"
    else:
        raise ValueError(f"Unrecognized HTTP Requests (URL '{url}')")

    try:
        logger.info(f"Querying '{url}'...")
        resp = requests.get(url, params={'api_key': API_KEY, 'language': 'en-US'})
        assert resp.status_code == 200
    except AssertionError:
        logger.warning(f"Failed Request: {resp.status_code, resp.reason}")
        raise
    except Exception as e:
        logger.warning(f"Something unexpected happened: {e}")
        raise

    logger.debug(resp.content)
    return resp


def get_or_create(clz, **kwargs):
    existing = clz.query.filter_by(id=kwargs['id']).first()
    if existing:
        return existing, False

    obj = clz(**{'id': int(kwargs['id']), **kwargs})
    db.session.add(obj)
    return obj, True


def get_wrong_actors(num, correct_persons, movie_id):
    """ Given an integer num, a list of correct persons IDs, and a Movie ID, generate
    a list of wrong actors from other movies similar to movie_id. While we're at it,
    we might as well add any Movie and MoviePerson instances we find to the Database
    for later caching.
    """
    if num <= 0:
        return []

    results = set()
    remaining = num
    movie_recs = []
    correct_ids = [c.id for c in correct_persons]

    # First grab all movie recs.
    resp = make_tmdb_request(TMDB_URLS['get_movie_recs'], movie_id)
    for data in resp.json()['results']:
        rec, _ = get_or_create(Movie, id=data['id'], title=data['title'])
        movie_recs.append(rec)

    random.shuffle(movie_recs)

    # Now loop through and fill up our 'wrong' results.
    while(movie_recs and remaining > 0):
        movie = movie_recs.pop(0)
        resp = make_tmdb_request(TMDB_URLS['get_cast_by_movie'], movie.id)
        actors = []

        for mp_data in resp.json()['cast']:
            if mp_data['id'] not in correct_ids:
                mp, _ = get_or_create(
                    MoviePerson,
                    id=mp_data['id'],
                    name=mp_data['name'],
                    profile_path_ext=mp_data['profile_path'],
                )
                movie.cast.append(mp)
                actors.append(mp)

        random.shuffle(actors)
        results.update(actors[:random.randint(1, remaining)])
        remaining -= len(results)

    return list(results)[:num]


def score_game(movie, user_input, actor_ids):
    """ 
    Given a dictionary containing the checks made on MoviePerson IDs, determine the score for the user.
    """
    right_choices = []
    all_choices = MoviePerson.query.filter(MoviePerson.id.in_(actor_ids)).all()
    user_input = MoviePerson.query.filter(MoviePerson.id.in_(user_input)).all()
    correct_answers = [mp for mp in all_choices if mp in movie.cast]

    for mp in user_input:
        if mp in correct_answers:
            right_choices.append(mp)

    score = TriviaScore(num_correct=len(right_choices), num_answers=len(correct_answers))
    return score, right_choices, all_choices
