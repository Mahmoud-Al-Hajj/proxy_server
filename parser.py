# parser.py - Parses raw HTTP requests into usable components


def parse_request(raw_request):
    """
    Parse the raw HTTP request and extract:
    - method (e.g. GET)
    - host   (e.g. example.com)
    - port   (e.g. 80)
    - path   (e.g. /index.html)
    """
    lines = raw_request.split('\r\n')
    request_line = lines[0]           # e.g. "GET http://example.com/ HTTP/1.1"
    parts = request_line.split(' ')   # ["GET", "http://example.com/", "HTTP/1.1"]
                                      #[  0 ,                  1   ,        2    ]
    if len(parts) < 3:
        raise ValueError(f"Malformed request line: {request_line}")

    method = parts[0].upper()
    url    = parts[1]
#-------------------------------------------------------------------------------
    # CONNECT method: request line is "CONNECT host:443 HTTP/1.1"
    if method == 'CONNECT':
        if ':' in url:
            host, port = url.split(':', 1)
            port = int(port)
        else:
            host = url
            port = 443
        return method, host, port, '/'
#-------------------------------------------------------------------------------
    if method != 'GET':
        raise ValueError(f"Unsupported method: {method}")

    # Remove "http://"
    if url.startswith('http://'):
        url = url[len('http://'):]

    # Split into host part and path
    if '/' in url:
        slash     = url.index('/')
        host_part = url[:slash]   # e.g. "example.com:8080"
        path      = url[slash:]   # e.g. "/index.html"
    else:
        host_part = url
        path      = '/'

    # Extract port if specified (e.g. "example.com:8080")
    if ':' in host_part:
        host, port = host_part.split(':', 1)
        port = int(port)
    else:
        host = host_part
        port = 80

    if not host:
        raise ValueError("Could not extract host from request")

    return method, host, port, path