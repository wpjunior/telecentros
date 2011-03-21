from utils import JSONResponse

def proxy(request):
    cmd = request.POST.get('cmd', '')
    mac = request.POST.get('mac', '')
    proxy = {'username': 'macumba', 'password':'12345', 'host': 'localhost', 'port': 1956}

    if cmd == 'login':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        return JSONResponse({'authenticated': True, 'error': None, 'full_name': "Junao", 'time': 15, 'http_proxy': proxy})

    elif cmd == 'identify':
        return JSONResponse({'name': 'Xuxu na Feira',})

    elif cmd == 'check_time':
        return JSONResponse({'logout': False, 'clean_apps': False, 'error': None, 'full_name': "Junao", 'time': 150, 'http_proxy': proxy})

    elif cmd == 'logout':
        return JSONResponse({'error': None})
