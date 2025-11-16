import os, subprocess
from configparser import ConfigParser

def main() -> None:
    script_path = os.path.dirname(os.path.realpath(__file__))
    os.chdir(script_path)

    if not os.path.exists("config.ini"):
        print("Running first time setup...\n")
        setup()

    config = ConfigParser()
    config.read("config.ini")

    audio_codec = config.get("main", "audio")
    video_codec = config.get("main", "video")
    preset = config.get("main", "preset")
    file_extension = config.get("main", "extension")

    print("ffmpegTrim-rewrite v1.0.1")

    input_path = input("Path to video (or drag and drop): ")
    start_time = input("Start time of clip (mm:ss): ")
    end_time = input("End time of clip (mm:ss): ")

    input_path = input_path.strip('\"\'')
    temp_path, _ = input_path.strip('\"\'').split(".", 1)

    i = 0
    while os.path.exists(
            (output_path := f"{temp_path}_Trim{'' if i == 0 else i}.{file_extension}")
    ): i += 1

    start_time_seconds = parse_timecode(start_time)
    end_time_seconds = parse_timecode(end_time)
    duration = end_time_seconds - start_time_seconds

    subprocess.run([
        "ffmpeg",
        "-ss", start_time,
        "-i", input_path,
        "-ss", "0",
        "-t", str(duration),
        "-c:v", video_codec,
        "-preset", preset,
        "-c:a", audio_codec,
        output_path
    ])
    return

def setup():
    print("Installing ffmpeg via winget...\n")
    subprocess.run(["winget", "install", "Gyan.FFmpeg"])
    print("Installing python libraries via pip...\n")
    subprocess.run(["pip", "install", "configparser"])

    print("Generating configuration file...")
    config = ConfigParser()

    config.read("config.ini")
    config.add_section("main")
    config.set("main", "audio", "copy")
    config.set("main", "video", "libx264")
    config.set("main", "preset", "medium")
    config.set("main", "extension", "mp4")

    with open("config.ini", "w") as f:
        config.write(f)

    print("Done!\n")
    return

def parse_timecode(tc):
    if "." in tc:
        whole, ms = tc.split(".")
        seconds = parse_timecode(whole)
        return seconds + float("0." + str(ms))
    else:
        parts = list(map(int, tc.split(":")))
        if len(parts) == 2:
            return parts[0]*60 + parts[1]
        elif len(parts) == 3:
            return parts[0]*3600 + parts[1]*60 + parts[2]
        else:
            raise ValueError("Invalid timecode format.")

if __name__ == "__main__":
    main()