from flask import Flask, render_template, request, redirect, url_for, session, flash
import dbconn  # 確保你的資料庫連線模組跟 app.py 在同一層

app = Flask(__name__)
app.secret_key = 'zhen_luxury_secret_key_for_session'  # 啟用 session 必備的密鑰

# --- 1. 首頁路由 ---
@app.route('/')
def index():
    user_name = session.get('user_name')
    return render_template('index.html', user_name=user_name)

# --- 2. 會員尊榮登入路由 (使用 mid 與 phone) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # 從前端 HTML 表單中接收用戶輸入的 mid 與 phone
        mid = request.form.get('mid')
        phone = request.form.get('phone')
        
        # 撰寫 SQL 語法：向 member 資料表查詢符合 mid 與 phone 的會員
        sql = "SELECT * FROM member WHERE mid = %s AND phone = %s"
        
        try:
            # 呼叫你的 dbconn 執行查詢
            user = dbconn.select_one(sql, (mid, phone))
            
            if user:
                # 登入成功：將會員資訊寫入 Session
                # 💡 註：如果你的資料庫回傳是字典格式，用 user['mid']；如果是元組(Tuple)格式，請改成 user[0]
                session['user_id'] = user['mid'] if isinstance(user, dict) else user[0]
                session['user_name'] = user['name'] if isinstance(user, dict) else user[1]
                
                flash('尊榮會員登入成功！歡迎光臨 ZHEN 奢華高訂鞋履', 'success')
                return redirect(url_for('index'))
            else:
                # 查無此會員或手機不符
                flash('會員編號或手機號碼錯誤，請重新確認', 'danger')
                
        except Exception as e:
            print(f"資料庫查詢發生錯誤: {e}")
            flash('系統連線異常，請稍後再試', 'danger')
            
    # 🎯 修正重點：因為你的檔案在 templates/member/signin.html
    return render_template('member/signin.html')

# --- 3. 登出路由 ---
@app.route('/logout')
def logout():
    session.clear()
    flash('您已成功安全登出尊榮會員系統', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)