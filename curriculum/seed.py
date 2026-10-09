"""Data awal kurikulum. Idempoten: aman dijalankan berulang (`manage.py seed_curriculum`).

CATATAN: teks Tetun (title_tet, goal_tet) ditulis sebaik mungkin dan WAJIB ditinjau penutur asli.
"""

SCENARIOS = [
    {'slug': 'tourist', 'title_tet': 'Turista', 'title_en': 'Tourist', 'emoji': '🧳', 'order': 1},
]

MISSIONS = [
    # ---- Placement (tanpa skenario) ----
    {
        'slug': 'placement', 'scenario': None, 'band': 'beginner', 'order': 0, 'is_placement': True, 'max_turns': 6,
        'title_tet': 'Teste nível', 'title_en': 'Level check',
        'goal_tet': 'Hatán pergunta balun atu hatene ita nia nível Inglés.',
        'goal_en': 'Answer a few friendly questions so the tutor can estimate the speaker\'s English level.',
        'ai_role': (
            'You are Lafaek, a warm language examiner. Hold a relaxed 5-question conversation to estimate the '
            'student\'s CEFR level. Start with a very easy question (name, where they live). Make each next '
            'question slightly harder (daily routine, past event, opinion, hypothetical situation) depending on '
            'how well they answered. Do not teach during the check; just ask the next question.'),
        'rubric': ['Grammar range', 'Vocabulary range', 'Fluency and length of answers', 'Understanding of questions'],
    },
    # ---- Tourist ----
    {
        'slug': 'tourist-airport', 'scenario': 'tourist', 'band': 'beginner', 'order': 1, 'max_turns': 10,
        'title_tet': 'Mai iha aeroportu', 'title_en': 'Arriving at the airport',
        'goal_tet': 'Hatete ita nia naran, ita mai husi ne\'ebé, no ita sei hela ba loron hira.',
        'goal_en': 'Greet the driver, say your name, say where you are from, and say how long you will stay.',
        'ai_role': (
            'You are a friendly taxi driver at the airport in Dili, Timor-Leste. The student is a tourist who just '
            'arrived. Welcome them, ask their name, where they are from, how long they will stay, and where they '
            'want to go. Use very simple English.'),
        'rubric': ['Greets politely', 'Gives name and country', 'States length of stay', 'Names a destination'],
    },
    {
        'slug': 'tourist-directions', 'scenario': 'tourist', 'band': 'beginner', 'order': 2, 'max_turns': 10,
        'title_tet': 'Husu dalan', 'title_en': 'Asking for directions',
        'goal_tet': 'Husu dalan ba merkadu ka hotél no komprende resposta.',
        'goal_en': 'Ask how to get to the market or a hotel and understand the directions you are given.',
        'ai_role': (
            'You are a helpful local person walking in Dili. A tourist stops you to ask for directions. Give short '
            'directions with simple words (turn left, turn right, straight, near, next to). Check that the tourist '
            'understood by asking them to repeat the directions.'),
        'rubric': ['Asks politely for directions', 'Understands left/right/straight', 'Repeats the directions back'],
    },
    {
        'slug': 'tourist-hotel', 'scenario': 'tourist', 'band': 'intermediate', 'order': 1, 'max_turns': 12,
        'title_tet': 'Rezerva kuartu iha otél', 'title_en': 'Booking a hotel room',
        'goal_tet': 'Rezerva kuartu ba kalan rua, husu folin, matabixu, no wifi.',
        'goal_en': 'Book a room for two nights and ask about the price, breakfast, and wifi.',
        'ai_role': (
            'You are a hotel receptionist in Dili. A guest wants a room. Ask for dates and number of guests, offer '
            'two room types with different prices, and answer questions about breakfast and wifi. Be polite and '
            'professional, and ask the guest to confirm the booking.'),
        'rubric': ['States dates and length of stay', 'Asks about price', 'Asks about breakfast or wifi', 'Confirms the booking'],
    },
    {
        'slug': 'tourist-restaurant', 'scenario': 'tourist', 'band': 'intermediate', 'order': 2, 'max_turns': 12,
        'title_tet': 'Han iha restaurante', 'title_en': 'Ordering at a restaurant',
        'goal_tet': 'Hili hahán, husu ingredientes, no hadi\'a pedidu sala.',
        'goal_en': 'Order a meal, ask what is in a dish, and politely fix a wrong order.',
        'ai_role': (
            'You are a waiter at a restaurant in Dili. Take the customer\'s order and describe dishes when asked. '
            'Midway, deliberately bring the wrong dish (for example fish instead of chicken) so the customer must '
            'politely complain and ask for the right one.'),
        'rubric': ['Orders food politely', 'Asks about ingredients', 'Complains politely about the mistake', 'Thanks the waiter'],
    },
    {
        'slug': 'tourist-lost-luggage', 'scenario': 'tourist', 'band': 'advanced', 'order': 1, 'max_turns': 14,
        'title_tet': 'Mala lakon iha aeroportu', 'title_en': 'Reporting lost luggage',
        'goal_tet': 'Relata mala lakon ho detallu no husu kompensasaun ho edukasaun.',
        'goal_en': 'Report lost luggage in detail and politely negotiate compensation and delivery.',
        'ai_role': (
            'You are an airline customer service agent at the airport. A passenger reports that their suitcase did '
            'not arrive. Ask for flight details, a description of the suitcase and its contents. Be formal and '
            'slightly bureaucratic; offer a small compensation first and let the passenger negotiate for more and '
            'for delivery to their hotel. Use natural, fairly advanced English.'),
        'rubric': ['Describes the problem clearly and in detail', 'Uses formal polite language', 'Negotiates with reasons', 'Agrees on next steps'],
    },
    {
        'slug': 'tourist-tour-deal', 'scenario': 'tourist', 'band': 'advanced', 'order': 2, 'max_turns': 14,
        'title_tet': 'Negosia viajen turístiku', 'title_en': 'Negotiating a private tour',
        'goal_tet': 'Negosia folin, roteiru, no polítika kansela ba viajen privadu.',
        'goal_en': 'Negotiate the price, itinerary, and cancellation policy of a private multi-day tour.',
        'ai_role': (
            'You are an experienced tour operator in Timor-Leste selling a 3-day private tour (Dili, Atauro, '
            'Mount Ramelau). Quote a high starting price, defend it with reasons, and give ground only when the '
            'customer argues well. Mention cancellation terms and ask follow-up questions. Speak natural, fluent English.'),
        'rubric': ['Negotiates price with arguments', 'Discusses itinerary details', 'Asks about cancellation policy', 'Uses hedging and polite persuasion'],
    },
]


def run():
	from .models import Mission, Scenario

	scenarios = {}
	for s in SCENARIOS:
		obj, _ = Scenario.objects.update_or_create(slug=s['slug'], defaults={k: v for k, v in s.items() if k != 'slug'})
		scenarios[s['slug']] = obj
	for m in MISSIONS:
		data = {k: v for k, v in m.items() if k not in ('slug', 'scenario')}
		data['scenario'] = scenarios.get(m['scenario'])
		Mission.objects.update_or_create(slug=m['slug'], defaults=data)
	return len(SCENARIOS), len(MISSIONS)
