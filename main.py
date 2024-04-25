import json
import random
import os
import sys
from datetime import timedelta
from flask import Flask, render_template, redirect, url_for, flash, request, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_session import Session
from sqlalchemy import JSON


######################################################################
#                        Инициализация переменных                    #
app = Flask(__name__)

# Название базы данных
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=60)

Session(app)
db = SQLAlchemy(app)
######################################################################


# Создание модели Игр
class Games(db.Model):
    """База данных содержит элементы для отображения информации об играх"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Integer)
    description = db.Column(db.Text)
    genre = db.Column(db.Text)
    date = db.Column(db.Text)
    platform = db.Column(db.Text)
    author = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer)
    dir_photo = db.Column(db.String)


# Создание модели Пользователя
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)


class News(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    content = db.Column(db.String, nullable=False)


class Messages(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    text = db.Column(db.String, nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False)
    game = db.relationship('Games', backref=db.backref('messages', lazy=True))


# Создание администраторской панели
class MyAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for("login"))


class AdminView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for("login"))


# Создание админ панели
admin = Admin(app, index_view=MyAdminIndexView())

#Добавление таблиц из базы данных в админ панель
admin.add_view(AdminView(User, db.session))
admin.add_view(AdminView(Games, db.session))
admin.add_view(AdminView(News, db.session))
admin.add_view(AdminView(Messages, db.session))

# Создание менеджера входа
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Создание маршрута для страницы входа
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('admin.index'))
        else:
            flash('Неправильное имя пользователя или пароль', 'error')

    return render_template('login.html')


# Создание маршрута для выхода
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


######################################################################
#                          Основная часть сайта                      #

@app.route("/")
def index():
    games = Games.query.all()
    games = random.sample(games, 10)
    return render_template("index.html", games = games)


@app.route("/news")
def news():
    elements = News.query.all()
    return render_template("news.html", elements=elements)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/games")
def games_list():
    games = Games.query.all()
    return render_template("games.html", games=games)


@app.route("/game/<id>")
def game(id):
    game1 = Games.query.filter_by(id=id).first()
    photos = [photo for photo in os.listdir("static/image/" + game1.dir_photo) if photo != "main.jpg"]
    if "rating" not in session:
        session["rating"] = dict()
    if game1.id not in session["rating"]:
        session["rating"][game1.id] = 0
    print(session["rating"])
    print(photos)
    return render_template("game.html", game1=game1, photos=photos, ratings=session["rating"][game1.id])


@app.route("/search", methods=["POST"])
def search():
    search_query = request.form['search_query']
    games = Games.query.filter(Games.name.like(f'%{search_query}%')).all()
    if len(games) == 1:
        photos = [photo for photo in os.listdir("static/image/" + games[0].dir_photo) if photo != "main.jpg"]
        print(photos)
        return render_template("game.html", game1=games[0], photos=photos)
    else:
        return render_template("games.html", games=games)


@app.route("/add_to_cart/<id>", methods=["POST"])
def add_to_cart(id):
    game1 = Games.query.filter_by(id=id).first()
    if "cart" not in session:
        session["cart"] = []

    if game1.id not in [i.id for i in session["cart"]]:
        session["cart"].append(game1)

    print(session["cart"])
    return jsonify(success=True)


@app.route("/remove_from_cart/<id>", methods=["POST"])
def remove(id):
    games=[]
    g = Games.query.filter_by(id=id).first()
    for i in session["cart"]:
        if i.id != g.id:
            games.append(i)
    session["cart"] = games

    return jsonify(success=True)


@app.route("/cart", methods=["POST", "GET"])
def cart():
    total_price = 0
    if "cart" not in session:
        session["cart"] = []
    for i in session["cart"]:
        total_price += i.price
    print(session["cart"])
    return render_template("cart.html", games=session["cart"], total_price=total_price)


@app.route("/community/<game_id>", methods=['GET'])
def community(game_id):
    if "id" not in session:
        session["id"] = random.randint(0, 65528)
    games = Games.query.filter_by(id=game_id).first()
    messages = games.messages
    return render_template("community.html", messages=messages, name=session["id"], game_id=game_id)


@app.route("/add_message/<game_id>", methods=["POST"])
def add_message(game_id):
    name = session["id"]
    text = request.json["text"]
    new_message = Messages(name=name, text=text, game_id=game_id)
    db.session.add(new_message)
    db.session.commit()
    return jsonify(name = name, text = text, id = new_message.id)


@app.route('/rate', methods=['POST'])
def rate():
    star_id = request.json['star_id']
    game_id = request.json['game_id']
    print(session["rating"])
    session["rating"][int(game_id)] = star_id

    print(game_id, star_id)

    return jsonify(success=True)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
