import os
from base64 import b64encode
import subprocess
import sys

import openai
import pysrt

openai.api_key_path = "./api_key.txt"

PROMPT = "You are a helpful assistant that summarises a recipe from a Youtube video."

template = """This is a transcription of a recipe from Youtube and the description of the video.

Transcript:

{transcript}

Description:

{description}

Generate the output as a recipe in English with the following constraints:

- If the quantity of ingredients is mentioned in either the description or the transcription, include the quantity in metric for those ingredients, otherwise only list the name of the ingredient.
- If the recipe includes any tips, include them at the end in the tips section, otherwise omit the tips section.
- Include total calories if mentioned, otherwise use the ingredients to estimate an amount of calories in the recipe.
- Merge the instructions from the description and transcript resolving any inconsistencies, giving priority to the transcript.

Follow this Markdown template:

# <Recipe title>

## Ingredients:

<Ingredients here as a markdown list>

## Total calories:

<Total calories per recipe here (estimated)>

## Steps:

<Steps here as a numbered list>

## Tips:

<Tips here as a markdown list>
"""


def openai_completion(text):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": PROMPT},
            {
                "role": "user",
                "content": text,
            },
        ],
        temperature=0,
        max_tokens=800,
        top_p=1,
        frequency_penalty=0.5,
        presence_penalty=0,
    )
    return response


def get_subs_list(video_url) -> list[str]:
    """Run command and return output"""
    # TODO: This should actually return a dict, because youtube differentiates between
    # auto-generated and manually created subtitles
    result = subprocess.run(
        ["yt-dlp", "--list-subs", video_url], stdout=subprocess.PIPE
    )
    languages = []
    for line in result.stdout.decode("utf-8").splitlines():
        if "vtt" in line:
            languages.append(line.split(" ")[0])
    return languages


def download_sub(video_url: str, language: str):
    # --write-auto-sub --sub-lang "en.*"
    video_id = b64encode(video_url.split("=")[-1].encode("utf-8"))
    filename = f"downloads/{video_id.decode('utf-8')}"
    # If filename exists, then return
    if os.path.exists(filename + ".en.srt"):
        print(">>> Reusing exisiting subs")
        return filename + ".en.srt"
    else:
        print(">>> Downloading subs from Youtube")
    for sub_type in ["--write-auto-sub", "--write-sub"]:
        subprocess.run(
            [
                "yt-dlp",
                "--skip-download",
                sub_type,
                "--sub-lang",
                language,
                video_url,
                "--output",
                filename,
                "--convert-subs",
                "srt",
                "--write-description",
            ],
            # Ignore output
            stdout=subprocess.DEVNULL,
        )
    return filename + ".en.srt"


def sub_to_text(filename):
    items = pysrt.open(filename)
    previous = None
    text = []
    for item in items:
        if previous and item.text.startswith(previous):
            # Sometimes a subtitle line includes the previous line
            # we don't want those duplicates
            text.append("")
        else:
            text.append(item.text.replace("[Music]", ""))
        previous = item.text
    return " ".join(text)


if __name__ == "__main__":
    if not sys.argv[1:]:
        print("Please provide a youtube video url")
        sys.exit(1)
    video_url = sys.argv[1]
    filename = download_sub(video_url, "en")
    transcript = sub_to_text(filename)
    description = open(filename.split(".")[0] + ".description", "r").read()

    text = template.format(transcript=transcript, description=description)
    print("\n" * 2)
    print(openai_completion(text)["choices"][0]["message"]["content"])
