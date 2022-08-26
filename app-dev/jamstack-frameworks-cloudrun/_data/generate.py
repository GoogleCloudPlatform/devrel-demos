from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

templateLoader = FileSystemLoader(searchpath="templates/")
env = Environment(loader=templateLoader, autoescape=select_autoescape())

frameworks = sorted(Path("data").glob("*.yml"))
firebase_path = Path("../../jamstack-frameworks-firebase-hosting")
gcr_path = Path("../")
readme_md = "README.md"

template = env.get_template("deployment.md.j2")
gcr_readme = env.get_template("cloudrun.md.j2")
firebase_readme = env.get_template("firebase.md.j2")
gcr_framework_list = []
firebase_framework_list = []

for config in frameworks:
    framework = config.stem

    with open(config) as f:
        data = yaml.safe_load(f.read())

    if "skip_cloudrun" not in data.keys():
        gcr_framework_list.append((data["name"], framework, data["language"]))
        with open(gcr_path / framework / readme_md, "w") as f:
            f.write(template.render(**data, platform="Cloud Run"))

    if "skip_firebase" not in data.keys():
        firebase_framework_list.append((data["name"], framework, data["language"]))
        with open(firebase_path / framework / readme_md, "w") as f:
            f.write(template.render(**data, platform="Firebase"))


with open(gcr_path / readme_md, "w") as f:
    f.write(gcr_readme.render(frameworks=gcr_framework_list))

with open(firebase_path / readme_md, "w") as f:
    f.write(firebase_readme.render(frameworks=firebase_framework_list))

print(f"Wrote out {len(gcr_framework_list) + len(firebase_framework_list)} demos. ({len(gcr_framework_list)} for Cloud Run, { len(firebase_framework_list)} for Firebase Hosting)")