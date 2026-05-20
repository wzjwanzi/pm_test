#!/bin/bash
# 快速打包脚本 - 适用于开发测试

echo "快速打包中..."

# 清理
rm -rf build dist

# 打包
pyinstaller build.spec --clean --noconfirm

if [ $? -eq 0 ]; then
    echo "✓ 打包成功！"
    echo "可执行文件: dist/MobileTestPlatform"
else
    echo "✗ 打包失败"
    exit 1
fi
