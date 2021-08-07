
from MySQLdb.cursors import Cursor
from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask_mysqldb import MySQL
from gevent.monkey import patch_ssl
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.hash import sha256_crypt
from functools import wraps #DECORATER modülümüzü dahil ettik...

#Kullanıcı giriş decoratoru...
#Kod tekrarını önlemiş oluyoruz sadace giriş yapıldıgında sistem kontrol panelini görüntüleyecek...
#https://flask.palletsprojects.com/en/2.0.x/patterns/viewdecorators/
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Kontrol paneline ulaşmak için lütfen giriş yapnız..","danger")
            return redirect(url_for("login"))

    return decorated_function


app = Flask(__name__) 
app.secret_key = "ybblog" #flask messageslerimizin çalışması için olusturuldu...

#Gerekli SQL sorgusu için modüller olusturulup gerekli configler aşağıda sağlanmıştır...
app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = "" 
app.config["MYSQL_DB"] = "ybblog"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app) #Kulandıgımız configleri mysql değişkenimize atadık


#Kullanıcı Kayıt Formu oluşturma...
class RegistorForm(Form):
    name = StringField("isim soyisim :", validators=[validators.length(min=4, max=25)])
    username = StringField("Kullanıcı Adı :", validators=[validators.length(min=5, max=35)])
    email = StringField("Email :", validators=[validators.email(message="Lütfen email adresini doğru bir şekilde giriniz.")])
    password = PasswordField("parola:",validators = [validators.DataRequired(message= "parola belirleyin"),validators.EqualTo(fieldname="confirm")])
    confirm = PasswordField("parolayı doğrulayın")

#Kayıt olma formun fonksiyon yapısı oluşturduk...
#https://flask.palletsprojects.com/en/1.1.x/patterns/wtforms/
@app.route("/register",methods = ["GET","POST"]) #Registerimiz reguest kısmının iki farklı şekilde tanımlamsı için get resquet ve post resquet kısımlarını fonksiyona tanıtmış olduk...
def register():
    form = RegistorForm(request.form) #formuzu oluşturduk...

    if request.method == "POST" and form.validate(): #burada form.validate methodumuz sistemde hata yoksa true olarak dönecek...
        
        #Kayıt işlemizi MYsql veritabanımıza aktarıyoruz...
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data) # parolamızı şifre haline getirmemizi yarayan bir modülü dahil ettik...
        
        #Burada yaptıgımız işlemler sql-server adında yaptığımız işlemlerle birebirdir...
        
        cursor = mysql.connection.cursor() #Sorgumuzu mySQL de yapmak için cursor oluşturrduk...
        sorgu = "INSERT INTO users(name,email,username,password) VALUES(%s,%s,%s,%s) "
        
        cursor.execute(sorgu,(name,email,username,password)) #Sorguyu çalıştırdık...
        mysql.connection.commit() #Veritabanında değişiklik yaptığımız için bu commit metıdunu kullanmak zorundayız...
        cursor.close()#Cursoru kapattık...
        
        flash("Kaydınız başarıyla alınmıştır.","success") #Oluşturdugumuz kayıt işleminin olup olmadıgını ekranda bir flask mesajı ile kullanıcıya aktarmıs olduk...
        return redirect(url_for("login")) #Gerekli butona basıldıgında yönlerileceğimiz url ye gitmek için kulandıgımız bir modül...
    else:
         return render_template("register.html", form = form)

#Kullanıcı Giriş Formu oluşturma...
class LoginForm(Form):
    username = StringField("Kullanıcı Adı")
    password = PasswordField("parola")

#Login kullanıcı girişi fonksiyon yapısı oluşturduk...
@app.route("/login",methods = ["GET","POST"])
def login():
    form = RegistorForm(request.form)
    
    
    if request.method == "POST":
        #Kayıt işlemizi MYsql veritabanımıza aktarıyoruz...
        username = form.username.data
        password_entered = form.password.data

        cursor = mysql.connection.cursor()
        sorgu = "SELECT * FROM users WHERE username = %s"

        #Şimdi result kısmımız sql-sorgumuzda ya vardır ya da yoktur bunun için iki farklı sart koymuş olacagız...
        result = cursor.execute(sorgu,(username,))
        
        if result > 0:
            data = cursor.fetchone() #sql veritabanımızdaki butun sütonları sözlük içine aktarmış olduk...
            real_password = data["password"] #sql-vertanımızın datasından password olanı değişkene atıyoruz...
            
            #sha256_crypt.verify ile girilen password ve veritanındaki passwordu karsılastırıyor..
            if sha256_crypt.verify(password_entered,real_password):
                flash("Başarıyla sisteme giriş yaptınız...","success")
                
                #Session modülü ile giriş ve çıkışları kontrol etmiş olduk...
                session["logged_in"] = True
                session["username"] = username

                return redirect(url_for("index"))
            else:
                flash("Parolanız yanlış..","danger")
                return redirect(url_for("login"))   
        else:
            flash("Böyle bir kullanıcı yoktur.","danger")
            return redirect(url_for("login"))
    
    return render_template("login.html", form = form)

