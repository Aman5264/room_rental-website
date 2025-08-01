from app import app, db, User

# Wrap everything in app.app_context()
with app.app_context():
    user = User.query.filter_by(email="amansinghsheikpura@gmail.com").first()
    if user:
        user.role = "admin"
        db.session.commit()
        print("✅ User promoted to admin.")
    else:
        print("❌ User not found.")
