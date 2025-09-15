# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from flask import Flask, render_template, request, redirect
from google import genai
from google.genai import types
import markdown
import base64
import prompts
from util import get_project_id

app = Flask(__name__)

client = genai.Client(
    vertexai=True,
    project=get_project_id(),
    location="us-central1",
)

@app.route('/', methods=['GET'])
def index():
    """
    Renders the home page.
    Returns: The rendered template.
    """
    return render_template('index.html')

def generate_image(blog_title):
    """
    Generates an image for a blog post using the Imagen model.

    Args:
        blog_title (str): The title of the blog post, used as a prompt for
                          image generation.

    Returns:
        str: Base64 encoded image data (PNG format).
    """
    prompt = prompts.get_image_gen_prompt(blog_title)
    response = client.models.generate_images(
        model='imagen-4.0-generate-001',
        prompt=prompt,
        config=types.GenerateImagesConfig(
            number_of_images=1,
            output_mime_type='image/png',
        ),
    )
    image_data = response.generated_images[0].image.image_bytes
    encoded_image = base64.b64encode(image_data).decode('utf-8')
    return encoded_image

def generate_blog_post_text(youtube_link, model):
    """
    Generates the blog post text content from a YouTube video.

    Args:
        youtube_link (str): The URL of the YouTube video.
        model (str): The name of the generative model to use.

    Returns:
        str: The generated blog post text in Markdown format.
    """
    contents = [
        types.Part.from_uri(file_uri=youtube_link, mime_type="video/*"),
        types.Part.from_text(text=prompts.get_blog_gen_prompt())
    ]
    return client.models.generate_content(
        model = model,
        contents = contents
    ).text

def extract_title_from_markdown(markdown_text):
    """
    Extracts the first '##' heading from a Markdown text as the title.

    Args:
        markdown_text (str): The Markdown text content.

    Returns:
        str: The extracted title, or a default title if no '##' heading is
             found.
    """
    default_title = "Your AI-Generated Blog Post"
    lines = markdown_text.split('\n')
    for line in lines:
        if line.startswith('## '):
            return line.strip('# ').strip()
    return default_title

@app.route('/blog', methods=['GET', 'POST'])
def generate_blog_post():
    """
    Generates a blog post from the user provided YouTube video.
    Returns: The rendered blog post.
    """
    if request.method == 'POST':
        youtube_link = request.form['youtube_link']
        model = request.form['model']
        blog_post_text = generate_blog_post_text(youtube_link, model)
        title = extract_title_from_markdown(blog_post_text)
        image_data = generate_image(title)
        return render_template(
            'blog-post.html',
            title=title,
            blog_post_html=markdown.markdown(blog_post_text),
            image_data=image_data
        )
    else:
        return redirect('/')

if __name__ == '__main__':
    server_port = os.environ.get('PORT', '8080')
    app.run(debug=False, port=server_port, host='0.0.0.0')
