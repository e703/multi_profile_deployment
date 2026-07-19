#!/bin/bash
# OneDrive 文件上传 + 分享链接生成
# 用法: ./onedrive_share.sh <文件路径>
# 示例: ./onedrive_share.sh /path/to/video.mp4

set -e

FILE="$1"

if [ -z "$FILE" ] || [ ! -f "$FILE" ]; then
  echo "❌ 用法: $0 <文件路径>"
  echo "示例: $0 /home/alan/workspace/xinjing/target/audio/xinjing.mp3"
  exit 1
fi

FILENAME=$(basename "$FILE")
FILESIZE=$(stat -c%s "$FILE" 2>/dev/null || stat -f%z "$FILE" 2>/dev/null)
FILESIZE_MB=$(awk "BEGIN {printf \"%.1f\", $FILESIZE/1048576}")

# 目标路径：OneDrive 上按日期归类
REMOTE_DIR="onedrive:Documents/agnes_share/$(date +%Y%m)"
REMOTE_PATH="$REMOTE_DIR/$FILENAME"

echo "📤 上传: $FILENAME ($FILESIZE_MB MB)"
echo "  → $REMOTE_DIR/"

# 上传到 OneDrive
rclone copy "$FILE" "$REMOTE_DIR/" 2>&1
echo "✅ 上传完成"

# 生成分享链接
echo "🔗 生成分享链接..."
LINK=$(rclone link "$REMOTE_PATH" 2>&1 | tail -1)

echo ""
echo "═══════════════════════════════════════"
echo "  ✅ 文件已上传到 OneDrive"
echo "  📄 $FILENAME"
echo "  📦 $FILESIZE_MB MB"
echo "  🔗 $LINK"
echo "═══════════════════════════════════════"
echo ""
echo "  📁 本地路径: $FILE"
echo "  ☁️  OneDrive: $REMOTE_PATH"
echo ""
echo "  ⚠️  OneDrive 链接默认是匿名可访问的"
echo "     如需更高安全性，请登录 OneDrive 网页端手动设置："
echo "     1. 打开链接"
echo "     2. 点击右上角 ⋯ → 管理访问权限"
echo "     3. 设置密码或到期时间"