from pickle import FALSE
from flask import Flask, jsonify, request
from flasgger import Swagger, LazyString, LazyJSONEncoder
from flasgger import swag_from
import pandas as pd
import re
import sqlite3

app = Flask(__name__)

###############################################################################################################
app.json_encoder = LazyJSONEncoder
swagger_template = dict(
    info = {
        'title': LazyString(lambda:'API Documentation for Data Processing and Modeling'),
        'version': LazyString(lambda:'1.0.0'),
        'description': LazyString(lambda:'Dokumentasi API untuk Data Processing dan Modeling')
        }, host = LazyString(lambda: request.host)
    )
swagger_config = {
        "headers":[],
        "specs":[
            {
            "endpoint":'docs',
            "route":'/docs.json'
            }
        ],
        "static_url_path":"/flasgger_static",
        "swagger_ui":True,
        "specs_route":"/docs/"
    }
swagger = Swagger(app, template=swagger_template, config=swagger_config)

###############################################################################################################
db = sqlite3.connect('goldbinar.db', check_same_thread=False)
df = pd.read_sql_query('SELECT * FROM data', db)


df['id'] = range(0,len(df))
df['id'] = df['id'].astype('int')
df.index = df['id']

def lowercase(text):
    return text.lower() 

def remove_text(text):
    text = re.sub('\n',' ',text) # Remove every '\n'
    text = re.sub('rt',' ',text) # Remove every retweet symbol
    text = re.sub('user',' ',text) # Remove every username
    text = re.sub('((www\.[^\s]+)|(https?://[^\s]+)|(http?://[^\s]+))',' ',text) # Remove every URL
    text = re.sub('  +', ' ', text) # Remove extra spaces
    text = re.sub(r'pic.twitter.com.[\w]+', '', text) # Remove every pic 
    text = re.sub('gue','saya',text) # replace gue - saya
    text = re.sub(r':', '', text) #Remove symbol 
    text = re.sub(r'‚Ä¶', '', text) #Remove symbol Ä¶
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
    #df_get['New_Tweet'] = df_get['Tweet'].str.casefold()
    df_get['New_Tweet'] = df_get['Tweet'].apply(preprocess)
    json = df_get.to_dict(orient='index')

    del df_get

    return json

db.commit() 
db.close()
###############################################################################################################
# GET 'It works!'

@swag_from("docs/index.yml", methods=['GET'])
@app.route('/', methods=['GET'])
def test():
	return jsonify({'message' : 'It works!'})

###############################################################################################################

@swag_from("docs/index.yml", methods=['GET'])
@app.route('/tweet', methods=['GET'])
def returnAll():
    db = sqlite3.connect('goldbinar.db', check_same_thread=False)
    df = pd.read_sql_query('SELECT * FROM data', db)

    json = frame(df)

    db.commit() 
    db.close()
    return jsonify(json)
    
###############################################################################################################


@swag_from("docs/lang_post.yml", methods=['POST'])
@app.route('/tweet/input_teks', methods=['POST'])
def addOne():
    #buka koneksi
    db = sqlite3.connect('goldbinar.db', check_same_thread=False)
    
    New_Tweet = {'Tweet': request.json['Tweet']}
    df.loc[len(df) + 1]=[New_Tweet['Tweet'],max(df['id'])+1]
    df.index = df['id']
    pd_new_tweet = pd.DataFrame([New_Tweet])
    pd_new_tweet.to_sql('data', db, if_exists='append', index=False)
    df.append(pd_new_tweet)
    json=frame(df)
    id = max(df.index)
    json = json[id]
    
    #tutup koneksi
    db.commit() 
    db.close()
    return jsonify(json)
   

###############################################################################################################


@swag_from("docs/lang_upload.yml", methods=['POST'])
@app.route('/tweet/upload_file', methods=['POST'])
def addUpload():
    #buka koneksi
    db = sqlite3.connect('goldbinar.db', check_same_thread=False)
    df = pd.read_sql_query('SELECT * FROM data', db)

    file = request.files['file']
    df_upload = pd.read_csv(file, usecols=["Tweet"], encoding='iso-8859-1')
    df_upload1=pd.DataFrame(df_upload)
    print(df_upload1)
    df_upload1.to_sql('data', db, if_exists='append', index=False)
    df.append(df_upload1)

    json=frame(df)
    id = max(df.index)
    json = json[id]

    #file output cleansing
    df_get = df.copy()
    df_get['New_Tweet'] = df_get['Tweet'].apply(preprocess)
    df_get.to_csv('file cleansing.csv', index=False)

    #tutup koneksi
    db.commit()
    db.close() 
    return 'Berhasil'


###############################################################################################################
# Run Flask
if __name__ == "__main__":
    app.run(debug=True)