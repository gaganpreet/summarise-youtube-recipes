from base64 import b64encode
import subprocess
import sys

import openai
import pysrt

openai.api_key_path = "./api_key.txt"


def openai_completion(prompt):
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=prompt,
        temperature=0,
        max_tokens=600,
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
            ]
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
    text = sub_to_text(filename)
    print(
        openai_completion("Summarise this as a recipe with steps:\n" + text)["choices"][
            0
        ]["text"]
    )
