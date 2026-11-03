"""Security regression tests for the new Neon-backed merchant/community API.
No live DB or third-party credentials are used in CI.
"""
import unittest
from unittest.mock import patch
from admin_core import merchant_community as api

class MerchantCommunityTests(unittest.TestCase):
    def invoke(self,method,path,headers=None,body=b'{}'):
        with patch.object(api,'use_postgres',return_value=True):
            return api.handle(method,path,headers or {},body)
    def test_unauthorized_public_writes(self):
        for path in ('/api/merchant-applications','/api/community/posts','/api/community/comments'):
            with self.subTest(path=path):
                with patch.object(api,'member',side_effect=api.RequestError(401,'login required')):
                    status,_,body=self.invoke('POST',path,{'host':'garakmall.lexid.site','content-type':'application/json'})
                self.assertEqual(status,401)
    def test_moderator_access_denied_without_session(self):
        status,_,_=self.invoke('GET','/api/community/moderation')
        self.assertEqual(status,401)
    def test_cross_site_write_rejected(self):
        status,_,_=self.invoke('POST','/api/community/posts',
             {'host':'garakmall.lexid.site','origin':'https://attacker.invalid','content-type':'application/json'})
        self.assertEqual(status,403)
    def test_rejects_invalid_json_and_content_type(self):
        with patch.object(api,'member',return_value=('userid','테스터')):
            status,_,_=self.invoke('POST','/api/community/posts',{'content-type':'text/plain'},b'{}')
            self.assertEqual(status,415)
            status,_,_=self.invoke('POST','/api/community/posts',{'content-type':'application/json'},b'{')
            self.assertEqual(status,413)
    def test_user_supplied_fields_bound(self):
        with self.assertRaises(api.RequestError):
            api.field({'phone':'\x00hack'},'phone',40)
        with self.assertRaises(api.RequestError):
            api.field({'title':'x'*200},'title',120,3)
    def test_invalid_moderation_does_not_execute_sql(self):
        with self.assertRaises(api.RequestError):
            api.moderate({'kind':'users','status':'approved','id':10})
    def test_request_method_restricted(self):
        status,_,_=self.invoke('PATCH','/api/community/posts')
        self.assertEqual(status,405)
    def test_invalid_board_category_rejected(self):
        with self.assertRaises(api.RequestError):
            api.list_posts({'category':['../admin']},{})
    def test_raw_error_does_not_reveal_secrets(self):
        with patch.object(api,'member',side_effect=RuntimeError('postgres://password@neon.example')):
            status,_,payload=self.invoke('GET','/api/merchant-applications')
        self.assertEqual(status,500)
        self.assertNotIn(b'postgres://',payload)

if __name__=='__main__':
    unittest.main()
