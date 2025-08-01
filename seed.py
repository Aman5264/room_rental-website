from app import app, db, Property

with app.app_context():
    room = Property(
        title="Sea View Apartment",
        description="Beautiful sea-facing room",
        location="Mumbai",
        price=3500,
        latitude=19.0760,
        longitude=72.8777,
        photo_filename="room1.jpeg",
        owner_id=1  # 🔴 Make sure user with id=1 exists or change this
    )

    db.session.add(room)
    db.session.commit()
    print("Room added successfully!")
