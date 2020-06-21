# Тут лежат все найстройки
set_easyrsadir = 'easyrsa'
set_htmldir = 'html'

set_httpserver_ip = '0.0.0.0'
set_httpserver_port = 8888

# Ключ для входа на сервера
set_ssh_key = 'ssh/id_rsa'
# Сервера, на которые нужно вносить изменения
# Вход по ssh, с использованием ключа
set_servers = [{
    'ip': '185.231.153.5',
    'port': 22,
    'user': 'root',
    'dir': '/etc/openvpn/server/'
}, {
    'ip': '62.113.113.199',
    'port': 22,
    'user': 'root',
    'dir': '/etc/openvpn/server/'
}]

# Пустой конфиг для клиентов, в который будем вставлять ключи
set_sample_ovpn = 'client.ovpn.sample'
