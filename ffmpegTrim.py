version = "v1.1.0"
import os, subprocess
from configparser import ConfigParser
from pathlib import Path


def main() -> None:
    config_path = Path(__file__).parent / "config.ini"

    if not config_path.is_file():
        print("Running first time setup...\n")
        setup()

    config = ConfigParser()
    config.read("config.ini")

    audio_codec     = config.get("audio", "codec")
    audio_quality   = config.get("audio", "quality")
    video_codec     = config.get("video", "codec")
    video_quality   = config.get("video", "quality")
    cpu_preset      = config.get("video", "preset")
    file_extension  = config.get("video", "extension")

    print(f"ffmpegTrim-rewrite {version}")

    input_path = input("Path to video (or drag and drop): ").strip().strip('\"\'')
    start_time = input("Start time of clip (hh:mm:ss, mm:ss): ")
    end_time = input("End time of clip (hh:mm:ss, mm:ss): ")

    temp_path = Path(input_path)

    output_path = get_output_path(str(temp_path.with_suffix("")), file_extension)

    start_time_seconds = parse_timecode(start_time)
    end_time_seconds = parse_timecode(end_time)
    duration = end_time_seconds - start_time_seconds

    video_args = (
        ["-c:v", "copy"]
        if video_codec == "copy"
        else ["-c:v", video_codec, "-preset", cpu_preset, "-crf", video_quality]
    )

    audio_args = (
        ["-c:a", "copy"]
        if audio_codec == "copy"
        else ["-c:a", audio_codec, "-b:a", audio_quality]
    )

    container_args = (
        ["-movflags", "+faststart"]
        if file_extension.lower() in ("mp4", "mov", "m4a")
        else []
    )

    args = [
        "-i", str(input_path),
        "-ss", start_time,
        "-t", str(duration),
        *video_args,
        *audio_args,
        *container_args,
        output_path
    ]

    subprocess.run([
        "ffmpeg", *args
    ])

    return

def get_output_path(temp_path: str, file_extension: str) -> str:
    i = 0
    while os.path.exists(
            (output_path := f"{temp_path}_Trim{'' if i == 0 else i}.{file_extension}")
    ): i += 1
    return output_path

def setup():
    print("Installing ffmpeg via winget...\n")
    subprocess.run(["winget", "install", "Gyan.FFmpeg"])
    print("Installing requirements.txt...\n")
    subprocess.run(["pip", "install", "-r", "requirements.txt"])

    print("Generating configuration file...")
    config = ConfigParser()
    config["audio"] = {
        "codec": "copy",
        "quality": "320k",
    }

    config["video"] = {
        "codec": "libx264",
        "quality": "23",
        "preset": "medium",
        "extension": "mp4",
    }

    config["qt"] = {
        "default-path": str(Path.home() / "Videos"),
        "default-theme": "win9x-dark",
    }

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