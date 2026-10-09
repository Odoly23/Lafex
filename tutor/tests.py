import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest import mock

from django.test import TestCase, override_settings
from django.utils import timezone

from users.models import User
from billing import services as billing
from billing.models import UsageDay
from curriculum import seed
from curriculum.models import Mission

from . import ai
from .views.api import MAX_TEXT
from .models import Session, Turn


def post(client, url, data=None):
	return client.post(url, data or {}, content_type='application/json')


@override_settings(LAFEX_OFFLINE=True)
class TutorFlowTests(TestCase):
	def setUp(self):
		seed.run()
		self.user = User.objects.create_user('a@x.com')
		self.client.force_login(self.user)

	def start(self, slug='tourist-airport', client=None):
		return post(client or self.client, '/api/sessions/', {'mission': slug})

	def test_requires_login(self):
		self.client.logout()
		self.assertEqual(self.start().status_code, 401)

	def test_start_turn_finish(self):
		r = self.start()
		self.assertEqual(r.status_code, 200)
		sid = r.json()['session_id']
		self.assertTrue(r.json()['turn']['reply'])
		t = post(self.client, f'/api/sessions/{sid}/turn/', {'text': 'My name is Maria'}).json()
		self.assertTrue(t['turn']['reply'])
		self.assertEqual(t['student_turns'], 1)
		f = post(self.client, f'/api/sessions/{sid}/finish/').json()
		self.assertTrue(0 <= f['score'] <= 100)
		s = Session.objects.get(pk=sid)
		self.assertIsNotNone(s.finished_at)
		self.assertEqual([x.role for x in s.turns.all()], ['assistant', 'user', 'assistant'])

	def test_finish_is_idempotent(self):
		sid = self.start().json()['session_id']
		post(self.client, f'/api/sessions/{sid}/turn/', {'text': 'Hello there my friend'})
		a = post(self.client, f'/api/sessions/{sid}/finish/').json()
		first_finish = Session.objects.get(pk=sid).finished_at
		b = post(self.client, f'/api/sessions/{sid}/finish/').json()
		self.assertEqual(a['summary'], b['summary'])
		self.assertEqual(Session.objects.get(pk=sid).finished_at, first_finish)

	def test_cannot_finish_without_speaking(self):
		sid = self.start().json()['session_id']
		self.assertEqual(post(self.client, f'/api/sessions/{sid}/finish/').status_code, 400)

	def test_turn_after_finish_and_empty_text_rejected(self):
		sid = self.start().json()['session_id']
		self.assertEqual(post(self.client, f'/api/sessions/{sid}/turn/', {'text': '   '}).status_code, 400)
		post(self.client, f'/api/sessions/{sid}/turn/', {'text': 'Hello there my friend'})
		post(self.client, f'/api/sessions/{sid}/finish/')
		self.assertEqual(post(self.client, f'/api/sessions/{sid}/turn/', {'text': 'more'}).status_code, 409)

	def test_mission_turn_cap(self):
		Mission.objects.filter(slug='tourist-airport').update(max_turns=1)
		sid = self.start().json()['session_id']
		r = post(self.client, f'/api/sessions/{sid}/turn/', {'text': 'Hello there my friend'}).json()
		self.assertTrue(r['done'])
		self.assertEqual(post(self.client, f'/api/sessions/{sid}/turn/', {'text': 'again'}).json()['error'], 'mission_full')

	def test_other_users_cannot_touch_my_session(self):
		sid = self.start().json()['session_id']
		other = User.objects.create_user('b@x.com')
		self.client.force_login(other)
		for path in (f'/api/sessions/{sid}/turn/', f'/api/sessions/{sid}/finish/'):
			self.assertEqual(post(self.client, path, {'text': 'hi'}).status_code, 404)

	def test_unknown_or_inactive_mission(self):
		self.assertEqual(self.start('nope').status_code, 404)
		Mission.objects.filter(slug='tourist-hotel').update(active=False)
		self.assertEqual(self.start('tourist-hotel').status_code, 404)

	def test_text_is_truncated_and_unicode_roundtrips(self):
		sid = self.start().json()['session_id']
		text = '안녕하세요 Hau nia naran Maria. ' + 'x' * 2000
		post(self.client, f'/api/sessions/{sid}/turn/', {'text': text})
		saved = Turn.objects.get(session_id=sid, role='user').text
		self.assertEqual(len(saved), MAX_TEXT)
		self.assertTrue(saved.startswith('안녕하세요 Hau nia naran Maria.'))

	def test_placement_sets_level(self):
		sid = self.start('placement').json()['session_id']
		post(self.client, f'/api/sessions/{sid}/turn/', {'text': 'My name is Maria and I live in Dili'})
		with mock.patch.object(ai, 'summarize', return_value=ai.clean_summary({'score': 80, 'level': 'B1'}, 'A1')):
			r = post(self.client, f'/api/sessions/{sid}/finish/').json()
		self.assertEqual(r['level'], 'B1')
		self.user.refresh_from_db()
		self.assertEqual((self.user.level, self.user.placement_done), ('B1', True))

	def test_regular_mission_promotes_one_level_at_most(self):
		sid = self.start().json()['session_id']
		post(self.client, f'/api/sessions/{sid}/turn/', {'text': 'Hello there my friend'})
		with mock.patch.object(ai, 'summarize', return_value=ai.clean_summary({'score': 95, 'level': 'C2'}, 'A1')):
			post(self.client, f'/api/sessions/{sid}/finish/')
		self.user.refresh_from_db()
		self.assertEqual(self.user.level, 'A2')

	def test_low_score_never_demotes_or_promotes(self):
		self.user.level = 'B1'; self.user.save()
		sid = self.start('tourist-hotel').json()['session_id']
		post(self.client, f'/api/sessions/{sid}/turn/', {'text': 'Hello there my friend'})
		with mock.patch.object(ai, 'summarize', return_value=ai.clean_summary({'score': 30, 'level': 'A1'}, 'B1')):
			post(self.client, f'/api/sessions/{sid}/finish/')
		self.user.refresh_from_db()
		self.assertEqual(self.user.level, 'B1')


