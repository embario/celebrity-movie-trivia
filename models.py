from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


movie_and_cast = db.Table(
    'movie_and_cast',
    db.Column('movie_id', db.Integer, db.ForeignKey('movie.id'), primary_key=True),
    db.Column('movie_person_id', db.Integer, db.ForeignKey('movie_person.id'), primary_key=True),
)


class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    cast = db.relationship("MoviePerson", secondary=movie_and_cast, lazy='subquery', backref=db.backref('movies', lazy=True))

    def __repr__(self):
        return f"<Movie {self.id} - {self.title}>"


class MoviePerson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    profile_path_ext = db.Column(db.String, nullable=True)
    profile_pic = db.Column(db.String, nullable=True)
    character = db.Column(db.String, nullable=True)

    def __repr__(self):
        return f"<MoviePerson {self.id} - {self.name}>"


class TriviaScore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    num_correct = db.Column(db.Integer, nullable=False)
    num_incorrect = db.Column(db.Integer, nullable=False)
    num_answers = db.Column(db.Integer, nullable=False)