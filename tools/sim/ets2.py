#!/usr/bin/env python

import cv2
import os
import numpy
import time

from multiprocessing import Queue
from openpilot.tools.sim.bridge.common import SimulatorBridge
from openpilot.tools.sim.bridge.ets2.microvnc import MicroVNC
from openpilot.tools.sim.lib.common import SimulatorState, World, vec3, W, H


class Ets2World(World):
  WAYVNC_SOCKET = "/tmp/wayvnc.sock"

  def __init__(self, status_q):
    super().__init__(False)

    self.status_q = status_q

    try:
      print("Waiting for wayvnc socket")
      while not os.path.exists(self.WAYVNC_SOCKET):
        time.sleep(2)

      print("Connecting to wayvnc")
      self.vnc = MicroVNC(self.WAYVNC_SOCKET)

      self.status_q.put({"status": "started"})

    except Exception as e:
      self.close(str(e))

  def apply_controls(self, steer_sim, throttle_out, brake_out):
    pass

  def tick(self):
    pass

  def read_state(self):
    pass

  def read_sensors(self, simulator_state: SimulatorState):
    simulator_state.velocity = vec3(0, 0, 0)
    simulator_state.valid = True

  def read_cameras(self):
    image = self.vnc.get_screen()
    scaled_image = image.resize(size=(W, H))
    self.road_image = cv2.cvtColor(numpy.array(scaled_image), cv2.COLOR_RGB2BGR)
    self.image_lock.release()

  def close(self, reason: str):
    self.vnc.close()
    self.status_q.put({
      "status": "terminating",
      "reason": reason,
    })

  def reset(self):
    pass


class Ets2Bridge(SimulatorBridge):
  def __init__(self, world_status_q):
    self.world_status_q = world_status_q

    super().__init__(False, False)

  def spawn_world(self):
    return Ets2World(world_status_q)


if __name__ == "__main__":
  command_queue: Queue = Queue()
  world_status_q: Queue = Queue()
  simulator_bridge = Ets2Bridge(world_status_q)
  simulator_process = simulator_bridge.run(command_queue)

  while True:
    world_status = world_status_q.get()
    print(f"World Status: {str(world_status)}")
    if world_status["status"] == "terminating":
      break

  simulator_process.join()
