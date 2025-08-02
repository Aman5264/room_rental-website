from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from flask_bcrypt import Bcrypt
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, FloatField
from wtforms.validators import InputRequired, Length, Email, EqualTo
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
from datetime import datetime
import os
from flask import session
from flask_wtf.file import FileAllowed, FileRequired, MultipleFileField
from wtforms import MultipleFileField
from flask_wtf.file import FileAllowed
from sqlalchemy import ForeignKeyConstraint
from wtforms import DateField, IntegerField, SubmitField
from wtforms.validators import DataRequired, NumberRange


# App setup
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
#app.config['GOOGLE_MAPS_API_KEY'] = '***'
app.config['SECRET_KEY'] = 'supersecretkey'
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Extensions
bcrypt = Bcrypt(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')
    properties = db.relationship('Property', backref='owner', lazy=True)

class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, nullable=False)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    photo_filename = db.Column(db.String(128))
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    photos = db.relationship('Photo', back_populates='room', cascade='all, delete-orphan')

class Photo(db.Model):  # ✅ Now defined outside
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('property.id', name='fk_photo_property_id'), nullable=False)
    room = db.relationship('Property', back_populates='photos')

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    check_in = db.Column(db.Date, nullable=False)
    check_out = db.Column(db.Date, nullable=False)
    guests = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='bookings')
    room = db.relationship('Property', backref='bookings')


# Forms
class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=4)])
    email = StringField('Email', validators=[InputRequired(), Email()])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=6)])
    confirm = PasswordField('Confirm Password', validators=[InputRequired(), EqualTo('password')])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[InputRequired(), Email()])
    password = PasswordField('Password', validators=[InputRequired()])
    submit = SubmitField('Login')

