#!/usr/bin/env python3
"""Monitor an Agnes Video async task, polling every 30s, notifying on progress.

Usage:
  python3 monitor_video.py --video-id <VIDEO_ID> --project-dir <DIR> --output <FILE>

Runs via terminal(background=True, notify_on_complete=True, timeout=600).
Loops every 30s, prints status, and exits when done.
"""
import argparse, json, os, subprocess, sys, time, datetime


def main():
    parser = argparse.ArgumentParser(description="Monitor Agnes Video async task")
    parser.add_argument("--video-id", required=True, help="Video ID to poll")
    parser.add_argument("--project-dir", required=True, help="Project workspace directory")
    parser.add_argument("--output", required=True, help="Output filename (e.g. output.mp4)")
    args = parser.parse_args()

    video_id = args.video_id
    project_dir = args.project_dir
    output_file = args.output

    api_key = os.environ.get("AGNES_API_KEY")
    if not api_key:
        print("ERROR: AGNES_API_KEY not set")
        sys.exit(1)

    os.makedirs(f"{project_dir}/target/videos", exist_ok=True)
    poll_count = 0

    while True:
        poll_count += 1
        cmd = [
            "curl", "-s", "--location",
            "-X", "GET",
            f"https://apihub.agnes-ai.com/agnesapi?video_id={video_id}",
            "-H", f"Authorization: Bearer {api_key}"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] ⚠ API parse error, retrying...")
            time.sleep(30)
            continue

        status = data.get("status", "unknown")
        progress = data.get("progress", 0)
        seconds = data.get("seconds", "?")
        size = data.get("size", "?")
        perf = data.get("perf_params", {})
        frame_rate = perf.get("frame_rate", "?")
        num_frames = perf.get("num_frames", "?")
        url = data.get("url")
        error = data.get("error")

        print("=" * 50)
        print(f"📊 状态: {status} ({progress}%)")
        print(f"⏱ 时长: {seconds}s | 📐 分辨率: {size}")
        print(f"🎞 帧数: {num_frames}帧 @ {frame_rate}fps")
        print(f"🔄 轮询 #{poll_count} | 🕐 {datetime.datetime.now().strftime('%H:%M:%S')}")
        print("=" * 50)

        if status == "completed" and url:
            output_path = f"{project_dir}/target/videos/{output_file}"
            dl_cmd = ["curl", "-sL", url, "-o", output_path]
            print("⬇ 下载中...")
            subprocess.run(dl_cmd, timeout=120)
            file_size = os.path.getsize(output_path)
            print(f"\n✅ 视频生成完成！")
            print(f"📁 文件: {output_path}")
            print(f"📏 大小: {file_size/1024/1024:.1f}MB")
            print(f"MEDIA:{output_path}")
            sys.exit(0)
        elif status == "failed":
            print(f"\n❌ 生成失败: {error}")
            sys.exit(1)
        else:
            time.sleep(30)


if __name__ == "__main__":
    main()