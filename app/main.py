import os
from datetime import datetime

import random
import string
import subprocess

import MySQLdb
from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from werkzeug.utils import secure_filename

import config

############################# end import##################################

app = Flask(__name__)
limiter = Limiter(get_remote_address, app=app)

MAX_FLASH = 10
UPLOAD_FOLDER = config.UPLOAD_FOLDER
ALLOWED_EXTENSIONS = config.ALLOWED_EXTENSIONS
CALL_BACK_TOKEN = config.CALL_BACK_TOKEN

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# flask-login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message_category = 'danger'


app.config.update(SECRET_KEY=config.SECRET_KEY)

# user
class User(UserMixin):
    """ A minimal and singleton user class used only for administrative tasks """
    def __init__(self, id):
        self.id = id

    def __repr__(self):
        return "%d" % (self.id)


user = User(0)


@app.route('/db_status/', methods=['GET'])
@login_required
def db_status():

    """ show some status about the DB """

    
    db = get_database_connection()
    cur = db.cursor()
    
    # collect some stats for the GUI
    try:
        cur.execute("SELECT count(*) FROM serials")
        num_serials = cur.fetchone()[0]
    except:
        num_serials = 'can not query serials count'

    try:
        cur.execute("SELECT count(*) FROM invalids")
        num_invalids = cur.fetchone()[0]
    except:
        num_invalids = 'can not query invalid count'

    try:
        cur.execute("SELECT log_value FROM logs WHERE log_name = 'import'")
        log_import = cur.fetchone()[0]
    except:
        log_import = 'can not read import log results... yet'

    try:
        cur.execute("SELECT log_value FROM logs WHERE log_name = 'db_filename'")
        log_filename = cur.fetchone()[0]
    except:
        log_filename = 'can not read db filename from database'

    try:
        cur.execute("SELECT log_value FROM logs WHERE log_name = 'db_check'")
        log_db_check = cur.fetchone()[0]
    except:
        log_db_check = 'Can not read db_check logs... yet'

    return render_template('db_status.html', data={'serials': num_serials, 'invalids': num_invalids, 
                                                   'log_import': log_import, 'log_db_check': log_db_check, 'log_filename': log_filename})


@app.route('/', methods=['GET', 'POST'])
@login_required
def home():
    """ creates database if method is post otherwise shows the homepage with some stats
    see import_database_from_excel() for more details on database creation"""
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            #TODO: is space find in a file name? check if it works
            filename = secure_filename(file.filename)
            filename.replace(' ', '_') # no space in filenames! because we will call them as command line arguments
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            subprocess.Popen(["python", "import_db.py", file_path])
            flash('File uploaded. Will be imported soon. follow from DB Status Page', 'info')
            return redirect('/')

    db = get_database_connection()

    cur = db.cursor()


    # get last 5000 sms
    cur.execute("SELECT * FROM codes ORDER BY active_date DESC LIMIT 5000")
    all_codes = cur.fetchall()
    codes = []
    for code in all_codes:
        code_value = code[1]
        active_date = code[2]
        status = code[3]
        codes.append({'status': status, 'active_date': active_date, 'code_value': code_value})

    # collect some stats for the GUI
    try:
        cur.execute("SELECT count(*) FROM codes WHERE status = 1")
        num_ok = cur.fetchone()[0]
    except: 
        num_ok = 'error'

    try:        
        cur.execute("SELECT count(*) FROM codes WHERE status = 0")
        num_failure = cur.fetchone()[0]
    except:
        num_failure = 'error'

    return render_template('index.html', data={'codes': codes, 'ok': num_ok, 'failure': num_failure})

@app.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    """ user login: only for admin user (system has no other user than admin)
    Note: there is a 10 tries per minute limitation to admin login to avoid minimize password factoring"""
    if current_user.is_authenticated:
        return redirect('/')
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if password == config.PASSWORD and username == config.USERNAME:
            login_user(user)
            return redirect('/')
        else:
            return abort(401)
    else:
        return render_template('login.html')


# @app.route(f"/v1/{config.REMOTE_CALL_API_KEY}/check_one_serial/<serial>", methods=["GET"])
# def check_one_serial_api(serial):
#     """ to check whether a serial number is valid or not using api
#     caller should use something like /v1/ABCDSECRET/check_one_serial/AA10000
#     answer back json which is status = DOUBLE, FAILURE, OK, NOT-FOUND
#     """
#     status, answer = check_serial(serial)
#     ret = {'status': status, 'answer': answer}
#     return jsonify(ret), 200


@app.route("/check_one_serial", methods=["POST"])
@login_required
def check_one_serial():
    code_to_check = request.form["serial"]
    # return code_to_check
    found_code=[]
    found_code = check_code(code_to_check)
    if found_code == 'not found':
        flash(f'{found_code} ', 'info')
    else:
        for code in found_code:
         flash(f'{code} ', 'info')
    return redirect('/')


def generate_random_string(length=30):
    characters = string.ascii_letters + string.digits
    random_string = ''.join(random.choice(characters) for _ in range(length))
    return random_string


@app.route("/register_code", methods=["POST"])
@login_required
def create_code():
    if request.method == 'POST':
        counter = request.form.get('codeCounter', type=int)
        for _ in range(counter):
            random_string = generate_random_string()

            db = get_database_connection()
            cur = db.cursor()
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            status = 1
            cur.execute("INSERT INTO  codes (code, active_date, status) VALUES (%s, %s, %s)", (random_string, current_time, status ))
            db.commit()
            db.close()

    return redirect('/')


