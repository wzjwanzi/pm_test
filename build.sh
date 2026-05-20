#!/bin/bash

echo "========================================"
echo "移动设备自动化测试平台 - 打包工具"
echo "========================================"
echo ""

echo "[1/5] 检查 Python 环境..."
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 Python，请先安装 Python 3.8+"
    exit 1
fi
echo "✓ Python 环境正常"
echo ""

echo "[2/5] 安装依赖包..."
pip3 install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "错误: 依赖安装失败"
    exit 1
fi
echo "✓ 依赖安装完成"
echo ""

echo "[3/5] 清理旧的构建文件..."
rm -rf build dist __pycache__
echo "✓ 清理完成"
echo ""

echo "[4/5] 开始打包（这可能需要几分钟）..."
pyinstaller build.spec --clean
if [ $? -ne 0 ]; then
    echo "错误: 打包失败"
    exit 1
fi
echo "✓ 打包完成"
echo ""

echo "[5/5] 创建发布包..."
mkdir -p release
cp dist/MobileTestPlatform release/
cp README.md release/
cp USAGE.md release/
cp 5G_TESTING_GUIDE.md release/
chmod +x release/MobileTestPlatform
echo "✓ 发布包创建完成"
echo ""

echo "========================================"
echo "打包成功！"
echo "可执行文件位置: release/MobileTestPlatform"
echo "========================================"
echo ""
