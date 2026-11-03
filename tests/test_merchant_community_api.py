"""Regression checks for public intake and moderated community. No live credentials."""
import json, os, sqlite3, tempfile, unittest
from unittest.mock import patch
from admin_core import merchant_community as app

class CommunityChecks(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=os.path.join(self.tmp.name,'community.sqlite')
        con=sqlite3.connect(self.path)
        con.executescript("""
        CREATE TABLE merchant_applications (id INTEGER PRIMARY KEY,author_id TEXT,shop_name TEXT,contact_name TEXT,phone TEXT,email TEXT,category TEXT,shop_location TEXT,description TEXT,consent_at TEXT,status TEXT DEFAULT 'pending',created_at TEXT DEFAULT CURRENT_TIMESTAMP,reviewed_at TEXT);
        CREATE TABLE community_posts (id INTEGER PRIMARY KEY,author_id TEXT,author_label TEXT,category TEXT,title TEXT,body TEXT,status TEXT DEFAULT 'pending',created_at TEXT DEFAULT CURRENT_TIMESTAMP,reviewed_at TEXT);
        CREATE TABLE community_comments (id INTEGER PRIMARY KEY,post_id INTEGER,author_id TEXT,author_label TEXT,body TEXT,status TEXT DEFAULT 'pending',created_at TEXT DEFAULT CURRENT_TIMESTAMP,reviewed_at TEXT);
        CREATE TABLE audit_logs (id INTEGER PRIMARY KEY,actor_id INTEGER,action TEXT,target TEXT,target_id INTEGER,at TEXT);
        """);con.close()
        def db():
            c=sqlite3.connect(self.path)
            c.row_factory=sqlite3.Row
            return c
        self.patches=[patch.object(app,'use_postgres',return_value=True),patch.object(app,'connect',side_effect=db),patch.object(app,'member',return_value={'id':'test-user','label':'Tester'}),patch.object(app,'admin',return_value=1)]
        for p in self.patches:p.start()
    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.tmp.cleanup()
    def call(self,method,path,data=None):
        h={'host':'localhost:8000','origin':'http://localhost:8000','content-type':'application/json'}
        status,headers,body=app.handle(method,path,h,json.dumps(data).encode() if data is not None else b'')
        return status,json.loads(body)
    def test_applications_are_private_and_duplicate_rejected(self):
        info={'shopName':'테스트업체','contactName':'담당자','phone':'010-1234-5678','email':'test@example.com','category':'수산','location':'1F','description':'가락시장 입점 검수 신청을 드립니다.','consent':True}
        status,result=self.call('POST','/api/merchant-applications',info)
        self.assertEqual((status,result['status']),(201,'pending'))
        self.assertEqual(len(self.call('GET','/api/merchant-applications')[1]['items']),1)
        self.assertEqual(self.call('POST','/api/merchant-applications',info)[0],409)
    def test_posts_and_comments_require_moderation(self):
        p={'category':'story','title':'테스트 상인 이야기','content':'오랜 경험을 가진 상인의 소개입니다.'}
        status,result=self.call('POST','/api/community/posts',p)
        self.assertEqual(status,201)
        pid=result['id']
        self.assertEqual(self.call('GET','/api/community/posts')[1]['items'],[])
        self.assertEqual(self.call('POST','/api/community/comments',{'postId':pid,'content':'좋아요'})[0],404)
        self.assertEqual(self.call('POST','/api/community/moderation',{'kind':'posts','id':pid,'status':'approved'})[0],200)
        self.assertEqual(len(self.call('GET','/api/community/posts')[1]['items']),1)
        status,result=self.call('POST','/api/community/comments',{'postId':pid,'content':'좋아요'})
        self.assertEqual(status,201)
        self.assertEqual(self.call('GET','/api/community/comments?postId='+str(pid))[1]['items'],[])
        self.assertEqual(self.call('POST','/api/community/moderation',{'kind':'comments','id':result['id'],'status':'approved'})[0],200)
        self.assertEqual(len(self.call('GET','/api/community/comments?postId='+str(pid))[1]['items']),1)
    def test_wrong_origin_and_malformed_input(self):
        self.assertEqual(self.call('POST','/api/community/posts',{'category':'other'})[0],400)
        h={'host':'garakmall.lexid.site','origin':'https://another.example','content-type':'application/json'}
        self.assertEqual(app.handle('POST','/api/community/posts',h,b'{}')[0],403)
        self.assertEqual(self.call('GET','/api/community/comments?postId=abc')[0],400)
if __name__=='__main__':unittest.main()
