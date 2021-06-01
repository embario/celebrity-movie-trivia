import unittest
from app import app
from models import db, Movie, MoviePerson, TriviaScore
import utils

EXAMPLE_MOVIE_ID = 603  # Matrix


class Tests(unittest.TestCase):
    index_url = "/"
    start_game_url = '/start_game'
    submit_game_url = '/submit_game_url'

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_index_only_get(self):
        resp = self.client.get(self.index_url)
        self.assertEqual(resp.status_code, 200)
        resp = self.client.post(self.index_url, data={'something': 1})
        self.assertEqual(resp.status_code, 405)

    def test_start_game_with_get_params(self):
        resp = self.client.get(f"{self.start_game_url}?movie_id={EXAMPLE_MOVIE_ID}")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Movie.query.filter_by(id=EXAMPLE_MOVIE_ID) is not None)

    def test_start_game_with_post_data(self):
        resp = self.client.post(self.start_game_url, data={'movie_id': EXAMPLE_MOVIE_ID})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Movie.query.filter_by(id=EXAMPLE_MOVIE_ID) is not None)

    def test_score_game(self):
        test_movie, _ = utils.get_or_create(Movie, id=1, title='test')
        test_correct_mp1, _ = utils.get_or_create(MoviePerson, id=1, name='test movie person')
        test_correct_mp2, _ = utils.get_or_create(MoviePerson, id=2, name='test movie person')
        test_wrong_mp1, _ = utils.get_or_create(MoviePerson, id=3, name='test movie person')
        test_wrong_mp2, _ = utils.get_or_create(MoviePerson, id=4, name='test movie person')
        all_mp_ids = [k.id for k in [test_correct_mp1, test_correct_mp2, test_wrong_mp1, test_wrong_mp2]]

        test_movie.cast.append(test_correct_mp1)
        test_movie.cast.append(test_correct_mp2)
        db.session.commit()

        before_score_count = TriviaScore.query.count()
        score, user_right_choices, user_wrong_choices, all_choices, correct_answers = utils.score_game(
            test_movie,
            [test_correct_mp1.id, test_wrong_mp1.id],
            all_mp_ids,
        )

        db.session.add(score)
        db.session.commit()
        self.assertEqual(TriviaScore.query.count(), before_score_count + 1)
        self.assertEqual(user_right_choices, [test_correct_mp1])
        self.assertEqual(user_wrong_choices, [test_wrong_mp1])
        self.assertEqual(correct_answers, [test_correct_mp1, test_correct_mp2])
