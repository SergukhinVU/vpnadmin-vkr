import json
import shlex
from http.server import BaseHTTPRequestHandler, HTTPServer
from subprocess import Popen, PIPE
import string
import shutil

import settings

set_easyrsadir = settings.set_easyrsadir
set_httpserver_ip = settings.set_httpserver_ip
set_httpserver_port = settings.set_httpserver_port
set_htmldir = settings.set_htmldir
set_ssh_key = settings.set_ssh_key
set_servers = settings.set_servers
set_sample_ovpn = settings.set_sample_ovpn


def vpn_add_user(username):
    # Сгенерировать сертификат
    command = "cd " + str(
        set_easyrsadir) + "&& source vars && export EASYRSA_BATCH=1 && ./easyrsa build-client-full " + str(username) + \
              " nopass"
    # Вызываем через баш, а не напрямую для поддержки работы export
    proc = Popen(['/bin/bash', '-c', command], shell=False, stdout=PIPE, stderr=PIPE)

    stderr = bytes.decode(proc.stderr.read(), "utf-8")
    stdout = bytes.decode(proc.stdout.read(), "utf-8")
    # print(stderr)
    # print(stdout)
    if 'Data Base Updated' in stdout:
        # Всё хорошо, пользователь добавлен
        return
    elif 'Request file already exists' in stderr:
        # Пользователь уже существует
        raise RequestFileAlreadyExists('Request key file already exists')


def vpn_revoke_user(username):
    # Отозвать сертификат
    command = "cd " + str(
        set_easyrsadir) + "&& source vars && export EASYRSA_BATCH=1 && ./easyrsa revoke " + str(username)
    # Вызываем через баш, а не напрямую для поддержки работы export
    proc = Popen(['/bin/bash', '-c', command], shell=False, stdout=PIPE, stderr=PIPE)

    stderr = bytes.decode(proc.stderr.read(), "utf-8")
    stdout = bytes.decode(proc.stdout.read(), "utf-8")
    print(stderr)
    print(stdout)
    # Почему-то сообщение об успешном удалении пользовтеля выводится в stderr, вместо stdout, как при добавлении
    if 'Data Base Updated' in stderr:
        # Всё хорошо, пользователь удалён

        # Генерируем crl
        vpn_gen_crl()

        return
    elif 'Unable to revoke as the input' in stderr:
        # Если пользователя не существует или уже удалён
        raise UserNotFound('Unable to revoke as the input file is not a valid certificate. Unexpected')


def vpn_gen_crl():
    command = "cd " + str(
        set_easyrsadir) + "&& source vars && export EASYRSA_BATCH=1 && ./easyrsa gen-crl"
    proc = Popen(['/bin/bash', '-c', command], shell=False, stdout=PIPE, stderr=PIPE)
    stderr = bytes.decode(proc.stderr.read(), "utf-8")
    stdout = bytes.decode(proc.stdout.read(), "utf-8")
    print(stderr)
    print(stdout)


def vpn_get_users():
    users_dict = []
    with open(set_easyrsadir + '/pki/index.txt', 'r') as f:
        for line in f.readlines():
            line = line.split('\t')
            users_dict.append({
                'valid': True if line[0] == 'V' else False,
                'date_create': line[1],
                'date_close': line[2],
                'cert_hash': line[3],
                'cert_name': line[5].rstrip().replace('/CN=', '')
            })
    return users_dict


