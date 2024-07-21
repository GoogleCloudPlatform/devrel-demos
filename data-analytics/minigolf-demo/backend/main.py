import functions_framework
import firebase_admin
from firebase_admin import firestore
from google.cloud import bigquery, storage
from flask import make_response
import base64
import matplotlib.pyplot as plt
from io import BytesIO
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import pandas as pd


PROJECT_ID = ""
BACKGROUND_IMAGE_BUCKET = ""
VIDEO_BUCKET = ""
BQ_DATASET = ""
BQ_PREFIX = f"{PROJECT_ID}.{BQ_DATASET}"


if not firebase_admin._apps:
    firebase_admin.initialize_app(options={'projectId':f'{PROJECT_ID}'})


db = firestore.client()
bq_client = bigquery.Client()


def get_user_status(user_id):
    """Retrieves the status of a user from Firestore."""
    user_doc_ref = db.collection('users_a').document(user_id)
    user_doc = user_doc_ref.get()

    if not user_doc.exists:
        return None  # Return None if user not found

    return user_doc.to_dict().get('status')


def get_commentary(user_id):
    """Fetches commentary for a user from BigQuery."""
    query = f"""
        SELECT commentary
        FROM `{BQ_PREFIX}.commentary`
        WHERE user_id = '{user_id}'
    """
    query_job = bq_client.query(query)
    results = list(query_job)
    return results[0].commentary if results else None


def get_stat(user_id):
    """Calculates and returns game statistics."""
    query = f"SELECT * FROM {BQ_PREFIX}.tracking"
    df = bq_client.query(query).to_dataframe()
    last_frame_per_user = df.groupby('user_id')['frame_number'].transform(max)
    df_filtered = df[df['frame_number'] == last_frame_per_user]
    df_filtered = df_filtered[df_filtered['distance'] < 30]
    user_shot_counts = df_filtered.groupby('user_id')['shot_number'].first()
    user_shot_counts = user_shot_counts[user_shot_counts > 0]
    shot_number_freq = user_shot_counts.value_counts()

    # Selected user's number of shots
    num_users = df['user_id'].nunique()
    user_shots = user_shot_counts.get(user_id, 0)
    average_shots_per_user = user_shot_counts.mean()
    
    plt.figure(figsize=(8, 6))  # Set figure size
    plt.xlim(0, 9)
    barlist = plt.bar(shot_number_freq.index, shot_number_freq.values, color='#4285F4')
    plt.xlabel('Number of Shots')
    plt.ylabel('Number of Users')
    plt.title('Distribution of Number of Shots per User')

    if user_shots in shot_number_freq.index:
        barlist[shot_number_freq.index.get_loc(user_shots)].set_color('#34A853')
        plt.legend([barlist[shot_number_freq.index.get_loc(user_shots)]], [f'Shot Number of {user_id}'])

    plt.xticks(range(9))

    # Save the plot to a BytesIO object
    fig = plt.gcf()
    canvas = FigureCanvas(fig)
    output = BytesIO()
    canvas.print_png(output)
    plt.close(fig)  # Close the figure to prevent memory leaks

    # Encode the image in Base64
    base64_encoded_image = base64.b64encode(output.getvalue()).decode('utf-8')

    # --- Construct the stat dictionary ---
    stat = {
        'num_users': num_users,
        'user_shots': user_shots,
        'average_shots': f'{average_shots_per_user:.2f}',
        'barchart': base64_encoded_image
    }
    return stat



@functions_framework.http
def get_user_data(request):
    """HTTP Cloud Function.
    Args:
        request (flask.Request): The request object.
        <https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data>
    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`
        <https://flask.palletsprojects.com/en/1.1.x/api/#flask.make_response>.
    """

    request_args = request.args
    if request_args and 'userId' in request_args:
        user_id = request_args['userId']
    else:
        return {'error': 'userId parameter is required'}, 400
    
    try:
        image_url = None
        commentary = None
        video_url = None
        stat = None
        
        status = get_user_status(user_id)
        if not status:
            return {'error': 'User is not existed'}, 400
        if status != "processing":
            image_url = f"https://storage.cloud.google.com/{BACKGROUND_IMAGE_BUCKET}/{user_id}.png"
            video_url = f"https://storage.cloud.google.com/{VIDEO_BUCKET}/{user_id}.mp4"
            commentary = get_commentary(user_id)
            stat = get_stat(user_id)

        response_data = {
            'status': status,
            'imageUrl': image_url,
            'commentary': commentary,
            'videoUrl': video_url,
            'users': int(stat['num_users']),
            'shots': int(stat['user_shots']),
            'average': stat['average_shots'],
            'barchart': stat['barchart']
        }

        response = make_response(response_data)
        response.headers.add('Access-Control-Allow-Origin', 'http://127.0.0.1:5501')
        response.headers['Content-Type'] = 'application/json'
        return response, 200
    
    except Exception as e:
        print(f"Error fetching user status: {e}")
        return {'error': 'Failed to fetch user status'}, 500
