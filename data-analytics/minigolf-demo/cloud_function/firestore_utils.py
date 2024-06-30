# Copyright 2024 Google LLC

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     https://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