def vpn_push_crl():
    for server in set_servers:
        # Залить сертификат
        # command = "scp -i " + set_ssh_key + " -p " + str(server['port']) + " " + set_easyrsadir + "/pki/crl.pem " + \
        #           str(server['user']) + "@" + server['ip'] + ":" + server['dir'] + 'keys/'
        command = 'scp -i {ssh_key_file} -P {s_port} {easyrsa_dir}/pki/crl.pem {s_user}@{s_ip}:{s_dir}keys/'
        command = command.format(ssh_key_file=set_ssh_key,
                                 s_port=server['port'],
                                 easyrsa_dir=set_easyrsadir,
                                 s_user=server['user'],
                                 s_ip=server['ip'],
                                 s_dir=server['dir'])
        proc = Popen(['/bin/bash', '-c', command], shell=False, stdout=PIPE, stderr=PIPE)

        stderr = bytes.decode(proc.stderr.read(), "utf-8")
        stdout = bytes.decode(proc.stdout.read(), "utf-8")
        print(stderr)
        print(stdout)

        # Перезапустить openVPN
        command = 'ssh  -p {s_port} -i {ssh_key_file} {s_user}@{s_ip} "systemctl restart openvpn-server@server.service"'
        command = command.format(ssh_key_file=set_ssh_key,
                                 s_port=server['port'],
                                 s_user=server['user'],
                                 s_ip=server['ip'])
        proc = Popen(['/bin/bash', '-c', command], shell=False, stdout=PIPE, stderr=PIPE)

        stderr = bytes.decode(proc.stderr.read(), "utf-8")
        stdout = bytes.decode(proc.stdout.read(), "utf-8")
        print(stderr)
        print(stdout)

    return


def vpn_get_userovpn(username):
    # Так сказать системные файлы
    try:
        with open(set_sample_ovpn, 'r') as f:
            ovpn_text = f.read()

        # Вероятно это можно и красивее написать, но так понятнее
        # ca.crt
        with open(set_easyrsadir + '/pki/ca.crt', 'r') as f:
            ca_crt = f.read()
        # ta.key
        with open(set_easyrsadir + '/pki/ta.key', 'r') as f:
            ta_key = f.read()
    except FileNotFoundError:
        raise SystemFileNotFound()
    # Клиентские
    try:
        # Ниже конкретно пользовательские
        # client.crt
        with open(set_easyrsadir + '/pki/issued/' + username + '.crt', 'r') as f:
            client_crt = f.read()
        # client.key
        with open(set_easyrsadir + '/pki/private/' + username + '.key', 'r') as f:
            client_key = f.read()
    except FileNotFoundError:
        raise UserNotFound()

    ovpn_text = ovpn_text.format(ca_crt=ca_crt, ta_key=ta_key, client_crt=client_crt, client_key=client_key)
    return ovpn_text


def vpn_save_new_db(users_dict):
    with open(set_easyrsadir + '/pki/index.txt', 'w') as f:
        for user in users_dict:
            # Валидность
            if user['valid']:
                f.write('V\t')
            else:
                f.write('R\t')
            # Дата создания
            f.write(str(user['date_create']) + '\t')
            # Дата отзыва
            f.write(str(user['date_close']) + '\t')
            # Хэш
            f.write(str(user['cert_hash']) + '\t')
            # Не нашёл что это в документации
            f.write('unknown\t')
            # Имя сертификата
            f.write('/CN=' + str(user['cert_name']))
            f.write('\n')


def vpn_restory_user(username):
    # Загружаем всех пользователей
    users_dict = vpn_get_users()
    # Станет True, если мы найдём пользователя в отозваных
    finded = False
    for user in users_dict:
        if user['valid'] == False and user['cert_name'] == username:
            finded = True

            # Востанавливаем его
            # Для начала востанавливаем файлы
            # Сертификат
            shutil.copyfile(set_easyrsadir + '/pki/revoked/certs_by_serial/' + str(user['cert_hash']) + '.crt',
                            set_easyrsadir + '/pki/certs_by_serial/' + str(user['cert_hash']) + '.pem')
            shutil.move(set_easyrsadir + '/pki/revoked/certs_by_serial/' + str(user['cert_hash']) + '.crt',
                        set_easyrsadir + '/pki/issued/' + str(user['cert_name']) + '.crt')
            # Ключ
            shutil.move(set_easyrsadir + '/pki/revoked/private_by_serial/' + str(user['cert_hash']) + '.key',
                        set_easyrsadir + '/pki/private/' + str(user['cert_name']) + '.key')

            # req
            shutil.move(set_easyrsadir + '/pki/revoked/reqs_by_serial/' + str(user['cert_hash']) + '.req',
                        set_easyrsadir + '/pki/reqs/' + str(user['cert_name']) + '.req')

            # Востанавливаем в базе
            user['valid'] = True
            user['date_close'] = ''

            break
    # Если востановили пользователя, сохраняем базу
    if finded:
        vpn_save_new_db(users_dict)

        # Генерируем crl
        vpn_gen_crl()

        return
    else:
        # Если нет такого пользователя в отзваных, сообщаем ошибку
        raise UserNotFound('Такого пользователя нет среди удалённых')


