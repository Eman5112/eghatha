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


# نموذج المستشفيات
class Hospital(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    info = db.Column(db.Text, nullable=True)  # معلومات إضافية عن المستشفى
    photo = db.Column(db.String(200), nullable=True, default='hospital_default.jpg')

# نموذج الأدوية - محدث بدون حقل category
class medicine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    photo = db.Column(db.String(200), nullable=False, default='medicine_default.jpg')

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
    specialization = request.args.get('specialization', '').strip()
    volunteer_count = Volunteer.query.count()
    visitor_count = Visitor.query.count()
    hospital_count = Hospital.query.count()
    medicine_count = medicine.query.count()  # إضافة عدد الأدوية
    hospitals = Hospital.query.all()

    if specialization:
        volunteers = Volunteer.query.filter(Volunteer.specialization.contains(specialization)).all()
    else:
        volunteers = Volunteer.query.all()

    return render_template('index.html', volunteers=volunteers, volunteer_count=volunteer_count, 
                          visitor_count=visitor_count, hospitals=hospitals, hospital_count=hospital_count,
                          medicine_count=medicine_count)  # تمرير عدد الأدوية

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

### 🔹 تسجيل المستشفيات
@app.route('/add_hospital', methods=['GET', 'POST'])
def add_hospital():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
        
    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        phone = request.form['phone']
        info = request.form['info']
        photo = request.files.get('photo')

        filename = 'hospital_default.jpg'
        if photo and photo.filename != '':
            filename = secure_filename(photo.filename)
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            photo.save(photo_path)

        new_hospital = Hospital(
            name=name, address=address, phone=phone, info=info, photo=filename
        )
        db.session.add(new_hospital)
        db.session.commit()

        flash("تم إضافة المستشفى بنجاح!", "success")
        return redirect(url_for('dashboard'))

    return render_template('add_hospital.html')

### 🔹 عرض تفاصيل المستشفى
@app.route('/hospital/<int:hospital_id>')
def hospital_details(hospital_id):
    hospital = Hospital.query.get_or_404(hospital_id)
    return render_template('hospital_details.html', hospital=hospital)

### 🔹 تعديل بيانات المستشفى
@app.route('/edit_hospital/<int:hospital_id>', methods=['GET', 'POST'])
def edit_hospital(hospital_id):
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    hospital = Hospital.query.get_or_404(hospital_id)
    
    if request.method == 'POST':
        hospital.name = request.form['name']
        hospital.address = request.form['address']
        hospital.phone = request.form['phone']
        hospital.info = request.form['info']
        
        photo = request.files.get('photo')
        if photo and photo.filename != '':
            filename = secure_filename(photo.filename)
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            photo.save(photo_path)
            hospital.photo = filename
            
        db.session.commit()
        flash("تم تعديل بيانات المستشفى بنجاح!", "success")
        return redirect(url_for('dashboard'))

    return render_template('edit_hospital.html', hospital=hospital)

### 🔹 حذف مستشفى
@app.route('/delete_hospital/<int:hospital_id>')
def delete_hospital(hospital_id):
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
        
    hospital = Hospital.query.get_or_404(hospital_id)
    db.session.delete(hospital)
    db.session.commit()
    flash("تم حذف المستشفى بنجاح!", "success")
    return redirect(url_for('dashboard'))


# صفحة عرض جميع الأدوية
@app.route('/medicines')
def medicines():
    """صفحة عرض جميع الأدوية"""
    all_medicines = medicine.query.all()
    return render_template('medicines.html', medicines=all_medicines)

# إضافة الأدوية - محدث بدون حقل category
@app.route('/add_medicine', methods=['GET', 'POST'])
def add_medicine():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
        
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        photo = request.files.get('photo')

        # التحقق من وجود اسم الدواء
        if not name:
            flash("يجب إدخال اسم الدواء!", "danger")
            return render_template('add_medicine.html')

        filename = 'medicine_default.jpg'
        if photo and photo.filename != '':
            filename = secure_filename(photo.filename)
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            photo.save(photo_path)

        try:
            # إنشاء دواء جديد بدون حقل category
            new_medicine = medicine(
                name=name,  
                photo=filename
            )
            db.session.add(new_medicine)
            db.session.commit()
            flash("تم إضافة الدواء بنجاح!", "success")
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f"حدث خطأ: {str(e)}", "danger")
            return render_template('add_medicine.html')

    return render_template('add_medicine.html')

# حذف الأدوية
@app.route('/delete_medicine/<int:medicine_id>')
def delete_medicine(medicine_id):
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
        
    medicine = medicine.query.get_or_404(medicine_id)
    db.session.delete(medicine)
    db.session.commit()
    flash("تم حذف الدواء بنجاح!", "success")
    return redirect(url_for('dashboard'))

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
        hospitals = Hospital.query.all()
        medicines = medicine.query.all()  # إضافة الأدوية
        return render_template('dashboard.html', volunteers=volunteers, visitors=visitors, 
                             hospitals=hospitals, medicines=medicines)

    return redirect(url_for('admin_login'))

@app.route('/all-volunteers')
def all_volunteers():
    """Route to display all volunteers."""
    # Get all volunteers from the database
    all_volunteers = Volunteer.query.all()
    
    return render_template('all_volunteers.html', 
                          volunteers=all_volunteers,
                          page_title="كل المتطوعين")

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
