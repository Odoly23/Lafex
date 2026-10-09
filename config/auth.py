from rest_framework.authentication import SessionAuthentication


class SessionAuth401(SessionAuthentication):
	"""SessionAuthentication (CSRF tetap dicek untuk pengguna yang sudah masuk).
    Sengaja TANPA BasicAuthentication: akun siswa tidak punya kata sandi, dan Basic
    membuka jalur tebak kata sandi akun staff/admin."""

	def authenticate_header(self, request):
		return 'Session'  # tanpa ini DRF menjawab 403 (bukan 401) untuk pengguna yang belum masuk
