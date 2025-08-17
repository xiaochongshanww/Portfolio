from app import create_app
application = create_app()

if __name__ == '__main__':
    print('[WSGI] starting app ...')
    try:
        app = create_app()
        print('[WSGI] app created, will run host=0.0.0.0 port=5000')
        try:
            app.run(host='0.0.0.0', port=5000, use_reloader=False)
            print('[WSGI] application.run returned WITHOUT exception')
        except Exception as run_exc:
            import traceback, sys
            print('[WSGI][ERROR] application.run raised exception:', run_exc)
            traceback.print_exc()
        finally:
            # 如果 run 提前返回，保持进程阻塞便于排查
            import time
            print('[WSGI] entering post-run hold loop (unexpected early return)')
            while True:
                time.sleep(60)
    finally:
        print('[WSGI] main block exiting (should normally not happen)')
