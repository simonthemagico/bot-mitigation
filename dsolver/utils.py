def fix_proxy(proxy):
    if isinstance(proxy, str):
        if proxy.count(':') == 4:
            proxy = proxy.split(':')
            if proxy[-1].isdigit():
                proxy = proxy[-2:] + proxy[:-2]
            proxy = f'{proxy[0]}:{proxy[1]}@{proxy[2]}:{proxy[3]}'
        elif proxy.count(':') == 2:
            proxy = f'{proxy[0]}:{proxy[1]}'
    elif isinstance(proxy, dict):
        proxy_string = f'{proxy["host"]}:{proxy["port"]}'
        if all([proxy['user'], proxy['password']]):
            proxy_string = f'{proxy["user"]}:{proxy["password"]}@{proxy_string}'
        proxy = proxy_string
    return proxy