@app.route("/user")
# @login_required
def user_method():
    return render_template('user.html', data={})





@app.route("/buy_with_voucher", methods=["POST"])
@login_required
def buy_with_voucher():
    if request.method == 'POST':
        voucher = request.form.get('Voucher')
        check_voucher = check_code(voucher)
        if check_voucher == "not found":
           flash('your Voucher is not valid', 'danger')
           return redirect('/user')
    flash('your Voucher is valid', 'info')

    return redirect('/user')







@app.route("/logout")
@login_required
def logout():
    """ logs out the admin user"""
    logout_user()
    flash('Logged out', 'success')
    return redirect('/login')


#
@app.errorhandler(401)
def unauthorized(error):
    """ handling login failures"""
    flash('Login problem', 'danger')
    return redirect('/login')


# callback to reload the user object
@login_manager.user_loader
def load_user(userid):
    return User(userid)


@app.route('/v1/ok')
def health_check():
    """ for system health check. calling it will answer with json message: ok """
    ret = {'message': 'ok'}
    return jsonify(ret), 200


def get_database_connection():
    """connects to the MySQL database and returns the connection"""
    return MySQLdb.connect(host=config.MYSQL_HOST,
                           user=config.MYSQL_USERNAME,
                           passwd=config.MYSQL_PASSWORD,
                           db=config.MYSQL_DB_NAME,
                           charset='utf8')


# def send_sms(receptor, message):
#     """ gets a MSISDN and a message, then uses KaveNegar to send sms."""
#     url = f'https://api.kavenegar.com/v1/{config.API_KEY}/sms/send.json'
#     data = {"message": message,
#             "receptor": receptor}
#     res = requests.post(url, data)


# def _remove_non_alphanum_char(string):
#     return re.sub(r'\W+', '', string)


# def _translate_numbers(current, new, string):
#     translation_table = str.maketrans(current, new)
#     return string.translate(translation_table)

# def normalize_string(serial_number, fixed_size=30):
#     """ gets a serial number and standardize it as following:
#     >> converts(removes others) all chars to English upper letters and numbers
#     >> adds zeros between letters and numbers to make it fixed length """
#
#     serial_number = _remove_non_alphanum_char(serial_number)
#     serial_number = serial_number.upper()
#
#     persian_numerals = '۱۲۳۴۵۶۷۸۹۰'
#     arabic_numerals = '١٢٣٤٥٦٧٨٩٠'
#     english_numerals = '1234567890'
#
#     serial_number = _translate_numbers(persian_numerals, english_numerals, serial_number)
#     serial_number = _translate_numbers(arabic_numerals, english_numerals, serial_number)
#
#     all_digit = "".join(re.findall("\d", serial_number))
#     all_alpha = "".join(re.findall("[A-Z]", serial_number))
#
#     missing_zeros = "0" * (fixed_size - len(all_alpha + all_digit))
#
#     return f"{all_alpha}{missing_zeros}{all_digit}"



def check_code(code):

    db = get_database_connection()

    with db.cursor() as cur:
        cur.execute("SELECT * FROM codes WHERE code = %s", (code,))
        all_codes = cur.fetchall()
        codes = []
        for code in all_codes:
            code_value = code[1]
            active_date = code[2]
            status = code[3]
            codes.append(
                {'status': status, 'active_date': active_date, 'code_value': code_value})

        if len(codes) == 0:
            return "not found"
        return codes


# @app.route(f'/v1/{CALL_BACK_TOKEN}/process', methods=['POST'])
# def process():
#     """ this is a call back from KaveNegar. Will get sender and message and
#     will check if it is valid, then answers back.
#     This is secured by 'CALL_BACK_TOKEN' in order to avoid mal-intended calls
#     """
#     data = request.form
#     sender = data["from"]
#     message = data["message"]
#
#     status, answer = check_serial(message)
#
#     db = get_database_connection()
#
#     cur = db.cursor()
#
#     log_new_sms(status, sender, message, answer, cur)
#
#     db.commit()
#     db.close()
#
#     send_sms(sender, answer)
#     ret = {"message": "processed"}
#     return jsonify(ret), 200

# def log_new_sms(status, sender, message, answer, cur):
#     if len(message) > 40:
#         return
#     now = time.strftime('%Y-%m-%d %H:%M:%S')
#     cur.execute("INSERT INTO PROCESSED_SMS (status, sender, message, answer, date) VALUES (%s, %s, %s, %s, %s)", (status, sender, message, answer, now))
    
@app.errorhandler(404)
def page_not_found(error):
    """ returns 404 page"""
    return render_template('404.html'), 404



# def create_sms_table():
#     """Creates PROCESSED_SMS table on database if it's not exists."""
#
#     db = get_database_connection()
#
#     cur = db.cursor()
#
#     try:
#         cur.execute("""CREATE TABLE IF NOT EXISTS PROCESSED_SMS (
#             status ENUM('OK', 'FAILURE', 'DOUBLE', 'NOT-FOUND'),
#             sender CHAR(20),
#             message VARCHAR(400),
#             answer VARCHAR(400),
#             date DATETIME, INDEX(date, status));""")
#         db.commit()
#     except Exception as e:
#         flash(f'Error creating PROCESSED_SMS table; {e}', 'danger')
#
#     db.close()


if __name__ == "__main__":
    # nima
    # create_sms_table()
    app.run("0.0.0.0", 5000, debug=False)
