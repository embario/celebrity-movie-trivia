import logging
import random

from flask import request, render_template, redirect, url_for, flash, Response, session

from celebrity_movie_trivia import app
from celebrity_movie_trivia.utils import get_or_create, TMDB_URLS, GAME_NUM_OPTIONS, GAME_NUM_CORRECT_OPTIONS, make_tmdb_request, get_wrong_actors, score_game
from celebrity_movie_trivia.models import db, User, Movie, MoviePerson, TriviaScore

logger = logging.getLogger(__name__)
logging.basicConfig(level='INFO')


@app.route('/movie_search')
def search_movies():
    logger.info(f'Movie Search Query: {request.query_string}')
    query_string = request.query_string.decode('utf-8')
    if query_string:
        resp = make_tmdb_request(TMDB_URLS['movie_search'], query_string)
        data = resp.json()['results']
    else:
        return {}

    results = [{'id': d['id'], 'text': f"{d['title']} ({d['release_date'].split('-')[0]})"} for d in data]
    logger.info(results)
    return {'results': results}


@app.route('/submit_game', methods=['POST'])
def submit_game():
    logger.info(request.form)
    form_data = dict(request.form)
    form_data.pop('Submit')
    movie = Movie.query.filter_by(id=form_data.pop('movie_id')).first()
    actor_ids = [v for k, v in form_data.items() if not k.isdigit()]
    user_input = [k for k, v in form_data.items() if k.isdigit()]
    score, right_choices, wrong_choices, all_choices, correct_answers = score_game(movie, user_input, actor_ids)
    db.session.add(score)
    db.session.commit()

    # Now add in Character names to help remember people!
    data = make_tmdb_request(TMDB_URLS['get_cast_by_movie'], movie.id).json()['cast']
    for choice in all_choices:
        try:
            choice.character = next(x['character'] for x in data if choice.id == x['id'])
        except:
            continue

    return render_template(
        'results.html',
        score=score,
        movie=movie,
        right_choices=right_choices,
        wrong_choices=wrong_choices,
        all_choices=all_choices,
        correct_answers=correct_answers,
    )


@app.route("/start_game", methods=['GET', 'POST'])
def start_game():
    logger.info(f"NUM CORRECT: {GAME_NUM_CORRECT_OPTIONS}")

    if GAME_NUM_CORRECT_OPTIONS:
        num_correct = int(GAME_NUM_CORRECT_OPTIONS)
    else:
        num_correct = random.randint(1, GAME_NUM_OPTIONS)

    num_wrong = GAME_NUM_OPTIONS - num_correct

    if request.method == "GET":
        movie_id = request.query_string.decode('utf-8').replace("movie_id=", "")
    else:
        movie_id = request.form['movie_id']

    if not movie_id:
        flash("Nothing was submitted.")
        return render_template("index.html")

    # Get Movie for details.
    data = make_tmdb_request(TMDB_URLS['get_movie_by_id'], movie_id).json()
    movie, _ = get_or_create(Movie, id=data['id'], title=data['title'])
    logger.info(f"Generating Correct ({num_correct}) / Incorrect ({num_wrong}) Options for {movie.title}...")

    # Grab Correct Movie Actors here.
    data = make_tmdb_request(TMDB_URLS['get_cast_by_movie'], movie_id).json()
    for mp_data in data['cast']:
        mp, _ = get_or_create(
            MoviePerson,
            id=mp_data['id'],
            name=mp_data['name'],
            profile_path_ext=mp_data['profile_path'],
        )
        movie.cast.append(mp)

    correct_persons = movie.cast
    random.shuffle(correct_persons)

    # Grab Wrong Movie Actors here (make sure they're different from correct options).
    wrong_persons = get_wrong_actors(num_wrong, correct_persons, movie_id)

    # Mix them all up and render!
    options = correct_persons[:num_correct] + wrong_persons
    random.shuffle(options)

    for option in options:
        if option.profile_pic is None and option.profile_path_ext is not None:
            resp = make_tmdb_request(TMDB_URLS['get_profile_pic'], option.profile_path_ext)
            with open(f"./static/img{option.profile_path_ext}", 'wb') as f:
                f.write(resp.content)
                option.profile_pic = f.name

    db.session.commit()
    return render_template("game.html", options=options, movie=movie)


@app.route("/score")
def score():
    scores = TriviaScore.query.all()
    return render_template('scores.html', scores=scores)


@app.route('/signup', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')

    if request.method == 'POST':
        if User.query.filter_by(username=request.form['username']).first() is not None:
            flash("A User with that username already exists.")
            return render_template('/signup.html')

        new_user = User(username=request.form['username'], password=request.form['password'])
        db.session.add(new_user)
        db.session.commit()
        flash(f"User successfully created. Welcome {new_user.username}!")
        return redirect(url_for('index'))


@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)
