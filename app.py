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


# WTForms 註冊表單定義
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
    return render_template('index.html')

# ✨ 核心修改：動態從 PostgreSQL 資料庫撈取 ZHEN 的 5 筆產品，供 product.html 渲染
@app.route('/product')
def product():
    conn = get_db_connection()
    # 使用 RealDictCursor 讓撈出來的資料能像 Python 字典一樣直接用欄位名稱讀取
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # 依照產品編號排序，撈出所有的鞋款資料
    cursor.execute("SELECT pno, pname, unitprice, description, category FROM product ORDER BY pno;")
    products = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    # 完美將資料庫的產品陣列傳送給前端
    return render_template('product.html', products=products)

# 預留的品牌故事與服務路由（如需要可再行擴充為 HTML）
@app.route('/aboutus')
def aboutus(): 
    return "<h3>關於 ZHEN 品牌美學（建構中）</h3>"

@app.route('/contactus')
def contactus(): 
    return "<h3>預約 VIP 私人試鞋體驗（建構中）</h3>"

# 路由：進入精品試鞋間（登入頁）
@app.route('/member/signin')
def signin():
    if 'username' in session:
        return redirect(url_for('user'))
    return render_template('member/signin.html')

# 路由：處理登入驗證 (POST)
@app.route('/member/login', methods=["POST"])
def login():
    if request.method == 'POST':
        username = request.form['username']
        userpassword = request.form['userpassword']
        
        # MD5 加密處理
        md = hashlib.md5()
        md.update(userpassword.encode('utf-8'))
        hashpass = md.hexdigest()
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        SQL = f"SELECT username, userpass FROM account WHERE username='{username}';"
        cursor.execute(SQL)
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user and username == user['username'] and hashpass == user['userpass']:
            session.permanent = True
            session['username'] = username
            return redirect(url_for('user', message='尊榮成員登入成功!'))
        else:
            # ✨ 新增：當輸入錯誤時，利用 flash 傳送通知給 signin.html 顯示紅字提示
            flash('您輸入的精品帳號或密碼有誤，請重新確認。')
            return redirect(url_for('signin'))

# 路由：VIP 專屬沙龍（會員中心）
@app.route('/user')
def user():
    if 'username' in session:
        username = session['username']
        message = request.args.get('message', '')
        return render_template('user.html', name=username, message=message)
    return redirect(url_for('signin'))

# 路由：尊榮入會註冊頁面顯示
@app.route('/member/signup')
def signup():
    regform = RegistrationForm()
    return render_template('member/signup.html', form=regform)

# 路由：處理註冊資料提交 (對應 signup.html 的 action)
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
        
        # 密碼進行 MD5 加密
        md = hashlib.md5()
        md.update(userpass.encode('utf-8'))
        hashpass = md.hexdigest()

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 計算現有會員數產出 mid
        cursor.execute("SELECT COUNT(*) FROM member")
        count = cursor.fetchone()[0]
        mid = 'm' + str(count + 1).zfill(4)
        
        # 寫入會員資料表與帳號資料表
        SQL2 = "INSERT INTO member (mid, name, birthday, phone, address, email) VALUES (%s, %s, %s, %s, %s, %s);"
        cursor.execute(SQL2, (mid, name, birthday, phone, address, email))
        
        SQL3 = "INSERT INTO account (mid, username, userpass) VALUES (%s, %s, %s);"
        cursor.execute(SQL3, (mid, username, hashpass))
        
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('signin'))
        
    return render_template('member/signup.html', form=regform)

# 路由：離開試鞋間（登出）
@app.route('/member/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('signin'))

if __name__ == '__main__':
    app.run(debug=True)