@override_settings(LAFEX_OFFLINE=True, FREE_TURNS_PER_DAY=2, PAID_TURNS_PER_DAY=3)
class QuotaTests(TestCase):
	def setUp(self):
		seed.run()
		self.user = User.objects.create_user('a@x.com')
		self.client.force_login(self.user)

	def test_free_quota_then_no_access_then_daily_limit(self):
		sid = post(self.client, '/api/sessions/', {'mission': 'tourist-airport'}).json()['session_id']  # giliran 1
		post(self.client, f'/api/sessions/{sid}/turn/', {'text': 'Hello there my friend'})              # giliran 2
		r = post(self.client, f'/api/sessions/{sid}/turn/', {'text': 'Another sentence here'})
		self.assertEqual((r.status_code, r.json()['error']), (402, 'no_access'))
		billing.redeem(self.user, billing.create_vouchers('1d', 1)[0])
		self.assertEqual(post(self.client, f'/api/sessions/{sid}/turn/', {'text': 'Another sentence here'}).status_code, 200)
		r = post(self.client, f'/api/sessions/{sid}/turn/', {'text': 'One more sentence now'})
		self.assertEqual((r.status_code, r.json()['error']), (402, 'daily_limit'))

	def test_ai_failure_refunds_turn_and_removes_empty_session(self):
		with mock.patch.object(ai, 'next_turn', side_effect=ai.TutorError('boom')):
			r = post(self.client, '/api/sessions/', {'mission': 'tourist-airport'})
		self.assertEqual((r.status_code, r.json()['error']), (502, 'tutor_failed'))
		self.assertEqual(billing.turns_left(self.user), 2)
		self.assertEqual(Session.objects.count(), 0)

	def test_failed_turn_is_refunded_and_not_saved(self):
		sid = post(self.client, '/api/sessions/', {'mission': 'tourist-airport'}).json()['session_id']
		left = billing.turns_left(self.user)
		with mock.patch.object(ai, 'next_turn', side_effect=ai.TutorRefused()):
			r = post(self.client, f'/api/sessions/{sid}/turn/', {'text': 'Hello there my friend'})
		self.assertEqual((r.status_code, r.json()['error']), (502, 'refused'))
		self.assertEqual(billing.turns_left(self.user), left)
		self.assertEqual(Turn.objects.filter(session_id=sid, role='user').count(), 0)


@override_settings(LAFEX_OFFLINE=True)
class ReviewTests(TestCase):
	def setUp(self):
		seed.run()
		self.user = User.objects.create_user('a@x.com')
		self.client.force_login(self.user)

	def finished(self, slug):
		sid = post(self.client, '/api/sessions/', {'mission': slug}).json()['session_id']
		post(self.client, f'/api/sessions/{sid}/turn/', {'text': 'Hello there my friend'})
		post(self.client, f'/api/sessions/{sid}/finish/')
		return sid

	def test_locked_without_active_plan(self):
		self.assertEqual(self.client.get('/api/review/').status_code, 402)

	def test_lists_only_finished_non_placement_sessions_of_me(self):
		billing.redeem(self.user, billing.create_vouchers('7d', 1)[0])
		done = self.finished('tourist-airport')
		self.finished('placement')
		post(self.client, '/api/sessions/', {'mission': 'tourist-hotel'})  # tidak selesai
		stranger = User.objects.create_user('b@x.com')
		s = Session.objects.create(user=stranger, mission=Mission.objects.get(slug='tourist-hotel'),
                                   level_start='A1', finished_at=timezone.now(), score=50)
		r = self.client.get('/api/review/').json()
		self.assertEqual([x['id'] for x in r['sessions']], [done])
		self.assertNotIn(s.id, [x['id'] for x in r['sessions']])
		self.assertEqual(r['sessions'][0]['turns'][0]['role'], 'assistant')
		self.assertIn('expires_at', r)

	def test_plan_expiry_locks_review(self):
		from billing.models import Entitlement
		billing.redeem(self.user, billing.create_vouchers('1d', 1)[0])
		self.finished('tourist-airport')
		Entitlement.objects.update(expires_at=timezone.now() - timezone.timedelta(seconds=1))
		self.assertEqual(self.client.get('/api/review/').status_code, 402)


