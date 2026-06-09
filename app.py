from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_wtf import FlaskForm
from wtforms import StringField, DateField, PasswordField, SubmitField, validators
from datetime import timedelta
import hashlib
import psycopg2
import psycopg2.extras
import dbconn

app = Flask(__name__, template_folder='templates', static_url_path='/static', static_folder='static')

# 設定金鑰與 Session 存續時間 (3分鐘)
app.secret_key = 'fd4723e200261a2271ea912571eaaa1d'
app.permanent_session_lifetime = timedelta(minutes=3)

# 資料庫連線方法
def get_db_connection():
    conn = psycopg2.connect(
        host=dbconn.host,
        database=dbconn.database,
        user=dbconn.user,
        password=dbconn.password
    )
    return conn


# WTForms 註冊表單定義 (保留原功能供註冊頁使用)
class RegistrationForm(FlaskForm):
    username = StringField('帳號', [validators.DataRequired(), validators.Length(min=4, max=50)])
    userpass = PasswordField('密碼', [validators.DataRequired(), validators.Length(min=8, max=50), validators.EqualTo('confirm', message='密碼必須與確認密碼一樣')])
    confirm = PasswordField('確認密碼')
    name = StringField('姓名', [validators.DataRequired(), validators.Length(min=2, max=8)])
    birthday = DateField('生日', format='%Y-%m-%d')
    phone = StringField('電話', [validators.DataRequired(), validators.Length(min=7, max=13)])
    address = StringField('地址', [validators.Length(min=6, max=50)])
    email = StringField('電子郵件', [validators.DataRequired(), validators.Length(min=6, max=50)])
    submit = SubmitField('立即註冊')


# 路由：首頁（高訂高跟鞋 ZHEN 一頁式核心官網）
@app.route('/')
@app.route('/index')
def index():
    # 順便把登入的會員姓名帶去首頁渲染 (選填)
    user_name = session.get('user_name')
    return render_template('index.html', user_name=user_name)


# 路由：商品頁
@app.route('/product')
def product():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT pno, pname, unitprice, description, category FROM product ORDER BY pno;")
    products = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('product.html', products=products)


# 預留的品牌故事與服務路由
@app.route('/aboutus')
def aboutus(): 
    return "<h3>關於 ZHEN 品牌美學（建構中）</h3>"

@app.route('/contactus')
def contactus(): 
    return "<h3>預約 VIP 私人試鞋體驗（建構中）</h3>"


# 路由：進入精品試鞋間顯示頁面 (GET)
@app.route('/member/signin')
def signin():
    # 如果已經登入過 mid，直接導向 VIP 會員中心
    if 'mid' in session:
        return redirect(url_for('user'))
    return render_template('member/signin.html')


# ✨ 核心修改：處理登入驗證 (POST) -> 改用 member 表的 mid 與 phone
@app.route('/member/login', methods=["POST"])
def login():
    if request.method == 'POST':
        # 1. 接收你在 signin.html 修改後的 name="mid" 與 name="phone"
        mid = request.form.get('mid')
        phone = request.form.get('phone')
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # 2. 修改 SQL 語句：直接向 member 資料表比對會員編號與手機號碼，並順便把姓名(name)撈出來
        SQL = "SELECT mid, phone, name FROM member WHERE mid = %s AND phone = %s;"
        cursor.execute(SQL, (mid, phone))
        user = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        # 3. 驗證比對
        if user:
            session.permanent = True
            session['mid'] = user['mid']         # 把會員編號存入 Session 替代舊的 username
            session['user_name'] = user['name']   # 把真正的姓名存下來，方便在會員中心或首頁稱呼
            return redirect(url_for('user', message='尊榮成員登入成功!'))
        else:
            # 當輸入錯誤時，利用 flash 傳送通知給 signin.html 顯示紅字提示
            flash('您輸入的會員編號或手機號碼有誤，請重新確認。')
            return redirect(url_for('signin'))


# ✨ 核心修改：VIP 專屬沙龍（會員中心）
@app.route('/user')
def user():
    # 檢查 session 改為比對 'mid'
    if 'mid' in session:
        mid = session['mid']
        user_name = session['user_name']
        message = request.args.get('message', '')
        # 傳送真正的姓名(name)跟編號給 user.html 網頁渲染
        return render_template('user.html', name=user_name, mid=mid, message=message)
    return redirect(url_for('signin'))


# 路由：尊榮入會註冊頁面顯示
@app.route('/member/signup')
def signup():
    regform = RegistrationForm()
    return render_template('member/signup.html', form=regform)


# 路由：處理註冊資料提交 (維持原功能不變，確保連動正常)
@app.route('/member/join', methods=["POST"])
def join():
    regform = RegistrationForm()
    if regform.validate_on_submit():
        username = regform.username.data
        userpass = regform.userpass.data
        name = regform.name.data
        birthday = regform.birthday.data
        phone = regform.phone.data
        address = regform.address.data
        email = regform.email.data
        
        md = hashlib.md5()
        md.update(userpass.encode('utf-8'))
        hashpass = md.hexdigest()

        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM member")
        count = cursor.fetchone()[0]
        mid = 'm' + str(count + 1).zfill(4)
        
        SQL2 = "INSERT INTO member (mid, name, birthday, phone, address, email) VALUES (%s, %s, %s, %s, %s, %s);"
        cursor.execute(SQL2, (mid, name, birthday, phone, address, email))
        
        SQL3 = "INSERT INTO account (mid, username, userpass) VALUES (%s, %s, %s);"
        cursor.execute(SQL3, (mid, username, hashpass))
        
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('signin'))
        
    return render_template('member/signup.html', form=regform)


# ✨ 核心修改：離開試鞋間（登出）
@app.route('/member/logout')
def logout():
    # 安全清空所有登入 session 紀錄
    session.clear()
    return redirect(url_for('signin'))


if __name__ == '__main__':
    app.run(debug=True)