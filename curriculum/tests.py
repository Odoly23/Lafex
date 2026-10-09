from django.test import TestCase

from users.models import User

from . import seed
from .models import Mission


class MissionManageTests(TestCase):
	def setUp(self):
		seed.run()
		self.staff = User.objects.create_user('s@x.com', is_staff=True)
		self.student = User.objects.create_user('e@x.com')
		self.mission = Mission.objects.get(slug='tourist-hotel')

	def data(self, **over):
		d = {'title_tet': 'Titulu foun', 'title_en': 'New title', 'goal_tet': 'Objetivu', 'goal_en': 'Goal',
             'ai_role': 'You are a receptionist.', 'rubric_text': 'First point\n\n  Second point  \n', 'max_turns': '8', 'active': 'on'}
		d.update(over)
		return d

	def test_seed_is_idempotent_and_has_special_missions(self):
		n = Mission.objects.count()
		seed.run()
		self.assertEqual(Mission.objects.count(), n)
		self.assertTrue(Mission.objects.get(slug='placement').is_placement)
		self.assertTrue(Mission.objects.get(slug='free-chat').is_free)

	def test_roles(self):
		url = f'/staff/misaun/{self.mission.pk}/'
		self.client.force_login(self.student)
		self.assertEqual(self.client.get(url).status_code, 403)
		self.assertEqual(self.client.get('/staff/materi/').status_code, 403)
		self.client.force_login(self.staff)
		self.assertEqual(self.client.get(url).status_code, 200)
		self.assertContains(self.client.get('/staff/materi/'), '/staff/kosakata/')

	def test_edit_saves_and_parses_rubric(self):
		self.client.force_login(self.staff)
		r = self.client.post(f'/staff/misaun/{self.mission.pk}/', self.data())
		self.assertEqual(r.status_code, 302)
		self.mission.refresh_from_db()
		self.assertEqual((self.mission.title_en, self.mission.max_turns), ('New title', 8))
		self.assertEqual(self.mission.rubric, ['First point', 'Second point'])
		self.assertEqual(self.mission.slug, 'tourist-hotel', 'kode misi tidak berubah')
		self.assertEqual(self.mission.band, 'intermediate')

	def test_validation(self):
		self.client.force_login(self.staff)
		for bad in ({'max_turns': '0'}, {'max_turns': '61'}, {'title_en': ''}, {'ai_role': ''}):
			r = self.client.post(f'/staff/misaun/{self.mission.pk}/', self.data(**bad))
			self.assertEqual(r.status_code, 200, bad)
		self.mission.refresh_from_db()
		self.assertNotEqual(self.mission.title_en, 'New title')

	def test_rubric_is_capped(self):
		self.client.force_login(self.staff)
		self.client.post(f'/staff/misaun/{self.mission.pk}/', self.data(rubric_text='\n'.join(f'p{i}' for i in range(30))))
		self.mission.refresh_from_db()
		self.assertEqual(len(self.mission.rubric), 10)

	def test_edited_mission_flows_into_ai_prompt(self):
		from tutor import ai
		from tutor.models import Session
		self.client.force_login(self.staff)
		self.client.post(f'/staff/misaun/{self.mission.pk}/', self.data(ai_role='You are a pirate hotel owner.'))
		s = Session.objects.create(user=self.student, mission=Mission.objects.get(pk=self.mission.pk), level_start='B1')
		self.assertIn('pirate hotel owner', ai._turn_system(s))
