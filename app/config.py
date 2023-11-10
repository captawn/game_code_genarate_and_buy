# this is a sample config file. rename it to `config.py` and edit accordingly

API_KEY = 'put your API key from kavenegar here'

# Mysql configs
MYSQL_HOST = 'localhost'
MYSQL_USERNAME = 'root'
MYSQL_PASSWORD = 'root'
MYSQL_DB_NAME = 'pt'


# call back url from KaveNegar will look like
# /v1/CALL_BACK_TOKEN/process
CALL_BACK_TOKEN = 'CALL BACK TOKEN'

# login cedentials
USERNAME = 'ramin'
PASSWORD = 'pass'

# generate one strong secret key for flask.
SECRET_KEY = 'random long string with alphanumeric + #()*&'


### Do not change below unless you know what you are doing
UPLOAD_FOLDER = 'C:/tmp/sms_serial_verification/UPLOAD_FOLDER'
ALLOWED_EXTENSIONS = {'xlsx'} 

### remote systems can call this program like 
### /v1/{REMOTE_CALL_API_KEY}/check_one_serial/<serial> and check one serial, returns back json
REMOTE_CALL_API_KEY = 'set_unguessable_remote_api_key_lkjdfljerlj3247LKJ'