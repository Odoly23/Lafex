import json


def json_body(request):
	"""Isi permintaan JSON sebagai dict; {} bila kosong atau rusak."""
	try:
		data = json.loads(request.body or b'{}')
	except ValueError:
		return {}
	return data if isinstance(data, dict) else {}
