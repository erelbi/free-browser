from flask import Flask, render_template,Response,redirect,url_for
from celery import Celery
import subprocess
import socket
import time
import json
import tempfile
import random
import string


app = Flask(__name__,template_folder='templates',static_folder='static')


# Celery ayarlarını yapın
app.config['CELERY_BROKER_URL'] = 'redis://127.0.0.1'
app.config['CELERY_RESULT_BACKEND'] = 'redis://127.0.0.1'
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)


# Kullanılmayan bir port aralığı belirleyin
start_port = 6800
end_port = 6802
selected_port = None
password = None

def find_unused_port(start_port, end_port):
    for port in range(start_port, end_port + 1):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', port))
        if result != 0:
            return port
        sock.close()
    return None

@celery.task
def docker_remove(container_id,random_dir):
    if container_id:
        stop_command = f"docker stop {container_id}"
        remove_command = f"docker rm  -vf {container_id}"
        remove_dir =   f"rm -rf {random_dir}"

        try:
            subprocess.run(stop_command, shell=True, check=True)
            subprocess.run(remove_command, shell=True, check=True)
            print("Container stop and remove.")
        except subprocess.CalledProcessError as e:
            print(f"Hata: {e}")

def generate_password(length=8):
    try:
        characters = string.ascii_letters + string.digits
        password = ''.join(random.choice(characters) for _ in range(length))
        return password
    except:
        return 'fp-proxy'



def start_and_stop_container():
        unused_port = find_unused_port(start_port, end_port)
        random_dir = tempfile.mkdtemp(dir='/tmp')
        password = generate_password()
        
        if unused_port is not None:
    
            docker_command = f"docker run -d -p {unused_port}:5800 -v {random_dir}:/config:rw --privileged -e VNC_PASSWORD={password} --shm-size 2g jlesage/firefox"

            try:
                result = subprocess.run(docker_command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if result.returncode == 0:
                    container_id = result.stdout.strip()  
                    result = docker_remove.apply_async(args=[container_id,random_dir], countdown=90)
                    return [password,unused_port]
                else:
                    return 'container can not start'
            except subprocess.CalledProcessError as e:
                return f"error: {e}"
        else:
             return 'Please wait'
        
@app.route('/get_container')
def get_container():
    try:
        result = subprocess.run(['docker', 'ps'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode == 0:
            docker_ps_output = result.stdout
            container_count = docker_ps_output.count('\n') - 1
            return json.dumps(container_count)
        else:
            return 'error'

    except subprocess.CalledProcessError as e:
        print(f'Error: {e}')
 

@app.route('/')
def index():
    #return render_template('index.html')
    return render_template('index.html')
@app.route('/start_container', methods=['POST'])
def start_container():
    # Celery işini başlat
    c_value = start_and_stop_container()
    if  isinstance(c_value, list):
        return render_template('index.html', url="http://158.178.145.106:{}".format(c_value[1]),password=c_value[0])
    else:
        return 'It occurred with an error. please try again later.'
  
    

if __name__ == '__main__':
    app.run(debug=True)
