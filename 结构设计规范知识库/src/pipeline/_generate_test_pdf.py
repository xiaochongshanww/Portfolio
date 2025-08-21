from PIL import Image, ImageDraw, ImageFont
import os

CWD = os.getcwd()
raw_dir = os.path.join(CWD, 'data', 'raw')
if not os.path.exists(raw_dir):
    os.makedirs(raw_dir)

img = Image.new('RGB', (800, 1200), color='white')
d = ImageDraw.Draw(img)
try:
    font = ImageFont.truetype('Arial.ttf', 40)
except Exception:
    font = ImageFont.load_default()

d.text((50, 50), '这是测试图片文字：测试 OCR 输出', fill='black', font=font)

pdf_path = os.path.join(raw_dir, 'test_image.pdf')
img.save(pdf_path, 'PDF', resolution=300)
print('已生成测试 PDF:', pdf_path)
