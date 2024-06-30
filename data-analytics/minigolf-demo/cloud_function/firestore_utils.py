import firebase_admin
from firebase_admin import firestore


def get_firestore_client():
    try:
        app = firebase_admin.get_app()
    except ValueError:
        app = firebase_admin.initialize_app()
    finally:
        db = firestore.client(app)

        # Create 'users' collection if it doesn't exist
        if not db.collection('users').get():
            db.collection('users').document().set({})
        return db
    
def update_user_status(db, id, status):
    # Save user information to Firestore
    users_ref = db.collection('users').document(id)
    users_ref.set({"user_id": id, "status": status})
    return
