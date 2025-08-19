#!/usr/bin/env python3
"""
A small OCR worker that loads PaddleOCR inside a subprocess and returns recognized lines as JSON.
This isolates Paddle's native libraries so the main process won't crash if Paddle triggers a segfault.
Usage: python _ocr_worker.py /path/to/image.png
"""
import sys
import os
import json
from contextlib import redirect_stdout, redirect_stderr
from PIL import Image
import numpy as np


def main():
    # 支持两种模式：
    # 1) 预热模式: python _ocr_worker.py --preheat
    # 2) 正常模式: python _ocr_worker.py /path/to/image.png
    if len(sys.argv) < 2:
        print(json.dumps({'error': 'missing argument'}), flush=True)
        sys.exit(2)

    if sys.argv[1] == '--preheat':
        # 仅初始化 PaddleOCR 并退出，用于预热模型下载和加载
        try:
            with open(os.devnull, 'w') as devnull, redirect_stdout(devnull), redirect_stderr(devnull):
                from paddleocr import PaddleOCR
                _ = PaddleOCR(use_textline_orientation=True, lang='ch')
            print(json.dumps({'status': 'preheated'}), flush=True)
            sys.exit(0)
        except Exception as e:
            print(json.dumps({'error': str(e)}), flush=True)
            sys.exit(1)

    img_path = sys.argv[1]
    try:
        # 为了完全屏蔽 PaddleOCR/PIL 等库在运行时可能打印到 stdout/stderr 的信息，
        # 我们在子进程内部把整个工作过程都重定向到 devnull，然后在外面把结果以 JSON 打印出来。
        lines = []
        error = None
        try:
            with open(os.devnull, 'w') as devnull, redirect_stdout(devnull), redirect_stderr(devnull):
                from paddleocr import PaddleOCR
                ocr = PaddleOCR(use_textline_orientation=True, lang='ch')

                pil_img = Image.open(img_path).convert('RGB')
                img_np = np.array(pil_img)
                result = ocr.ocr(img_np)

                if result and result[0] is not None:
                    lines = [line[1][0] for line in result[0]]

        except Exception as e:
            error = str(e)

        # 只将结构化结果输出到父进程的 stdout，避免混入库的原始日志
        if error:
            print(json.dumps({'error': error}, ensure_ascii=False), flush=True)
            sys.exit(1)
        else:
            print(json.dumps({'lines': lines}, ensure_ascii=False), flush=True)
    except Exception as e:
        print(json.dumps({'error': str(e)}), flush=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