#Detay sayfamızın fonksiyonu
@app.route("/article/<string:id>")
def article(id):
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles WHERE ıd = %s"

    result = cursor.execute(sorgu,(id,))

    if result > 0:
        article = cursor.fetchone()
        return render_template("article.html",article = article)
    else:
        return render_template("article.html")



#Kullanıcı çıkış fonsiyonu oluşturma...
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

#Konrol Paneli yönetimi fonksiyonu...
@app.route("/dashboard")
@login_required
def KonrolPaneli():
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles WHERE author = %s"

    result = cursor.execute(sorgu,(session["username"],))
    
    #Veritabanımızda gerekli bilgilerin olup olmadıgını sorguluyoruz...
    if result > 0:
        articles = cursor.fetchall()
        return render_template("dashboard.html", articles = articles)
    else:
        return render_template("dashboard.html")    


#Makale kayıt formu oluşturma...
class ArticleForm(Form):
    title = StringField("Makale bağlığı",validators=[validators.length(min=5)])
    content = TextAreaField("Makale İçeriği",validators=[validators.length(min=10)])

#Makale oluşturma fonksiyonu...
@app.route("/addarticle",methods = ["GET","POST"])
def addarticle():
    form = ArticleForm(request.form)

    if request.method == "POST" and form.validate():
        
        title = form.title.data
        #Bu content kısmızı CK-editör ile layoyt kısmına stripledik...
        content = form.content.data
        
        #SQL-server adı altında vertabına data base işlemleri girildi...
        cursor = mysql.connection.cursor()
        sorgu = "INSERT INTO articles(title,author,content) VALUES(%s,%s,%s) "
        cursor.execute(sorgu,(title,session["username"],content))
        mysql.connection.commit()
        cursor.close()

        flash("Makaleniz başarıyla kaydedilmiştir.","success") #Oluşturdugumuz kayıt işleminin olup olmadıgını ekranda bir flask mesajı ile kullanıcıya aktarmıs olduk...
        return redirect(url_for("KonrolPaneli"))
    
    return render_template("addarticle.html", form = form)

#Makale silme fonksiyonu...
@app.route("/delete/<string:id>")
@login_required #Giriş yapmadan yetki vermedik decorator fonk. ile...
def delete(id):
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles WHERE author=%s and ıd=%s"

    result = cursor.execute(sorgu,(session["username"],id))

    if result > 0:
        sorgu2 = "DELETE FROM articles WHERE ıd=%s"
        cursor.execute(sorgu2,(id,))
        mysql.connection.commit()
    
        return redirect(url_for("KonrolPaneli"))
    else:
        flash("Kendinize ait olmayan bir makaleyi silemessiniz.","danger")
        return redirect(url_for("index"))

#Makale güncelleme fonksiyonu...
@app.route("/edit/<string:id>",methods = ["GET","POST"])
@login_required
def update(id):

    #Makalenin mysql tarafında update.html ile tekrar düzenleme sayfasına getirildi...
    if request.method == "GET":

        cursor = mysql.connection.cursor()
        sorgu = "SELECT * FROM articles WHERE ıd=%s and author=%s"

        result = cursor.execute(sorgu,(id,session["username"]))

        if result == 0:
            flash("Böyle bir makale bulunmuyor veya buna yetkinz bulunmamaktadır.","danger")
            return redirect(url_for("index"))
        else:
            article = cursor.fetchone()
            form = ArticleForm()

            form.title.data = article["title"]
            form.content.data = article["content"]
            return render_template("update.html",form = form)
    
    #Makalenin post kısmı yani butona basıldıgında gerekli şlemlerin kaydedilme işlemi yapıldı...
    else:
        form = ArticleForm(request.form)
        newtitle = form.title.data
        newcontent = form.content.data

        sorgu2 = "UPDATE articles SET title=%s,content=%s WHERE ıd=%s"

        cursor = mysql.connection.cursor()

        cursor.execute(sorgu2,(newtitle,newcontent,id))
        mysql.connection.commit()

        flash("Makale başarıyla güncellendi.","success")
        return redirect(url_for("index"))

#Makale arama işlemi yapmak...
@app.route("/search", methods= ["GET","POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword")

        cursor = mysql.connection.cursor()
        sorgu = "SELECT * FROM articles where title like '%" + keyword + "%'"

        result = cursor.execute(sorgu)

        if result == 0:
            flash("Arana başlığa karsılık makale bulunmamaktadır.","danger")
            return redirect(url_for("articles"))
        else:
            articles = cursor.fetchall()

            return render_template("articles.html",articles = articles)    

#Veritabanındaki Makalelerin Başlıklarını görüntülemek...
@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles"

    result = cursor.execute(sorgu)
    #Veritabanımızda gerekli makalelerin olup olmadıgını sorguluyoruz...
    if result > 0:
        articles = cursor.fetchall()
        return render_template("articles.html", articles = articles)
    else:
        return render_template("articles.html")

#İlk ana sayfa fonksiyonu...
@app.route("/")
def index():
    return render_template("index.html") #HTML uzantılarımızı kodumuza aktarmamızı saglıyor...

#Hakkımda kısmının olustuğu fonsiyon...
@app.route("/abaut")
def about():
    return render_template("about.html")


    
 
if __name__ == "__main__":
    app.run(debug = True) #Hata oldugunda sistemin URL'sinde omu gösteriyor...
    


    
    
    

        
        

        





