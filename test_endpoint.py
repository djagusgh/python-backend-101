import pytest
import bcrypt
import config
import json

from app import create_app
from sqlalchemy import create_engine, text

database = create_engine(config.test_config['DB_URL'], encoding='utf-8', max_overflow = 0)

@pytest.fixture
def api():
    app = create_app(config.test_config)
    app.config['TEST'] = True
    api = app.test_client()

    return api

def setup_function(): # 각 테스트가 실행되기 전에 자동으로 실행
    ## Create a test user
    hashed_password = bcrypt.hashpw(
        b"test password",
        bcrypt.gensalt()
    )
    new_users = [{
        'id' : 1,
        'name' : 'zzz',
        'email' : 'songew@gmail.com',
        'profile': 'test profile',
        'hashed_password' : hashed_password
    },{
        'id' : 2,
        'name' : 'yyy',
        'email' : 'test@naver.com',
        'profile' : 'test_profile2',
        'hashed_password' : hashed_password
    }]

    database.execute(text("""
    INSERT INTO users (
        id, name, email, profile, hashed_password) VALUES (
        :id, :name, :email, :profile, :hashed_password)"""), new_users)

    ## User 2의 트윗 미리 생성 해놓기
    database.execute(text("""
        INSERT INTO tweets (
            user_id,
            tweet
        ) VALUES (
            2,
            "Hello World!"
        )
    """))


def teardown_function(): # 각 테스트가 종료된 후 자동으로 실행 
    database.execute(text("SET FOREIGN_KEY_CHECKS=0"))
    database.execute(text("TRUNCATE users"))
    database.execute(text("TRUNCATE tweets"))
    database.execute(text("TRUNCATE users_follow_list"))
    database.execute(text("SET FOREIGN_KEY_CHECKS=1"))

def test_ping(api):
    resp = api.get('/ping')
    assert b'pong' in resp.data

def test_login(api):
    resp = api.post(
            '/login',
            data = json.dumps({'email' : 'songew@gmail.com', 'password' : 'test password'}),
            content_type = 'application/json'
            )
    assert b"access_token" in resp.data

def test_unauthorized(api):
    ## access token이 없이는 401 응답을 리턴하는지 확인!
    resp = api.post(
            '/tweet',
            data = json.dumps({'tweet' : "Hello World!"}),
            content_type = 'application/json'
    )
    assert resp.status_code == 401

    resp = api.post(
            '/follow',
            data = json.dumps({'id' : 1, 'follow' : 2}),
            content_type = 'application/json'
    )
    assert resp.status_code == 401
    
    resp = api.post(
            '/unfollow',
            data = json.dumps({'id' : 1, 'unfollow' : 2}),
            content_type = 'application/json'
    )
    assert resp.status_code == 401


def test_tweet(api):
    
    ## tweet endpoint에 http 요청하려면 access token이 필요함 
    ## -> /login endpoint를 먼저 호출해 access token을 읽어 들임     
    resp = api.post(
            '/login',
            data = json.dumps({'email' : 'songew@gmail.com', 'password' : 'test password'}),
            content_type = 'application/json'
            )

    resp_json = json.loads(resp.data.decode('utf-8'))
    access_token = resp_json['access_token']
    
    ## tweet
    resp = api.post(
            '/tweet',
            data = json.dumps({'tweet' : "Hello World!"}),
            content_type = 'application/json',
            headers = {'Authorization' : access_token}
            )

    assert resp.status_code == 200

    # tweet이 잘 만들어졌는지 확인하기 위해 timeline endpoint를 호출해서 response를 확인!
    resp = api.get(f'/timeline/1')
    
    tweets = json.loads(resp.data.decode('utf-8'))
    
    assert resp.status_code == 200
    
    assert tweets == {
            'user_id' : 1,
            'timeline' : [
                {
                    'user_id' : 1,
                    'tweet' : 'Hello World!'
                }
            ]
        }

def test_follow(api):
    # 로그인
    resp = api.post(
            '/login',
            data = json.dumps({'email' : 'songew@gmail.com', 'password' : 'test password'}),
            content_type = 'application/json'
            )
    resp_json = json.loads(resp.data.decode('utf-8'))
    access_token = resp_json['access_token']

    ## 먼저 사용자 1의 tweet 확인해서 tweet 리스트가 비어 있는 것을 확인
    resp = api.get(f'/timeline/1')
    tweets = json.loads(resp.data.decode('utf-8'))

    assert resp.status_code == 200
    assert tweets == {
        'user_id' : 1,
        'timeline' : [ ]
    }

    # follow 사용자 아이디 = 2
    resp = api.post(
        '/follow',
        data = json.dumps({'id' : 1, 'follow' : 2}),
        content_type = 'application/json',
        headers = {'Authorization' : access_token}
    )

    assert resp.status_code == 200
    
    ## 이제 사용자 1의 tweet 확인해서 사용자 2의 tweet이 리턴되는지 확인
    resp = api.get(f'/timeline/1')
    tweets = json.loads(resp.data.decode('utf-8'))

    assert resp.status_code == 200
    assert tweets  == {
        'user_id' : 1,
        'timeline' : [
            {
                'user_id' : 2,
                'tweet' : 'Hello World!'
            }
        ]
    }

def test_unfollow(api):
    ## 로그인
    resp = api.post(
            '/login',
            data = json.dumps({'email' : 'songew@gmail.com', 'password' : 'test password'}),
            content_type = 'application/json'
            )
    resp_json = json.loads(resp.data.decode('utf-8'))
    access_token = resp_json['access_token']
    

    ## follow 사용자 아이디 = 2
    resp = api.post(
            '/follow',
            data = json.dumps({'id' : 1, 'follow' : 2}),
            content_type = 'application/json',
            headers = {'Authorization' : access_token}
    )
    assert resp.status_code == 200
    
    ## 이제 사용자 1의 tweet 확인해서, 사용자 2의 tweet이 리턴되는 것을 확인
    resp = api.get(f'/timeline/1')
    tweets = json.loads(resp.data.decode('utf-8'))

    assert resp.status_code == 200
    assert tweets   == {
            'user_id' : 1,
            'timeline' : [
                {
                    'user_id' : 2,
                    'tweet' : 'Hello World!'
                }
            ]
        }
    
    ## unfollow 사용자 아이디 = 2
    resp = api.post(
            '/unfollow',
            data = json.dumps({'id' : 1, 'unfollow' : 2}),
            content_type = 'application/json',
            headers = {'Authorization' : access_token}
    )
    assert resp.status_code == 200
    
    ## 이제 사용자 1의 tweet 확인해서 유저 2의 tweet이 더 이상 리턴되지 않는 것을 확인
    resp = api.get(f'/timeline/1')
    tweets = json.loads(resp.data.decode('utf-8'))

    assert resp.status_code == 200
    assert tweets == {
            'user_id' : 1,
            'timeline' : [ ]
    }

    
    
