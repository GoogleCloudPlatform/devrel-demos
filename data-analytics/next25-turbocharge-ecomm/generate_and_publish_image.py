import vertexai
from vertexai.preview.vision_models import ImageGenerationModel
from google.cloud import storage
from google.cloud import pubsub_v1
import datetime
import random
import json  # Use json.dumps for better message formatting
import io

def generate_random_toy_name() -> str:
    """
    Generates a random, child-friendly toy name. Includes "toy".
    """
    materials = [
        "wooden", "plush", "plastic", "soft", "colorful",
        "musical", "interactive", "stacking", "rolling", "cuddly",
    ]
    animals = [
        "bear", "dog", "cat", "rabbit", "lion", "elephant",
        "monkey", "giraffe", "penguin", "parrot", "duck",
        "fish", "horse", "puppy", "kitten", "bunny"
    ]
    objects = [
        "train", "blocks", "car", "truck", "puzzle",
        "doll", "boat", "plane", "rattle", "stacker", "xylophone",
    ]
    descriptors = [
        "with tracks", "for building", "for cuddling", "that sings",
        "with lights", "for learning", "",  # Empty string for no extra descriptor
        "set", "and friends"
    ]

    material = random.choice(materials)
    # Choose animal or object, not both.
    if random.random() < 0.6:  # 60% chance of an object
        item = random.choice(objects)
        animal = ""
    else:  # 40% chance of animal
        item = ""
        animal = random.choice(animals)

    descriptor = random.choice(descriptors)

    # Construct the name, handling different combinations logically.
    if item:
        name = f"{material} toy {item} {descriptor}"
    elif animal:
        name = f"{material} {animal} toy {descriptor}"
    else:  # Edge Case
        name = f"{material} toy"

    # Clean up extra spaces and capitalize.
    name = " ".join(name.split()).title()
    return name


def generate_and_publish_image(project_id: str, gcs_bucket_name: str, location: str = "us-central1") -> None:
    """
    Generates a toy image using Vertex AI, uploads it to GCS, and publishes a message to Pub/Sub.

    Args:
        project_id: Your Google Cloud project ID.
        gcs_bucket_name: The name of your GCS bucket.
        location: The Vertex AI location. Defaults to "us-central1".
    """

    vertexai.init(project=project_id, location=location)
    model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-002")  # Or a suitable model

    # Generate a toy name for the prompt
    prompt = generate_random_toy_name()
    print(f"Generated Prompt: {prompt}")

    # Create a filename-safe version of the prompt
    filename_safe_prompt = prompt.replace(" ", "_").lower()

    # Generate the image
    try:
        images = model.generate_images(
            prompt=prompt,
            number_of_images=1,
            language="en",
            aspect_ratio="1:1",
            safety_filter_level="block_some",
        )
        image = images[0]  # Get the first (and only) image
        image_bytes = image._image_bytes # Get image bytes

        print(f"Created output image using {len(image_bytes)} bytes")

        # Show the image (optional, useful for notebooks)
        #image.show()  # Uncomment if you're in a Jupyter environment


    except Exception as e:
        print(f"Error generating image: {e}")
        return

    # Initialize GCS and Pub/Sub clients
    storage_client = storage.Client()
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, "demo6-topic")  # Replace "demo6-topic" with your topic

    # GCS Upload
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        image_name = f"image_{filename_safe_prompt}_{timestamp}.jpeg"  # Use .jpeg extension
        gcs_path = f"raw/{image_name}"
        bucket = storage_client.bucket(gcs_bucket_name)
        blob = bucket.blob(gcs_path)
        blob.upload_from_string(image_bytes, content_type="image/jpeg")  # Upload bytes
        print(f"Image uploaded to gs://{gcs_bucket_name}/{gcs_path}")

    except Exception as e:
        print(f"Error uploading to GCS: {e}")
        return  # Exit if upload fails

    # Pub/Sub Publish
    try:
        message_data = {
            "image_path": f"gs://{gcs_bucket_name}/{gcs_path}",
            "image_bucket": gcs_bucket_name,
            "image_path_split": gcs_path,
            "contextual_text": prompt,
        }
        message_bytes = json.dumps(message_data).encode("utf-8")  # Use json.dumps

        publish_future = publisher.publish(topic_path, data=message_bytes)
        publish_future.result()  # Wait for publish to complete (important!)
        print(f"Message published to {topic_path}")

    except Exception as e:
        print(f"Error publishing message: {e}")


if __name__ == '__main__':
    my_project_id = "data-connect-demo6"
    my_gcs_bucket = "demo6-df-temp"

    generate_and_publish_image(my_project_id, my_gcs_bucket)
