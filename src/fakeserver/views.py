from utils import JSONResponse

def proxy(request):
    cmd = request.POST.get('cmd', '')
    mac = request.POST.get('mac', '')
    proxy = {'username': 'macumba', 'password':'12345', 'host': 'localhost', 'port': 1956}

    if cmd == 'login':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        return JSONResponse({'authenticated': True, 'error': None, 'full_name': "Junao", 'time': 60, 'up_apps': [['firefox', 'http://www.gmail.com'], ['xterm', '-c', 'python']]})#, 'http_proxy': proxy})

    elif cmd == 'identify':
        return JSONResponse({'name': 'Xuxu na Feira',})

    elif cmd == 'check_time':
        return JSONResponse({'logout': True, 'clean_apps': ['pidgin', 'rhythmbox'], 'error': None, 'full_name': "Junao", 'time': 60, 'after_action':0})#, 'http_proxy': proxy})

    elif cmd == 'logout':
        return JSONResponse({'error': None, 'clean_apps': ['pidgin', 'rhythmbox']})
