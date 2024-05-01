#Copyright 2023 Google LLC
#
#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.

import base64
import json
import os
import copy_image


from flask import Flask, request, make_response, jsonify




print("Started...")
app = Flask(__name__)


#################################
# Update Source and Target Registries with your project and repo
#################################
# SA Requires Artifact Registry Read Permission
SOURCE_AR_REGISTRY = "us-docker.pkg.dev/$source_project_name$/ar"


# SA Requires Artifact Registry Read Permission
TARGET_AR_REGISTRY = "us-docker.pkg.dev/$target_project_name$/ar"


# Path in quotes below (/image/copy) must be added to EventArc Trigger > "Service URL path. Path allows CloudRun to know which API is being called"
@app.route('/image/copy', methods=['POST'])
def cp_image():
    pubsub_message = request.get_json()
    if not pubsub_message:
        msg = "No Pub/Sub message received"
        print(f"Error: {msg}")
        response = make_response(msg, 400)
        return jsonify(response)


    if not isinstance(pubsub_message, dict) or "message" not in pubsub_message:
        msg = "Invalid Pub/Sub message format"
        response = make_response(msg, 400)
        return jsonify(response)
    message = pubsub_message["message"]
  
#################################
# Edit Image Tag that will be copied to target
#################################
    image_tag_target = "$target_image_tag:$"


    source_ar_repository_name = SOURCE_AR_REGISTRY if not os.environ.get("SOURCE_AR_REGISTRY") else os.environ.get("SOURCE_AR_REGISTRY")
    target_ar_repository_name = TARGET_AR_REGISTRY if not os.environ.get("TARGET_AR_REGISTRY") else os.environ.get("TARGET_AR_REGISTRY")


    print(f"source repo name: {source_ar_repository_name}")
    print(f"target repo name: {target_ar_repository_name}")
  
#################################
# Copy image_tag
#################################
    if isinstance(message, dict) and "data" in message:
        data = base64.b64decode(message["data"]).decode("utf-8").strip()
        print(f"data: {data}", flush=True)
        data_clean = data.replace("data:","")
        data = json.loads(data_clean)
        image_full_name= data["tag"]
        data_repo = data["tag"].rsplit('/', 1)[0:1]
        print(f"data_repo: {str(data_repo[0])}", flush=True)


        if (data["action"] == "INSERT") and (str(data_repo[0]) == source_ar_repository_name) :
            image_full_name= data["tag"]
            image_tag_pubsub_msg = image_full_name.split("/")[::-1][:1]
            print(f"image_tag: {image_tag_pubsub_msg}", flush=True)
if (image_tag_target == image_tag_pubsub_msg) :
            print(f"If passed")
            try:
                copy_image_result = copy_image.copy_image(str(image_tag_pubsub_msg[0]), source_ar_repository_name, target_ar_repository_name)
                print(f"-----response: {copy_image_result}", flush=True)
                response = jsonify("Done")
                response.status_code = 200
                print(f"response: {response}", flush=True)
                return response
            except Exception:
                response = jsonify("gcrane timed out after 600 seconds")
response.status_code = 400
                print(f"error: {response}", flush=True)
                return response
            else :
              print(f"The source AR updates were not made to the concerning image. No image will be updated as a result.")
        else :
            response = jsonify("Nothing to update")
            response.status_code = 204
            print(f"no content: {response}", flush=True)
            return response
    else :
        msg = jsonify("Invalid Pub/Sub message format")
        response.status_code = 400
        return response




if __name__ == "__main__":
app.run(debug=True, host="0.0.0.0", port=int(os.environ.get('PORT', 8080)))
