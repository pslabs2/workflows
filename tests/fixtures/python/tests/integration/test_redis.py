import socket


def test_redis_ping() -> None:
    with socket.create_connection(("localhost", 6379), timeout=5) as conn:
        conn.sendall(b"PING\r\n")
        assert conn.recv(16) == b"+PONG\r\n"
