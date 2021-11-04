from flask import Flask, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
import smtplib

from forms import CreatePostForm, CommentPostForm
from flask_gravatar import Gravatar
import datetime
import os


app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
app.config['CKEDITOR_PKG_TYPE'] = 'basic'
bootstrap = Bootstrap(app)

login_manager = LoginManager()
login_manager.init_app(app)
today = datetime.datetime.today()
EMAIL = os.environ.get("EMAIL")
PASSWORD = os.environ.get("PASSWORD")

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)


def send_email(name, email, number, message):
    with smtplib.SMTP("smtp.gmail.com") as connection:
        connection.starttls()
        connection.login(user=EMAIL, password=PASSWORD)
        connection.sendmail(
            from_addr=EMAIL,
            to_addrs=email,
            msg=f"Subject: SoriOner's Blog Website Contact\n\n"
                f"{name} want to hear from you\n"
                f"{name} Phone Number: {number}\n"
                f"message: {message}"
        )


##CONFIGURE TABLES
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(1000), nullable=False)
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="author")

    def check_password(self, secret):
        return check_password_hash(self.password, secret)


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    author = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="parent_post")



class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    date = db.Column(db.String(250), nullable=False)
    post_number = db.Column(db.Integer, db.ForeignKey("blog_posts.id"), nullable=False)
    parent_post = relationship("BlogPost", back_populates="comments")
    author = relationship("User", back_populates="comments")


db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts, year=today.year)


@app.route('/register', methods=["POST", "GET"])
def register():
    if request.method == "POST":
        if User.query.filter_by(email=request.form["email"]).first():
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for("login"))
        else:
            new_user = User(
                name=request.form["name"],
                email=request.form["email"],
                password=generate_password_hash(request.form["password"], method="pbkdf2:sha256", salt_length=8)
            )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for("get_all_posts"))
    return render_template("register.html", year=today.year)


@app.route('/login', methods=["POST", "GET"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(email=request.form["email"]).first()
        password = request.form["password"]
        if user.check_password(password):
            login_user(user)
            return redirect(url_for("get_all_posts"))
    return render_template("login.html", year=today.year)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:index>", methods=["POST", "GET"])
def show_post(index):
    form = CommentPostForm()
    requested_post = BlogPost.query.get(index)
    try:
        if form.validate_on_submit():
            new_comment = Comment(
                post_number=index,
                text=form.body.data,
                author_id=current_user.id,
                date=today.strftime("%m/%d/%Y, %H:%M:%S")
            )
            db.session.add(new_comment)
            db.session.commit()
            return render_template("post.html", post=requested_post, form=form, year=today.year)
    except AttributeError:
        flash("You need to log in or register to comment.")
        return redirect(url_for("login"))
    return render_template("post.html", post=requested_post, form=form, year=today.year)


@app.route("/about")
def about():
    return render_template("about.html", year=today.year)


@app.route("/contact", methods=["POST", "GET"])
def contact():
    h1 = "Contact Me"
    return render_template("contact.html", h1=h1, year=today.year)


@app.route('/message', methods=['POST'])
def message():
    h1 = "Email Sent"
    name = request.form['name']
    email = request.form['email']
    phone = request.form['phone']
    message = request.form['message']
    try:
        send_email(name, email, phone, message)
    except Exception as e:
        print(e)

    return render_template("contact.html", date=today, h1=h1, year=today.year)


@app.route("/add_new_post", methods=['POST', 'GET'])
@login_required
def add_new_post():
    if current_user.id == 1:
        form = CreatePostForm()
        if form.validate_on_submit():
            new_post = BlogPost(author_id=current_user.id,
                                title=form.title.data,
                                subtitle=form.subtitle.data,
                                img_url=form.img_url.data,
                                body=form.body.data,
                                date=f"{today.strftime('%B')} {today.day}, {today.year}")
            db.session.add(new_post)
            db.session.commit()
            return redirect("/")
        return render_template("make-post.html", form=form, h1="Create a Post", year=today.year)
    else:
        return render_template("unauthorized.html"), 401



@app.route("/edit-post/<post_id>", methods=["POST", "GET"])
@login_required
def edit_post(post_id):
    if current_user.id == 1:
        post = BlogPost.query.get(int(post_id))
        form = CreatePostForm(title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body)
        h1 = "Edit Post"
        if form.validate_on_submit():
            post.title = form.title.data
            post.body = form.body.data
            post.subtitle = form.subtitle.data
            post.author = form.author.data
            post.img_url = form.img_url.data
            db.session.commit()
            return redirect("/")
        return render_template("make-post.html", form=form, h1=h1, year=today.year)
    else:
        return render_template("unauthorized.html"), 401


@app.route("/delete/<int:post_id>")
@login_required
def delete_post(post_id):
    if current_user.id == 1:
        post_to_delete = BlogPost.query.get(post_id)
        db.session.delete(post_to_delete)
        db.session.commit()
        return redirect(url_for('get_all_posts'))
    else:
        return render_template("unauthorized.html"), 401


def footer():
    return render_template("footer.html", year=today.year)

if __name__ == '__main__':
    app.run(debug=True)