class _FakeAnthropic(BaseHTTPRequestHandler):
	seen = []
	reply = {}
	stop_reason = 'end_turn'

	def do_POST(self):
		body = json.loads(self.rfile.read(int(self.headers['content-length'])))
		type(self).seen.append(body)
		is_summary = 'score' in body['output_config']['format']['schema']['properties']
		payload = type(self).reply['summary' if is_summary else 'turn']
		out = {'id': 'msg_1', 'type': 'message', 'role': 'assistant', 'model': body['model'],
               'stop_reason': type(self).stop_reason, 'stop_sequence': None,
               'content': [{'type': 'text', 'text': json.dumps(payload)}],
               'usage': {'input_tokens': 1, 'output_tokens': 1}}
		data = json.dumps(out).encode()
		self.send_response(200)
		self.send_header('content-type', 'application/json')
		self.send_header('content-length', str(len(data)))
		self.end_headers()
		self.wfile.write(data)

	def log_message(self, *a):
		pass


@override_settings(LAFEX_OFFLINE=False)  # jalur AI harus diuji meski lingkungan memaksa mode offline
class ClaudePathTests(TestCase):
	"""Jalur AI diuji terhadap server Anthropic palsu: bentuk permintaan dan pembacaan balasan."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.server = HTTPServer(('127.0.0.1', 0), _FakeAnthropic)
		threading.Thread(target=cls.server.serve_forever, daemon=True).start()
		cls.env = mock.patch.dict(os.environ, {
            'ANTHROPIC_BASE_URL': f'http://127.0.0.1:{cls.server.server_port}', 'ANTHROPIC_API_KEY': 'test'})
		cls.env.start()

	@classmethod
	def tearDownClass(cls):
		cls.env.stop()
		cls.server.shutdown()
		super().tearDownClass()

	def setUp(self):
		seed.run()
		_FakeAnthropic.seen = []
		_FakeAnthropic.stop_reason = 'end_turn'
		_FakeAnthropic.reply = {
            'turn': {'reply': 'Welcome to Dili! What is your name?', 'correction': 'I am a student.',
                     'explanation': 'Uza "a" molok "student".', 'goal_met': False},
            'summary': {'score': 140, 'level': 'ZZ', 'headline': 'Di\'ak!', 'tips': ['Prátika.'],
                        'vocab': [{'word': 'luggage', 'meaning_tet': 'mala'}],
                        'corrections': [{'said': 'I student', 'better': 'I am a student', 'why_tet': 'Presiza "am".'}]},
        }
		self.user = User.objects.create_user('a@x.com')
		self.client.force_login(self.user)

	def test_ai_mode_is_on(self):
		self.assertTrue(ai.mode().startswith('ai:'))

	def test_request_shape_and_flow(self):
		r = post(self.client, '/api/sessions/', {'mission': 'tourist-hotel'}).json()
		first = _FakeAnthropic.seen[0]
		self.assertEqual(first['model'], 'claude-opus-5-5')
		self.assertEqual(first['messages'], [{'role': 'user', 'content': ai.OPENING}])
		self.assertIn('hotel receptionist', first['system'])
		self.assertIn('Tetun', first['system'])
		fmt = first['output_config']['format']
		self.assertEqual(fmt['type'], 'json_schema')
		self.assertFalse(fmt['schema']['additionalProperties'])

		post(self.client, f"/api/sessions/{r['session_id']}/turn/", {'text': 'I student'})
		msgs = _FakeAnthropic.seen[1]['messages']
		self.assertEqual([m['role'] for m in msgs], ['user', 'assistant', 'user'])  # mulai dengan user, selang-seling
		self.assertEqual(msgs[-1]['content'], 'I student')
		turn = Turn.objects.get(session_id=r['session_id'], role='user')
		self.assertEqual(turn.correction, 'I am a student.')

	def test_summary_is_sanitised(self):
		sid = post(self.client, '/api/sessions/', {'mission': 'tourist-hotel'}).json()['session_id']
		post(self.client, f'/api/sessions/{sid}/turn/', {'text': 'I student'})
		f = post(self.client, f'/api/sessions/{sid}/finish/').json()
		self.assertEqual(f['score'], 100, 'nilai dibatasi 0-100')
		self.assertEqual(f['summary']['level'], 'A1', 'level tak dikenal diganti level awal')
		self.assertEqual(f['summary']['vocab'][0]['word'], 'luggage')

	def test_refusal_is_handled(self):
		_FakeAnthropic.stop_reason = 'refusal'
		r = post(self.client, '/api/sessions/', {'mission': 'tourist-hotel'})
		self.assertEqual((r.status_code, r.json()['error']), (502, 'refused'))
		self.assertEqual(billing.turns_left(self.user), 5)

	def test_placement_prompt_forbids_teaching(self):
		post(self.client, '/api/sessions/', {'mission': 'placement'})
		self.assertIn('Jangan mengajar', _FakeAnthropic.seen[0]['system'])
