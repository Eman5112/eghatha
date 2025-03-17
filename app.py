import datetime
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "secret123"  # مفتاح سري لحماية الجلسات

# إعداد قاعدة البيانات
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///volunteers.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# مجلد حفظ الصور
UPLOAD_FOLDER = 'static/uploads/'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# بيانات تسجيل الدخول للمشرف
ADMIN_CREDENTIALS = {"admin": "1234"}

# نموذج المتطوعين
class Volunteer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    specialization = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False, unique=True)
    address = db.Column(db.String(200), nullable=False)
    photo = db.Column(db.String(200), nullable=False, default='default.jpg')
    available_time_start = db.Column(db.Time, nullable=False)
    available_time_end = db.Column(db.Time, nullable=False)

# نموذج الزائرين
class Visitor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False, unique=True)

# إنشاء قاعدة البيانات
with app.app_context():
    db.create_all()

### 🔹 توجيه المستخدم إلى تسجيل الدخول دائمًا عند فتح الموقع
@app.route('/')
def home():
    session.pop('visitor', None)  # إزالة الجلسة في كل مرة يدخل المستخدم الموقع
    return redirect(url_for('visitor_register'))  # إعادة توجيهه إلى صفحة تسجيل الدخول

### 🔹 تسجيل الزوار (إجبار التسجيل في كل مرة)
@app.route('/login', methods=['GET', 'POST'])
def visitor_register():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']

        # التحقق مما إذا كان رقم الهاتف موجودًا بالفعل
        existing_visitor = Visitor.query.filter_by(phone=phone).first()
        if not existing_visitor:
            new_visitor = Visitor(name=name, phone=phone)
            db.session.add(new_visitor)
            db.session.commit()
            flash("تم تسجيل الدخول بنجاح!", "success")

        return redirect(url_for('index'))  # توجيه المستخدم إلى الصفحة الرئيسية بعد التسجيل

    return render_template('login.html')

### 🔹 الصفحة الرئيسية بعد تسجيل الدخول
@app.route('/index')
def index():
    volunteer_count = Volunteer.query.count()
    visitor_count = Visitor.query.count()
    volunteers = Volunteer.query.all()
    return render_template('index.html', volunteers=volunteers, volunteer_count=volunteer_count, visitor_count=visitor_count)

### 🔹 تسجيل المتطوعين
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        specialization = request.form['specialization']
        phone = request.form['phone']
        address = request.form['address']
        photo = request.files.get('photo')

        filename = 'default.jpg'
        if photo and photo.filename != '':
            filename = secure_filename(photo.filename)
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            photo.save(photo_path)

        available_time_start = datetime.datetime.strptime(request.form['available_time_start'], '%H:%M').time()
        available_time_end = datetime.datetime.strptime(request.form['available_time_end'], '%H:%M').time()

        new_volunteer = Volunteer(
            name=name, specialization=specialization, address=address, phone=phone, photo=filename, 
            available_time_start=available_time_start, available_time_end=available_time_end
        )
        db.session.add(new_volunteer)
        db.session.commit()

        flash("تم تسجيل المتطوع بنجاح!", "success")
        return redirect(url_for('index'))

    return render_template('register.html')

### 🔹 عرض تفاصيل المتطوع
@app.route('/volunteer/<int:volunteer_id>')
def volunteer_details(volunteer_id):
    volunteer = Volunteer.query.get_or_404(volunteer_id)
    return render_template('volunteer_details.html', volunteer=volunteer)

### 🔹 تسجيل دخول المشرف
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username in ADMIN_CREDENTIALS and ADMIN_CREDENTIALS[username] == password:
            session['admin'] = username
            return redirect(url_for('dashboard'))
        else:
            flash("اسم المستخدم أو كلمة المرور غير صحيحة!", "danger")

    return render_template('admin.html')

### 🔹 لوحة تحكم المشرف
@app.route('/dashboard')
def dashboard():
    if 'admin' in session:
        volunteers = Volunteer.query.all()
        visitors = Visitor.query.all()
        return render_template('dashboard.html', volunteers=volunteers, visitors=visitors)

    return redirect(url_for('admin_login'))

### 🔹 تعديل بيانات المتطوع
@app.route('/edit/<int:volunteer_id>', methods=['GET', 'POST'])
def edit_volunteer(volunteer_id):
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    volunteer = Volunteer.query.get(volunteer_id)
    if request.method == 'POST':
        volunteer.name = request.form['name']
        volunteer.specialization = request.form['specialization']
        volunteer.phone = request.form['phone']
        db.session.commit()
        flash("تم تعديل بيانات المتطوع بنجاح!", "success")
        return redirect(url_for('dashboard'))

    return render_template('edit_volunteer.html', volunteer=volunteer)

### 🔹 حذف متطوع
@app.route('/delete/<int:volunteer_id>')
def delete_volunteer(volunteer_id):
    if 'admin' in session:
        volunteer = Volunteer.query.get(volunteer_id)
        if volunteer:
            db.session.delete(volunteer)
            db.session.commit()
            flash("تم حذف المتطوع بنجاح!", "success")
        return redirect(url_for('dashboard'))

    return redirect(url_for('admin_login'))

### تشغيل التطبيق
if __name__ == '__main__':
    app.run(debug=True ,host="0.0.0.0", port=8000)