class RequestHandler(BaseHTTPRequestHandler):

    def _send_cors_api_headers(self):
        # Загогловки для CORS
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "x-api-key,Content-Type")

    # Если пользоатель есть - отправим его конфиг текстом, если нет - 404.
    def httpapi_get_getuserovpn(self, username):
        # Если прислали пустое или наличие спецсимволов '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~ ' - 404
        if username == '' or not set(string.punctuation + ' ').isdisjoint(username):
            self.send_response(404)
            self.end_headers()
        else:
            try:
                textovpn = vpn_get_userovpn(username)
                # Отдаём в виде простого текста
                self.send_response(200)
                self._send_cors_api_headers()
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.send_header('Content-Disposition', 'attachment; filename="' + username + '.ovpn"')
                self.end_headers()
                self.wfile.write(textovpn.encode())
            # Если какая-то ошибка - 404
            except (SystemFileNotFound, UserNotFound):
                self.send_response(404)
                self.end_headers()
        return

    def httpapi_post_getusers(self):
        self.send_response(200)
        self._send_cors_api_headers()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            'status': '0',
            'users': vpn_get_users()
        }).encode())
        return

    def httpapi_post_adduser(self):
        data_string = self.rfile.read(int(self.headers['Content-Length']))
        data = json.loads(data_string)
        self.send_response(200)
        self._send_cors_api_headers()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        try:
            username = str(data['username'])
        except IndexError:
            username = ''
        # Проверяем чтоб пустое имя пользователя не прислали
        if username == '':
            # Если прислали пустое - отправляем ошибку
            # Так же у нас проверка на пустое имя реализовано и на фронтенде, но нужно и тут проверять
            self.wfile.write(json.dumps({
                'status': '100',
                'errortext': 'Имя пользователя не может быть пустым'
            }).encode())
        # Проверяем наличие спецсимволов '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~ '
        elif not set(string.punctuation + ' ').isdisjoint(username):
            self.wfile.write(json.dumps({
                'status': '100',
                'errortext': 'Имя пользователя содержит запрещённые символы'
            }).encode())
        # Если всё ок, пробуем создать ползователя
        else:
            try:
                vpn_add_user(username)
                # Если ок, возвращаем успех
                self.wfile.write(json.dumps({
                    'status': '0'
                }).encode())
            # Если easyrsa сообщет что сертификат с таким именем уже существует
            except RequestFileAlreadyExists:
                self.wfile.write(json.dumps({
                    'status': '100',
                    'errortext': 'Пользователь уже существует'
                }).encode())
        return

    def httpapi_post_revokeuser(self):
        data_string = self.rfile.read(int(self.headers['Content-Length']))
        data = json.loads(data_string)
        self.send_response(200)
        self._send_cors_api_headers()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        try:
            username = str(data['username'])
        except IndexError:
            username = ''
        # Проверяем чтоб пустое имя пользователя не прислали
        if username == '':
            # Если прислали пустое - отправляем ошибку
            # Так же у нас проверка на пустое имя реализовано и на фронтенде, но нужно и тут проверять
            self.wfile.write(json.dumps({
                'status': '100',
                'errortext': 'Имя пользователя не может быть пустым'
            }).encode())
        # Проверяем наличие спецсимволов '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~ '
        elif not set(string.punctuation + ' ').isdisjoint(username):
            self.wfile.write(json.dumps({
                'status': '100',
                'errortext': 'Имя пользователя содержит запрещённые символы'
            }).encode())
        # Если всё ок, пробуем создать ползователя
        else:
            try:
                # Удаляем пользователя из базы
                vpn_revoke_user(username)
                # Обновляем crl и рассылаем по серверам
                vpn_push_crl()
                # Если ок, возвращаем успех
                self.wfile.write(json.dumps({
                    'status': '0'
                }).encode())
            # Если easyrsa сообщет что сертификат с таким именем уже существует
            except UserNotFound:
                self.wfile.write(json.dumps({
                    'status': '100',
                    'errortext': 'Пользователь не существует или уже был удалён'
                }).encode())
        return

    def httpapi_post_restoreuser(self):
        data_string = self.rfile.read(int(self.headers['Content-Length']))
        data = json.loads(data_string)
        self.send_response(200)
        self._send_cors_api_headers()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        try:
            username = str(data['username'])
        except IndexError:
            username = ''
        # Проверяем чтоб пустое имя пользователя не прислали
        if username == '':
            # Если прислали пустое - отправляем ошибку
            # Так же у нас проверка на пустое имя реализовано и на фронтенде, но нужно и тут проверять
            self.wfile.write(json.dumps({
                'status': '100',
                'errortext': 'Имя пользователя не может быть пустым'
            }).encode())
        # Проверяем наличие спецсимволов '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~ '
        elif not set(string.punctuation + ' ').isdisjoint(username):
            self.wfile.write(json.dumps({
                'status': '100',
                'errortext': 'Имя пользователя содержит запрещённые символы'
            }).encode())
        # Если всё ок, пробуем создать ползователя
        else:
            try:
                # Востанавливаем пользователя
                vpn_restory_user(username)
                # Обновляем crl и рассылаем по серверам
                vpn_push_crl()
                # Если ок, возвращаем успех
                self.wfile.write(json.dumps({
                    'status': '0'
                }).encode())
            # Если сообщает что такого пользователя нет
            except UserNotFound:
                self.wfile.write(json.dumps({
                    'status': '100',
                    'errortext': 'Пользователь не существует'
                }).encode())
        return

    def do_GET(self):
        # Без указания файла отдаём index.html
        path = self.path.split('/')
        if self.path == '/':
            self.path = '/index.html'

        # Если у нас обращение к api
        if path[1] == 'api':
            # Запрос получения конфиг файла
            if path[2] == 'getuserovpn':
                # Проверяем наличие имени пользователя
                try:
                    username = path[3]
                except IndexError:
                    username = ''
                self.httpapi_get_getuserovpn(str(username))
        # Если запрос не к api, просто отдём файл
        else:
            try:
                with open(set_htmldir + str(self.path), 'rb') as f:
                    # Код ответа (200, 404 и тд.)
                    self.send_response(200)
                    # Заголовки
                    self.end_headers()
                    # Сам файл
                    self.wfile.write(f.read())
            except FileNotFoundError:
                # Если нет файла
                self.send_response(404)
                self.end_headers()

        return

    def do_POST(self):
        path = self.path.split('/')
        if path[1] == 'api':
            # Запрос списка пользователей
            if path[2] == 'getusers':
                self.httpapi_post_getusers()
            # Запрос добавления пользователя
            elif path[2] == 'adduser':
                self.httpapi_post_adduser()
            # Запрос отзыва пользователя
            elif path[2] == 'revokeuser':
                self.httpapi_post_revokeuser()
            # Запрос востановления пользователя
            elif path[2] == 'restoreuser':
                self.httpapi_post_restoreuser()
        else:
            self.send_response(404)
            self.end_headers()

        return

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_api_headers()
        self.end_headers()


class Error(Exception):
    pass


# Пользователь уже существует
class RequestFileAlreadyExists(Error):
    def __init__(self, message):
        self.message = message


# Не нашли ключи пользователя
class UserNotFound(Error):
    pass


# Не нашли какие-то нужные файлы, не относящиеся к пользоватлю
class SystemFileNotFound(Error):
    pass


# u = vpn_get_users()
# vpn_save_new_db(u)

# vpn_restory_user('iii')

# vpn_revoke_user('123')
# print(vpn_get_userovpn('test2'))
# vpn_push_crl()
# exit(0)
server_address = (set_httpserver_ip, set_httpserver_port)
httpd = HTTPServer(server_address, RequestHandler)
httpd.serve_forever()
