import socket

from PIL import Image


class MicroVNC:
  def __init__(self, sock_file):
    self.vnc_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    self.vnc_sock.connect(sock_file)

    self.vnc_sock.recv(12)  # Protocol version
    self.vnc_sock.send(b'RFB 003.008\n')  # Protocol version

    num_auth_types = int.from_bytes(self.vnc_sock.recv(1))
    self.vnc_sock.recv(num_auth_types)
    self.vnc_sock.send(int.to_bytes(1))  # Auth type None
    auth_result = int.from_bytes(self.vnc_sock.recv(4))
    if auth_result != 0:
      raise RuntimeError("VNC Auth failed")

    self.vnc_sock.send(int.to_bytes(0))
    self.screen_width = int.from_bytes(self.vnc_sock.recv(2))
    self.screen_height = int.from_bytes(self.vnc_sock.recv(2))
    pixel_format = self.vnc_sock.recv(16)  # wayvnc is using rgba
    server_name_len = int.from_bytes(self.vnc_sock.recv(4))
    server_name = self.vnc_sock.recv(server_name_len).decode()
    print(f"Connected to: {server_name}")

    self.vnc_sock.send(b'\x02\x00\x00\x01\x00\x00\x00\x06')  # SetEncodings

  def get_screen(self):
    fb_update_request = b"".join([
      int.to_bytes(3),  # Message type
      bool.to_bytes(0),  # Incremental
      int.to_bytes(0, 2),  # X position
      int.to_bytes(0, 2),  # Y position
      int.to_bytes(self.screen_width, 2),  # Width
      int.to_bytes(self.screen_height, 2),  # Height
    ])
    self.vnc_sock.send(fb_update_request)

    message_type = int.from_bytes(self.vnc_sock.recv(1))
    if message_type != 0:
      raise RuntimeError("Unknown message type")
    self.vnc_sock.recv(1)  # Padding
    image = Image.new(mode="RGB", size=(self.screen_width, self.screen_height))
    number_of_rectangles = int.from_bytes(self.vnc_sock.recv(2))

    for rectangle in range(number_of_rectangles):
      r_x = int.from_bytes(self.vnc_sock.recv(2))
      r_y = int.from_bytes(self.vnc_sock.recv(2))
      r_width = int.from_bytes(self.vnc_sock.recv(2))
      r_height = int.from_bytes(self.vnc_sock.recv(2))
      r_encoding = int.from_bytes(self.vnc_sock.recv(4))

      if r_encoding != 0:
        raise RuntimeError("Unsupported encoding")

      r_pixels_size = r_width * r_height * 4
      r_pixels_received = 0
      r_pixels = bytearray(r_pixels_size)
      while r_pixels_received < r_pixels_size:
        r_pixels_received += self.vnc_sock.recv_into(memoryview(r_pixels)[r_pixels_received:])
      r_image = (Image.frombytes(mode="RGBA",
                                 size=(r_width, r_height),
                                 data=r_pixels,
                                 decoder_name="raw").convert("RGB"))
      image.paste(r_image, box=(r_x, r_y))

    return image

  def close(self):
    self.vnc_sock.close()
