# all constants

PROXY_HOST  = '0.0.0.0'
PROXY_PORT = 3128
BUFFER_SIZE = 4096


CACHE_TTL      = 300
CACHE_MAX_SIZE = 50

BLOCKED_HOSTS = [
    'ads.example.com',
    'malware.example.com',
    'facebook.com',
]
 
BLOCKED_IPS = [
    # '192.168.1.50',   # uncomment to block a specific client IP
]

LOG_FILE = 'proxy.log'
 