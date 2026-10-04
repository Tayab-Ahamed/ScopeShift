import os, subprocess, json

def assemble():
    base_dir = r"c:\Projects\Scope Shift\brag-output"
    os.chdir(base_dir)

    # 1. Write SRT subtitles file
    srt_content = """1
00:00:00,400 --> 00:00:06,200
In multi-agent teams, seeing a button in a staging UI is often hallucinated as scope approval.

2
00:00:06,600 --> 00:00:15,000
ScopeShift decouples extraction from authority. Every citation is code-verified verbatim against artifacts.

3
00:00:15,400 --> 00:00:22,400
Inspect live evidence side-by-side. Only cryptographically verified client decisions can govern.

4
00:00:22,800 --> 00:00:29,600
Every mutation is SHA-256 hash-chained and streamed to BigQuery. Stop AI spec drift with ScopeShift.
"""
    with open("subtitles.srt", "w", encoding="utf-8") as f:
        f.write(srt_content)

    # 2. Concat audio
    audio_list = "concat_audio.txt"
    with open(audio_list, "w", encoding="utf-8") as f:
        f.write("file 'scene1.wav'\nfile 'scene2.wav'\nfile 'scene3.wav'\nfile 'scene4.wav'\n")

    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", audio_list, "-c", "copy", "master_audio.wav"], check=True)

    # 3. Create video segments for each scene
    # Durations: scene1: 6.47s, scene2: 8.78s, scene3: 7.40s, scene4: 7.25s
    # Scenes: 
    # 1: scene1_cockpit.png
    # 2: scene2_studio.png
    # 3: scene5_provenance_modal.png
    # 4: scene4_audit.png
    clips = [
        ("scene1_cockpit.png", 6.47, "clip1.mp4"),
        ("scene2_studio.png", 8.78, "clip2.mp4"),
        ("scene5_provenance_modal.png", 7.40, "clip3.mp4"),
        ("scene4_audit.png", 7.25, "clip4.mp4")
    ]

    for img, dur, out in clips:
        cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", img,
            "-t", str(dur),
            "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black,format=yuv420p",
            "-r", "30",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            out
        ]
        subprocess.run(cmd, check=True)

    # 4. Concat video clips
    video_list = "concat_video.txt"
    with open(video_list, "w", encoding="utf-8") as f:
        f.write("file 'clip1.mp4'\nfile 'clip2.mp4'\nfile 'clip3.mp4'\nfile 'clip4.mp4'\n")

    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", video_list, "-c", "copy", "raw_video.mp4"], check=True)

    # 5. Burn in subtitles and merge with master audio
    # Subtitles styling via drawtext or subtitles filter
    # To avoid Windows path escaping issues in libass, let's use ffmpeg subtitles filter with simple filename
    cmd_final = [
        "ffmpeg", "-y",
        "-i", "raw_video.mp4",
        "-i", "master_audio.wav",
        "-vf", "subtitles=subtitles.srt:force_style='Fontname=Arial,Fontsize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H80000000,BorderStyle=4,Outline=1,Shadow=0,MarginV=42,Alignment=2'",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        "scopeshift_demo.mp4"
    ]
    subprocess.run(cmd_final, check=True)

    # 6. Extract best poster image (frame at ~16s showing Provenance Inspector modal)
    subprocess.run([
        "ffmpeg", "-y", "-ss", "00:00:16", "-i", "scopeshift_demo.mp4",
        "-vframes", "1", "-q:v", "2",
        "scopeshift_demo_poster.jpg"
    ], check=True)

    print("SUCCESS: scopeshift_demo.mp4 and poster created!")

if __name__ == "__main__":
    assemble()
