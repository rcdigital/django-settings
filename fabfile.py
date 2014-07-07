from __future__ import with_statement
import datetime
from fabric.api import cd, env, sudo, local, prompt, put, run
from fabric.context_managers import settings, prefix
from fabric.colors import blue, red
import user

global repo_path

def dev():
    global repo_path
    repo_path = '/sites/{{PROJECT_NAME}}'
    env.user = user.name
    env.hosts = ['{{DEV_IP}}']

def prod():
    global repo_path
    repo_path = '/sites/{{PROJECT_NAME}}'
    env.user = user.name
    env.hosts = ['{{PROD_IP}}']

def config():
    global repo_path
    _printOut('Creating repo on: '+str(env.hosts))
    with cd('/sites/'):
        sudo('hg clone ssh://hg@bitbucket.org/rccomunicacao/{{PROJECT_NAME}}', user='www-data')
    with cd(repo_path):
        sudo('virtualenv --distribute env', user='www-data')
        with prefix('source env/bin/activate'):
            print('Installing environment')
            sudo('pip install -r requirements.txt', user='www-data')
            sudo('cp {{PROJECT_ID}}/local_settings_template.py {{PROJECT_ID}}/local_settings.py', user='www-data')
            database_name = prompt('Name of MySQL database to be created: ', default='{{PROJECT_ID}}')
            sudo('mysql -u root -p -e "create database %s"'%database_name, user='www-data')
            print('Now starting the configure of the local_settings.py module')
        config_local_settings()
        put('{{PROJECT_ID}}/server_local_settings.py', '{{PROJECT_ID}}/local_settings.py', use_sudo=True)
        sudo('chown www-data:www-data {{PROJECT_ID}}/local_settings.py')
        with prefix('source env/bin/activate'):
            sudo('python manage.py syncdb', user='www-data')
        print('Configure wsgi bridge file')
        config_wsgi_file()
        sudo('mkdir apache', user='www-data')
        put('apache_wsgi.wsgi', 'apache/django.wsgi', use_sudo=True)
        sudo('chown www-data:www-data apache/django.wsgi')
    sudo('/etc/init.d/apache2 reload')

def config_wsgi_file():
    global repo_path
    # Read template file
    with open('apache_wsgi.template') as f:
        configurations = f.read()
    # Write configuration file with user options
    new_config = open('apache_wsgi.wsgi', 'w')
    new_config.write(
            configurations \
            .replace('{{PROJECT_PATH}}', repo_path) \
            .replace('{{MODULE_NAME}}', 'tempo')
            )
    new_config.close()

def config_local_settings():
    global repo_path
    # Read template file
    with open('{{PROJECT_ID}}/local_settings_template.py') as f:
        configurations = f.read()
    # Write configuration file with user options
    new_config = open('{{PROJECT_ID}}/server_local_settings.py', 'w')
    new_config.write(
            configurations \
            .replace('{{PATH}}', repo_path+'/') \
            .replace('{{SECRET}}', prompt('Some unique string for hashs: ')) \
            .replace('{{DB_TYPE}}', prompt('Type of db (mysql, sqlite3): ', default='mysql')) \
            .replace('{{DB_NAME}}', prompt('Name of database: ', default='tempo')) \
            .replace('{{DB_USER}}', prompt('Database username: ', default='root')) \
            .replace('{{DB_PASS}}', prompt('Database password: ')) \
            .replace('{{DB_HOST}}', prompt('Database host, empty for localhost: ')) \
            .replace('{{DB_PORT}}', prompt('Database port, empty for default: ')) \
            .replace('{{ADMIN_NAME}}', prompt('Admin name, used for receiving log emails: ')) \
            .replace('{{ADMIN_EMAIL}}', prompt('Admin email, used for receiving log emails: '))
            )
    new_config.close()

def update(branch='default'):
    _printOut('Updating server on: '+str(env.hosts))
    _push_changes()
    update_server(branch)
    update_static()

def _push_changes():
    _printOut('Pushing local changes to repo')
    with settings(warn_only=True):
        local('hg push')

def update_server(branch):
    global repo_path
    _printOut('Uploading to dev server on :'+str(env.hosts))
    with cd(repo_path):
        sudo('hg pull', user='www-data')
        sudo('hg up '+branch, user='www-data')
    sudo('/etc/init.d/apache2 reload')

def update_static():
    with cd(repo_path):
        with prefix('source env/bin/activate'):
            sudo('python manage.py collectstatic', user='www-data')

def create_user():
    _printOut('Creating an user profile:')
    user_name = prompt('Username to grant access: ')
    local("echo 'name = \"%s\"' | tee user.py" % user_name)

def _printOut(message):
    print("\n---------------------------")
    print(blue(message))
    print("---------------------------\n")
