from flask import Flask, jsonify, request
from flasgger import Swagger, LazyString, LazyJSONEncoder
from flasgger import swag_from
import pandas as pd
import re
import sqlite3

app = Flask(__name__)

#######################################################################################################
# Konfigurasi Swagger
app.json_encoder = LazyJSONEncoder
swagger_template = {
    "info": {
        "title": "API Documentation for Data Processing and Modeling",
        "version": "1.0.0",
        "description": "Dokumentasi API untuk Data Processing dan Modeling"
    },
    "host": "127.0.0.1:5000"  # Gantilah dengan host yang sesuai
}
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'docs',
            "route": '/docs.json'
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/docs/"
}
swagger = Swagger(app, template=swagger_template, config=swagger_config)
#######################################################################################################

# Koneksi Database
db = sqlite3.connect('goldbinar.db', check_same_thread=False)
df = pd.read_sql_query('SELECT * FROM data', db)

# Fungsi Preprocessing
def lowercase(text):
    return text.lower()

def remove_text(text):
    text = re.sub('\n', ' ', text)
    text = re.sub('rt', ' ', text)
    text = re.sub('user', ' ', text)
    text = re.sub('((www\.[^\s]+)|(https?://[^\s]+)|(http?://[^\s]+))', ' ', text)
    text = re.sub('  +', ' ', text)
    text = re.sub(r'pic.twitter.com.[\w]+', '', text)
    text = re.sub('gue', 'saya', text)
    text = re.sub(r':', '', text)
    text = re.sub(r'‚Ä¶', '', text)
    return text

def remove_nonaplhanumeric(text):
    text = re.sub('[^0-9a-zA-Z]+', ' ', text)
    return text

def preprocess(text):
    text = lowercase(text)
    text = remove_text(text)
    text = remove_nonaplhanumeric(text)
    return text

def frame(df):
    df_get = df.copy()
    df_get['New_Tweet'] = df_get['Tweet'].apply(preprocess)
    json = df_get.to_dict(orient='index')
    del df_get
    return json
#############################################################################################################


# Rute Test
@swag_from("docs/index.yml", methods=['GET'])
@app.route('/', methods=['GET'])
def test():
    return jsonify({'message': 'HI, THIS IS APP CLEANSING'})

# Rute Mengambil Semua Data
@swag_from("docs/index.yml", methods=['GET'])
@app.route('/tweet', methods=['GET'])
def returnAll():
    db = sqlite3.connect('goldbinar.db', check_same_thread=False)
    df = pd.read_sql_query('SELECT * FROM data', db)
    json = frame(df)
    db.commit()
    db.close()
    return jsonify(json)

# Rute Menambahkan Data Teks
@swag_from("docs/lang_post.yml", methods=['POST'])
@app.route('/tweet/input_teks', methods=['POST'])
def addOne():
    try:
        db = sqlite3.connect('goldbinar.db', check_same_thread=False)
        # Mendapatkan data teks dari permintaan JSON
        tweet_data = request.json.get('Tweet')
        # Memastikan data teks tidak kosong
        if not tweet_data:
            return jsonify({'message': 'Tweet cannot be empty'}), 400
        # Memproses data teks
        processed_tweet = preprocess(tweet_data)
        # Menambahkan data baru ke database
        cursor = db.cursor()
        cursor.execute("INSERT INTO data (Tweet) VALUES (?)", (processed_tweet,))
        db.commit()
        # Mendapatkan ID dari data yang baru saja dimasukkan
        cursor.execute("SELECT last_insert_rowid()")
        new_id = cursor.fetchone()[0]
        # Menyiapkan respons JSON
        response_data = {'id': new_id, 'Tweet': processed_tweet}
        return jsonify(response_data), 201  # 201 Created
    except Exception as e:
        return jsonify({'error': str(e)}), 500  # 500 Internal Server Error
    finally:
        db.close()

# Rute Mengunggah Data Teks dari File
@swag_from("docs/lang_upload.yml", methods=['POST'])
@app.route('/tweet/upload_file', methods=['POST'])
def addUpload():
    db = sqlite3.connect('goldbinar.db', check_same_thread=False)
    df = pd.read_sql_query('SELECT * FROM data', db)
    file = request.files['file']
    df_upload = pd.read_csv(file, encoding='utf-8-sig')
    df_upload1 = pd.DataFrame(df_upload)
    df.to_sql('data', db, if_exists='append', index=False)
    df = pd.concat([df, df_upload1], ignore_index=True)  # Menggabungkan DataFrame baru
    json = frame(df)
    id = max(df.index)
    json = json[id]
    df_get = df.copy()
    df_get['New_Tweet'] = df_get['Tweet'].apply(preprocess)
    df_get.to_csv('file_cleansing.csv', index=False)
    db.commit()
    db.close()
    return 'Berhasil'

# Menjalankan Aplikasi
if __name__ == "__main__":
    app.run(debug=True)
