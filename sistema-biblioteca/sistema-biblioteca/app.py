from flask import Flask, render_template, request, redirect, url_for, flash, session, g
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import date, timedelta
import sqlite3, os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'biblioteca.db')
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'troque-esta-chave-em-producao')


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')
    return g.db

@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute('PRAGMA foreign_keys = ON')
    db.executescript('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        registration TEXT UNIQUE NOT NULL,
        email TEXT,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'reader',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        isbn TEXT,
        category TEXT,
        year INTEGER,
        copies INTEGER NOT NULL DEFAULT 1 CHECK(copies >= 0),
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS loans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id),
        book_id INTEGER NOT NULL REFERENCES books(id),
        loan_date TEXT NOT NULL,
        due_date TEXT NOT NULL,
        return_date TEXT,
        fine REAL NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'active'
    );
    ''')
    existing = db.execute('SELECT id FROM users WHERE registration = ?', ('admin',)).fetchone()
    if not existing:
        db.execute('INSERT INTO users(name, registration, email, password_hash, role) VALUES(?,?,?,?,?)',
                   ('Administrador', 'admin', 'admin@biblioteca.local', generate_password_hash('admin123'), 'admin'))
    db.commit(); db.close()

init_db()


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            flash('Entre na sua conta para continuar.', 'warning')
            return redirect(url_for('login'))
        return fn(*args, **kwargs)
    return wrapper


def admin_required(fn):
    @wraps(fn)
    @login_required
    def wrapper(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Esta função é exclusiva do bibliotecário/administrador.', 'danger')
            return redirect(url_for('dashboard'))
        return fn(*args, **kwargs)
    return wrapper

@app.context_processor
def inject_globals():
    return {'today': date.today().isoformat()}

@app.route('/')
def index():
    if session.get('user_id'):
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        registration = request.form.get('registration', '').strip()
        password = request.form.get('password', '')
        user = get_db().execute('SELECT * FROM users WHERE registration = ?', (registration,)).fetchone()
        if user and check_password_hash(user['password_hash'], password):
            session.clear()
            session.update(user_id=user['id'], name=user['name'], role=user['role'], registration=user['registration'])
            return redirect(url_for('dashboard'))
        flash('Matrícula/usuário ou senha incorretos.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear(); flash('Você saiu do sistema.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    stats = {
        'books': db.execute('SELECT COUNT(*) FROM books').fetchone()[0],
        'users': db.execute("SELECT COUNT(*) FROM users WHERE role='reader'").fetchone()[0],
        'active': db.execute("SELECT COUNT(*) FROM loans WHERE status='active'").fetchone()[0],
        'overdue': db.execute("SELECT COUNT(*) FROM loans WHERE status='active' AND due_date < ?", (date.today().isoformat(),)).fetchone()[0],
    }
    recent = db.execute('''SELECT loans.*, users.name AS user_name, books.title AS book_title
                           FROM loans JOIN users ON users.id=loans.user_id JOIN books ON books.id=loans.book_id
                           ORDER BY loans.id DESC LIMIT 8''').fetchall()
    return render_template('dashboard.html', stats=stats, recent=recent)

@app.route('/books')
@login_required
def books():
    q = request.args.get('q', '').strip()
    db = get_db()
    rows = db.execute('''SELECT books.*, books.copies - (SELECT COUNT(*) FROM loans WHERE loans.book_id=books.id AND status='active') AS available
                         FROM books WHERE title LIKE ? OR author LIKE ? OR COALESCE(isbn,'') LIKE ? OR COALESCE(category,'') LIKE ?
                         ORDER BY title''', (f'%{q}%',)*4).fetchall()
    return render_template('books.html', books=rows, q=q)

@app.route('/books/new', methods=['GET', 'POST'])
@admin_required
def book_new():
    if request.method == 'POST':
        title = request.form.get('title','').strip(); author = request.form.get('author','').strip()
        if not title or not author:
            flash('Título e autor são obrigatórios.', 'danger')
        else:
            get_db().execute('INSERT INTO books(title,author,isbn,category,year,copies) VALUES(?,?,?,?,?,?)',
                (title, author, request.form.get('isbn','').strip(), request.form.get('category','').strip(),
                 int(request.form['year']) if request.form.get('year','').isdigit() else None,
                 max(1, int(request.form.get('copies',1) or 1))))
            get_db().commit(); flash('Livro cadastrado com sucesso.', 'success'); return redirect(url_for('books'))
    return render_template('book_form.html', book=None)

@app.route('/books/<int:book_id>/edit', methods=['GET','POST'])
@admin_required
def book_edit(book_id):
    db=get_db(); book=db.execute('SELECT * FROM books WHERE id=?',(book_id,)).fetchone()
    if not book: flash('Livro não encontrado.','danger'); return redirect(url_for('books'))
    if request.method=='POST':
        title=request.form.get('title','').strip(); author=request.form.get('author','').strip()
        copies=max(1,int(request.form.get('copies',1) or 1))
        active=db.execute("SELECT COUNT(*) FROM loans WHERE book_id=? AND status='active'",(book_id,)).fetchone()[0]
        if copies < active: flash(f'Não é possível definir {copies} exemplar(es): existem {active} empréstimo(s) ativo(s).','danger')
        elif not title or not author: flash('Título e autor são obrigatórios.','danger')
        else:
            db.execute('UPDATE books SET title=?,author=?,isbn=?,category=?,year=?,copies=? WHERE id=?',
                (title,author,request.form.get('isbn','').strip(),request.form.get('category','').strip(),int(request.form['year']) if request.form.get('year','').isdigit() else None,copies,book_id))
            db.commit(); flash('Livro atualizado.','success'); return redirect(url_for('books'))
    return render_template('book_form.html', book=book)

@app.route('/books/<int:book_id>/delete', methods=['POST'])
@admin_required
def book_delete(book_id):
    db=get_db(); count=db.execute('SELECT COUNT(*) FROM loans WHERE book_id=?',(book_id,)).fetchone()[0]
    if count: flash('Este livro possui histórico de empréstimos e não pode ser excluído.','danger')
    else: db.execute('DELETE FROM books WHERE id=?',(book_id,)); db.commit(); flash('Livro excluído.','success')
    return redirect(url_for('books'))

@app.route('/users')
@admin_required
def users():
    rows=get_db().execute('SELECT id,name,registration,email,role,created_at FROM users ORDER BY name').fetchall()
    return render_template('users.html', users=rows)

@app.route('/users/new', methods=['GET','POST'])
@admin_required
def user_new():
    if request.method=='POST':
        name=request.form.get('name','').strip(); reg=request.form.get('registration','').strip(); password=request.form.get('password','')
        if not name or not reg or len(password)<6: flash('Informe nome, matrícula e senha com pelo menos 6 caracteres.','danger')
        else:
            try:
                get_db().execute('INSERT INTO users(name,registration,email,password_hash,role) VALUES(?,?,?,?,?)',
                    (name,reg,request.form.get('email','').strip(),generate_password_hash(password),request.form.get('role','reader') if request.form.get('role') in ('reader','admin') else 'reader'))
                get_db().commit(); flash('Usuário cadastrado.','success'); return redirect(url_for('users'))
            except sqlite3.IntegrityError: flash('Essa matrícula já está cadastrada.','danger')
    return render_template('user_form.html')

@app.route('/loans')
@login_required
def loans():
    db=get_db()
    if session.get('role')=='admin':
        rows=db.execute('''SELECT loans.*,users.name user_name,users.registration,books.title book_title FROM loans JOIN users ON users.id=loans.user_id JOIN books ON books.id=loans.book_id ORDER BY CASE status WHEN 'active' THEN 0 ELSE 1 END, due_date''').fetchall()
    else:
        rows=db.execute('''SELECT loans.*,users.name user_name,users.registration,books.title book_title FROM loans JOIN users ON users.id=loans.user_id JOIN books ON books.id=loans.book_id WHERE user_id=? ORDER BY id DESC''',(session['user_id'],)).fetchall()
    return render_template('loans.html', loans=rows)

@app.route('/loans/new', methods=['GET','POST'])
@admin_required
def loan_new():
    db=get_db()
    if request.method=='POST':
        user_id=request.form.get('user_id',type=int); book_id=request.form.get('book_id',type=int)
        user=db.execute("SELECT * FROM users WHERE id=? AND role='reader'",(user_id,)).fetchone()
        book=db.execute('SELECT * FROM books WHERE id=?',(book_id,)).fetchone()
        active=db.execute("SELECT COUNT(*) FROM loans WHERE book_id=? AND status='active'",(book_id,)).fetchone()[0] if book else 0
        active_user=db.execute("SELECT COUNT(*) FROM loans WHERE user_id=? AND status='active'",(user_id,)).fetchone()[0] if user else 0
        if not user or not book: flash('Selecione um usuário e um livro válidos.','danger')
        elif book['copies']-active < 1: flash('Não há exemplares disponíveis deste livro.','danger')
        elif active_user >= 3: flash('Este usuário já possui 3 empréstimos ativos (limite do sistema).','danger')
        else:
            loan_date=date.today(); due=loan_date+timedelta(days=14)
            db.execute('INSERT INTO loans(user_id,book_id,loan_date,due_date) VALUES(?,?,?,?)',(user_id,book_id,loan_date.isoformat(),due.isoformat()))
            db.commit(); flash(f'Empréstimo registrado. Devolução prevista: {due.strftime("%d/%m/%Y")}.','success'); return redirect(url_for('loans'))
    user_rows=db.execute("SELECT id,name,registration FROM users WHERE role='reader' ORDER BY name").fetchall()
    book_rows=db.execute('''SELECT books.id,books.title,books.author,books.copies-(SELECT COUNT(*) FROM loans WHERE loans.book_id=books.id AND status='active') available FROM books ORDER BY title''').fetchall()
    return render_template('loan_form.html', users=user_rows, books=book_rows)

@app.route('/loans/<int:loan_id>/return', methods=['POST'])
@admin_required
def loan_return(loan_id):
    db=get_db(); loan=db.execute('SELECT * FROM loans WHERE id=?',(loan_id,)).fetchone()
    if not loan: flash('Empréstimo não encontrado.','danger')
    elif loan['status']!='active': flash('Este empréstimo já foi devolvido.','warning')
    else:
        today=date.today(); due=date.fromisoformat(loan['due_date']); late=max(0,(today-due).days); fine=late*1.0
        db.execute("UPDATE loans SET status='returned',return_date=?,fine=? WHERE id=?",(today.isoformat(),fine,loan_id)); db.commit()
        flash(f'Devolução registrada. Multa: R$ {fine:.2f} ({late} dia(s) de atraso).','success')
    return redirect(url_for('loans'))

@app.route('/reports')
@admin_required
def reports():
    db=get_db()
    summary=db.execute('''SELECT COUNT(*) total, SUM(CASE WHEN status='active' THEN 1 ELSE 0 END) active, SUM(CASE WHEN status='returned' THEN 1 ELSE 0 END) returned, SUM(fine) fines FROM loans''').fetchone()
    overdue_rows=db.execute('''SELECT loans.*,users.name user_name,books.title book_title FROM loans JOIN users ON users.id=loans.user_id JOIN books ON books.id=loans.book_id WHERE status='active' AND due_date < ? ORDER BY due_date''',(date.today().isoformat(),)).fetchall()
    overdue=[dict(row) | {'days_late': (date.today()-date.fromisoformat(row['due_date'])).days} for row in overdue_rows]
    popular=db.execute('''SELECT books.title,COUNT(loans.id) total FROM books LEFT JOIN loans ON loans.book_id=books.id GROUP BY books.id ORDER BY total DESC,books.title LIMIT 5''').fetchall()
    return render_template('reports.html', summary=summary, overdue=overdue, popular=popular)

if __name__ == '__main__':
    app.run(debug=True)
