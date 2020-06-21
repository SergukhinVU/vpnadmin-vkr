function apirequest_getusers(){
    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/getusers', true);
    xhr.onload = function (e) {
      if (xhr.readyState === 4) {
        if (xhr.status === 200) {
            data =  JSON.parse(xhr.responseText);
            if (data.status == 0) {
                updateusers(data.users)
            }else{
                alert(data.errortext)
            }
        }
      }
    };
    xhr.send(null);
}

function apirequest_getuserovpn(username){
    if (username){
        window.open('/api/getuserovpn/' + username,'_blank')
    }
}

function apirequest_revokeuser(username){
    if (username){
        var xhr = new XMLHttpRequest();
        xhr.open('POST', '/api/revokeuser', true);
        xhr.onload = function (e) {
          if (xhr.readyState === 4) {
            if (xhr.status === 200) {
                data =  JSON.parse(xhr.responseText);
                if (data.status == 0) {
                    apirequest_getusers();
                    alert('Пользователь отозван')
                }else{
                    alert(data.errortext)
                }
            }
          }
        };
        xhr.setRequestHeader('Content-type', 'application/json; charset=utf-8');
        var json = JSON.stringify({
            'username': username
        });
        xhr.send(json);
    }
}

function apirequest_restoreuser(username){
    if (username){
        var xhr = new XMLHttpRequest();
        xhr.open('POST', '/api/restoreuser', true);
        xhr.onload = function (e) {
          if (xhr.readyState === 4) {
            if (xhr.status === 200) {
                data =  JSON.parse(xhr.responseText);
                if (data.status == 0) {
                    apirequest_getusers();
                    alert('Пользователь востановлен')
                }else{
                    alert(data.errortext)
                }
            }
          }
        };
        xhr.setRequestHeader('Content-type', 'application/json; charset=utf-8');
        var json = JSON.stringify({
            'username': username
        });
        xhr.send(json);
    }
}

function apirequest_adduser(){
    var username = prompt('Имя нового пользователя');
    if (username){
        var xhr = new XMLHttpRequest();
        xhr.open('POST', '/api/adduser', true);
        xhr.onload = function (e) {
          if (xhr.readyState === 4) {
            if (xhr.status === 200) {
                data =  JSON.parse(xhr.responseText);
                if (data.status == 0) {
                    apirequest_getusers();
                    alert('Пользователь добавлен')
                }else{
                    alert(data.errortext)
                }
            }
          }
        };
        xhr.setRequestHeader('Content-type', 'application/json; charset=utf-8');
        var json = JSON.stringify({
            'username': username
        });
        xhr.send(json);
    }
}

function updateusers(data){
    <!--Чистим таблицы-->
    for (var i = document.getElementById('validusers').getElementsByTagName('tr').length -1; i; i--) {
        document.getElementById('validusers').deleteRow(i);
    }
    for (var i = document.getElementById('revokeusers').getElementsByTagName('tr').length -1; i; i--) {
        document.getElementById('revokeusers').deleteRow(i);
    }
    <!--Добавляем свежие данные-->
    data.forEach(function(item) {
        new_row = document.createElement("tr");
        td_name = document.createElement("td");
        td_name.appendChild(document.createTextNode(item.cert_name));
        td_key = document.createElement("td");
        td_key.appendChild(document.createTextNode(item.cert_hash));
        new_row.appendChild(td_name);
        new_row.appendChild(td_key);
        if (item.valid){
            td_butt = document.createElement("td");
            bb = document.createElement("input");
            bb.type = "button";
            bb.value = 'Отозвать';
            bb.setAttribute("onclick", "apirequest_revokeuser('" + item.cert_name + "')");
            td_butt.appendChild(bb);
            bb = document.createElement("input");
            bb.type = "button";
            bb.value = 'Получить .ovpn';
            bb.setAttribute("onclick", "apirequest_getuserovpn('" + item.cert_name + "')");
            td_butt.appendChild(bb);

            new_row.appendChild(td_butt);
            document.getElementById('validusers').appendChild(new_row);
        }else{
            td_butt = document.createElement("td");
            bb = document.createElement("input");
            bb.type = "button";
            bb.value = 'Востановить';
            bb.setAttribute("onclick", "apirequest_restoreuser('" + item.cert_name + "')");
            td_butt.appendChild(bb);
//            bb = document.createElement("input");
//            bb.type = "button";
//            bb.value = 'Получить .ovpn';
//            bb.setAttribute("onclick", "apirequest_getuserovpn('" + item.cert_name + "')");
//            td_butt.appendChild(bb);

            new_row.appendChild(td_butt);
            document.getElementById('revokeusers').appendChild(new_row);
        }
    });
}