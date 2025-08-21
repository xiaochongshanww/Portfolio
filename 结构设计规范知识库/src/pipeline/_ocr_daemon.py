#!/usr/bin/env python3
"""
长期运行的 OCR 守护进程。启动后会初始化 PaddleOCR（仅一次），通过 TCP 接受 JSON 请求：
  {"cmd": "ocr", "image_path": "/tmp/..png"}
或
  {"cmd": "preheat"}
返回用 JSON（一行）响应：{"lines": [...]} 或 {"status":"preheated"} 或 {"error": "..."}

注意：为避免终端被 Paddle 的下载/进度条污染，初始化与识别时会屏蔽 stdout/stderr。
"""
import socketserver
import socket
import json
import os
from contextlib import redirect_stdout, redirect_stderr
import sys
from PIL import Image
import numpy as np


class OCRHandler(socketserver.StreamRequestHandler):
    def handle(self):
        try:
            raw = self.rfile.readline()
            if not raw:
                return
            try:
                req = json.loads(raw.decode('utf-8'))
            except Exception as e:
                self.wfile.write(json.dumps({'error': f'invalid json: {e}'}).encode('utf-8') + b"\n")
                return

            cmd = req.get('cmd')
            if cmd == 'preheat':
                self.wfile.write(json.dumps({'status': 'preheated'}, ensure_ascii=False).encode('utf-8') + b"\n")
                return

            if cmd == 'shutdown':
                self.wfile.write(json.dumps({'status': 'shutting down'}, ensure_ascii=False).encode('utf-8') + b"\n")
                # signal server to shutdown by setting a flag on server
                self.server.should_shutdown = True
                return

            if cmd != 'ocr':
                self.wfile.write(json.dumps({'error': 'unknown cmd'}).encode('utf-8') + b"\n")
                return

            img_path = req.get('image_path')
            if not img_path or not os.path.exists(img_path):
                self.wfile.write(json.dumps({'error': 'missing or invalid image_path'}, ensure_ascii=False).encode('utf-8') + b"\n")
                return

            # run OCR while suppressing stdout/stderr
            lines = []
            try:
                with open(os.devnull, 'w') as devnull, redirect_stdout(devnull), redirect_stderr(devnull):
                    # ocr_model is attached to server
                    pil_img = Image.open(img_path).convert('RGB')
                    img_np = np.array(pil_img)
                    result = self.server.ocr_model.ocr(img_np)
                    if result and result[0] is not None:
                        lines = [line[1][0] for line in result[0]]
            except Exception as e:
                self.wfile.write(json.dumps({'error': str(e)}, ensure_ascii=False).encode('utf-8') + b"\n")
                return

            self.wfile.write(json.dumps({'lines': lines}, ensure_ascii=False).encode('utf-8') + b"\n")

        except Exception as e:
            try:
                self.wfile.write(json.dumps({'error': str(e)}, ensure_ascii=False).encode('utf-8') + b"\n")
            except Exception:
                # 如果无法写回客户端，安静地忽略
                pass
            return


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True


def run_server(host='127.0.0.1', port=18765):
    # Initialize OCR model with stdout/stderr suppressed
    try:
        with open(os.devnull, 'w') as devnull, redirect_stdout(devnull), redirect_stderr(devnull):
            from paddleocr import PaddleOCR
            ocr_model = PaddleOCR(use_textline_orientation=True, lang='ch')
            # 预热：对一张小的空白图像执行一次识别，以确保模型文件下载并加载到内存
            try:
                import numpy as _np
                dummy = _np.zeros((64, 64, 3), dtype=_np.uint8)
                # 识别一次以触发模型加载/下载（输出被重定向）
                _ = ocr_model.ocr(dummy)
            except Exception:
                # 预热失败不应阻塞守护进程启动，但会在主进程通过 TCP 检测时体现为未就绪
                pass
    except Exception as e:
        print(json.dumps({'error': f'failed to init PaddleOCR: {e}'}), flush=True)
        sys.exit(1)

    server = ThreadedTCPServer((host, port), OCRHandler)
    server.ocr_model = ocr_model
    server.should_shutdown = False

    print(json.dumps({'status': 'started', 'port': port}), flush=True)

    try:
        # Serve until a handler sets should_shutdown True
        while not server.should_shutdown:
            server.handle_request()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=18765)
    args = parser.parse_args()
    run_server(host=args.host, port=args.port)
