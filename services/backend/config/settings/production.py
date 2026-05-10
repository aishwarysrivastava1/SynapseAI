from .base import *
import os

DEBUG = False

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[
    "sanchaalansaathi.onrender.com",
    ".railway.app",           # covers all *.railway.app subdomains
    "localhost",
    "127.0.0.1",
])

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=False)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