class PropertyForm(FlaskForm):
    title = StringField('Title', validators=[InputRequired()])
    description = TextAreaField('Description', validators=[InputRequired()])
    location = StringField('Location', validators=[InputRequired()])
    price = FloatField('Price', validators=[InputRequired()])
    latitude = FloatField('Latitude')
    longitude = FloatField('Longitude')
    photos = MultipleFileField('Property Photos', validators=[FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')])

    submit = SubmitField('Submit')

class BookingForm(FlaskForm):
     check_in = DateField('Check-in Date', validators=[DataRequired()])
     check_out = DateField('Check-out Date', validators=[DataRequired()])
     guests = IntegerField('Number of Guests', validators=[DataRequired(), NumberRange(min=1)])
     submit = SubmitField('Confirm Booking')


# User loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route("/")
def home():

    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    has_photos = request.args.get('has_photos')

    query = Property.query

    if min_price is not None:
        query = query.filter(Property.price >= min_price)
    if max_price is not None:
        query = query.filter(Property.price <= max_price)
    if has_photos == 'on':
        query = query.filter(Property.photo_filename.isnot(None))
    properties = query.all()
    rooms = query.options(db.joinedload(Property.photos)).all()
    wishlist_ids = []
    if current_user.is_authenticated:
        wishlist_ids = session.get('wishlist', [])
    return render_template('home.html', properties=properties,  wishlist_ids=wishlist_ids, year=datetime.now().year, google_maps_api_key=app.config['GOOGLE_MAPS_API_KEY'])

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('⚠️ Email is already registered. Please log in or use another email.', 'danger')
            return redirect(url_for('register'))

        hashed_pw = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        role = request.form.get('role', 'user')
        user = User(
            username=form.username.data,
            email=form.email.data,
            password=hashed_pw,
            role=role)
        db.session.add(user)
        db.session.commit()
        flash('Registered successfully! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid email or password', 'danger')
    return render_template('login.html', form=form)


@app.route('/wishlist')
@login_required
def wishlist():
    wishlist_ids = session.get('wishlist', [])
    wishlist_properties = Property.query.filter(Property.id.in_(wishlist_ids)).all()
    return render_template('wishlist.html', wishlist_properties=wishlist_properties)

@app.route('/add_to_wishlist/<int:room_id>', methods=['POST'])
@login_required
def add_to_wishlist(room_id):
    wishlist = session.get('wishlist', [])
    if room_id not in wishlist:
        wishlist.append(room_id)
        session['wishlist'] = wishlist
    return redirect(url_for('home'))

@app.route('/remove_from_wishlist/<int:room_id>', methods=['POST'])
@login_required
def remove_from_wishlist(room_id):
    wishlist = session.get('wishlist', [])
    if room_id in wishlist:
        wishlist.remove(room_id)
        session['wishlist'] = wishlist
        flash('Removed from wishlist', 'info')
    return redirect(url_for('wishlist'))

@app.route('/book/<int:room_id>')
@login_required
def book_property(room_id):
    # You can update this logic later to handle actual booking
    room = Property.query.get_or_404(room_id)

    form = BookingForm()

    if form.validate_on_submit():
        booking = Booking(
            user_id=current_user.id,
            room_id=room.id,
            check_in=form.check_in.data,
            check_out=form.check_out.data,
            guests=form.guests.data
        )
        db.session.add(booking)
        db.session.commit()
        flash('Booking confirmed successfully!', 'success')
        return redirect(url_for('home'))

    return render_template('book_property.html', room=room, form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'info')
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        users = User.query.all()
        properties = Property.query.all()

        # 📊 Chart data: count of properties per owner
        owner_data = db.session.query(User.username, db.func.count(Property.id)) \
            .join(Property, Property.owner_id == User.id) \
            .group_by(User.username).all()

        owner_names = [data[0] for data in owner_data]
        owner_counts = [data[1] for data in owner_data]

        return render_template('admin_dashboard.html',
                               users=users,
                               properties=properties,
                               owner_names=owner_names,
                               owner_counts=owner_counts)
    elif current_user.role == 'owner':
        props = Property.query.filter_by(owner_id=current_user.id).all()
        return render_template('dashboard_owner.html', properties=props)
    else:
       return render_template('dashboarduser.html')
    
@app.route('/edit_property/<int:property_id>', methods=['GET', 'POST'])
@login_required
def edit_property(property_id):
    room = Property.query.get_or_404(property_id)

    # Restrict edit access
    if current_user.role not in ['owner', 'admin'] or room.owner_id != current_user.id:
        flash("You are not authorized to edit this property.", "danger")
        return redirect(url_for('dashboard'))

    form = PropertyForm(obj=room)

    if form.validate_on_submit():
        # ✅ Delete selected photos
        photo_ids_to_delete = request.form.getlist('delete_photos')
        for photo_id in photo_ids_to_delete:
            photo = Photo.query.get(int(photo_id))
            if photo and photo in room.photos:
                room.photos.remove(photo)
                photo_path = os.path.join(app.config['UPLOAD_FOLDER'], photo.filename)
                if os.path.exists(photo_path):
                    os.remove(photo_path)
                db.session.delete(photo)

        # ✅ Update property fields
        room.title = form.title.data
        room.description = form.description.data
        room.location = form.location.data
        room.price = form.price.data
        room.latitude = form.latitude.data
        room.longitude = form.longitude.data

        # ✅ Add new photos
        if form.photos.data:
            for photo in form.photos.data:
                if photo:
                    filename = secure_filename(photo.filename)
                    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    photo.save(path)
                    new_photo = Photo(filename=filename)
                    room.photos.append(new_photo)

        db.session.commit()
        flash("Property updated successfully!", "success")
        return redirect(url_for('dashboard'))

    return render_template("edit_property.html", form=form, room=room)



from werkzeug.utils import secure_filename

@app.route('/add_property', methods=['GET', 'POST'])
@login_required
def add_property():
    if current_user.role not in ['owner', 'admin']:
        flash('Only owners or admins can add properties!', 'warning')
        return redirect(url_for('dashboard'))

    form = PropertyForm()

    if form.validate_on_submit():
        # Step 1: Save the property record
        prop = Property(
            title=form.title.data,
            description=form.description.data,
            location=form.location.data,
            price=form.price.data,
            latitude=form.latitude.data,
            longitude=form.longitude.data,
            owner_id=current_user.id
        )
        db.session.add(prop)
        db.session.flush()  # Makes prop.id available

        # Step 2: Handle multiple photo uploads
        photos = form.photos.data
        for photo_file in photos:
            if photo_file:
                filename = secure_filename(photo_file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                photo_file.save(filepath)

                photo_record = Photo(filename=filename, room_id=prop.id)
                db.session.add(photo_record)

        db.session.commit()
        flash('Property added successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('add_property.html', form=form)


    
@app.route('/delete_property/<int:property_id>', methods=['POST'])
@login_required
def delete_property(property_id):
    if current_user.role != 'admin':
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('dashboard'))

    prop = Property.query.get_or_404(property_id)
    db.session.delete(prop)
    db.session.commit()
    flash('Property deleted successfully!', 'success')
    return redirect(url_for('dashboard'))

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
