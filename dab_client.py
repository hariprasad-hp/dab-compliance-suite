from time import sleep
from threading import Lock
from paho.mqtt.properties import Properties
from paho.mqtt.packettypes import PacketTypes 
import paho.mqtt.client as mqtt
import json
import uuid
from logger import LOGGER 
from util.argument_validator import handle_connection_error

METRICS_TIMES = 5

class DabClient:
    def __init__(self):
        self.__lock = Lock()
        self.__lock.acquire()
        self.__client = mqtt.Client(f"mqtt5_client_{uuid.uuid4().hex[:8]}", protocol=mqtt.MQTTv5)
        self.__broker_address = None
        self.__broker_port = 1883
        self.__metrics_count = 0
        self.__metrics_state = False
        self.__response_chunks = []
        self.__response_dic = {}
        self.__code = -1

    def __on_message(self, client, userdata, message):
        """Buffer incoming DAB response chunks; hold request lock until remainingChunks reaches 0."""
        self.__response_dic = json.loads(message.payload)
        self.__response_chunks.append(self.__response_dic)
        raw_status = self.__response_dic.get('status') if isinstance(self.__response_dic, dict) else None
        if isinstance(raw_status, int) and not isinstance(raw_status, bool):
            self.__code = raw_status
        else:
            self.__code = -2
        release_now = True
        if isinstance(self.__response_dic, dict) and self.__code == 200:
            rem = self.__response_dic.get("remainingChunks")
            if isinstance(rem, int) and not isinstance(rem, bool) and rem > 0:
                release_now = False
        if release_now and self.__lock.locked():
            self.__lock.release()

    def get_response_chunk(self):
        return self.__response_chunks.pop(0) if self.__response_chunks else None

    def __on_message_metrics(self, client, userdata, message):
        """Count incoming telemetry samples and safely release the wait lock once threshold is met."""
        if not message.payload:
            return

        try:
            metrics_response = json.loads(message.payload)
        except Exception:
            return
        if self.__metrics_count < METRICS_TIMES:
            self.__metrics_count += 1
            logger = getattr(self, "logger", LOGGER)
            logger.info(f"{metrics_response}")
        else:
            self.__metrics_state = True
            if self.__lock.locked():
                self.__lock.release()

    def disconnect(self):
        try:
            self.__client.loop_stop()
        except Exception:
            pass
        try:
            self.__client.disconnect()
        except Exception:
            pass

    def _is_loop_alive(self) -> bool:
        t = getattr(self.__client, "_thread", None)
        return bool(t and t.is_alive())

    def _wait_connected(self, timeout_sec: float = 2.0) -> bool:
        waited = 0.0
        while waited < timeout_sec:
            if self.__client.is_connected() and self._is_loop_alive():
                return True
            sleep(0.02)
            waited += 0.02
        return bool(self.__client.is_connected() and self._is_loop_alive())

    def ensure_connected(self):
        """Ensure an active MQTTv5 connection and live reader thread, recreating both if crashed."""
        if self._wait_connected(0.2):
            return
        if not self.__broker_address:
            return
        try:
            if self._is_loop_alive():
                self.__client.reconnect()
                if self._wait_connected(2.0):
                    return
        except Exception:
            pass
        try:
            self.disconnect()
            self.__client = mqtt.Client(f"mqtt5_client_{uuid.uuid4().hex[:8]}", protocol=mqtt.MQTTv5)
            self.__client.connect(self.__broker_address, port=self.__broker_port)
            self.__client.loop_start()
            self._wait_connected(2.5)
        except Exception:
            pass

    def connect(self,broker_address,broker_port):
        """Connect to the MQTTv5 broker, start the background loop, and wait for CONNACK."""
        self.__broker_address = broker_address
        self.__broker_port = broker_port
        try:
            self.__client.connect(broker_address, port=broker_port)
            self.__client.loop_start()
            self._wait_connected(2.5)
        except Exception as e:
            handle_connection_error(broker_address, broker_port, e)
    
    def request(self,device_id,operation,msg="{}",timeout=135):
        # Send request and block until get the response or timeout
        self.ensure_connected()
        topic = "dab/" + device_id+"/" + operation
        response_topic = f"dab/_response/{uuid.uuid4().hex}"
        self.__response_chunks.clear()
        self.__response_dic = {}
        self.__code = -1

        if not self.__lock.locked():
            self.__lock.acquire()

        def _on_response(client, userdata, message):
            self.__on_message(client, userdata, message)

        self.__client.message_callback_add(response_topic, _on_response)
        self.__client.subscribe(response_topic)
        sleep(0.02)
        properties=Properties(PacketTypes.PUBLISH)
        properties.ResponseTopic=response_topic
        self.__client.publish(topic,msg,properties=properties)
        if not (self.__lock.acquire(timeout = timeout)):
            self.__code = 100
        try:
            self.__client.message_callback_remove(response_topic)
        except:
            pass
        self.__client.unsubscribe(response_topic)
        
    def response(self):
        if((self.__code != -1) and (self.__code != 100)):
            return json.dumps(self.__response_dic, indent=2)
        else:
            return ""

    def subscribe_metrics(self, device_id, operation):
        """Subscribe to a telemetry topic using a topic-scoped callback and wait for samples."""
        self.ensure_connected()
        self.__metrics_state = False
        self.__metrics_count = 0
        if not self.__lock.locked():
            self.__lock.acquire()
        response_topic = "dab/" + device_id+"/" + operation
        self.__client.message_callback_add(response_topic, self.__on_message_metrics)
        self.__client.subscribe(response_topic)
        sleep(0.02)
        if not (self.__lock.acquire(timeout = 30)):
            self.__metrics_state = False

    def unsubscribe_metrics(self, device_id, operation):
        response_topic = "dab/" + device_id+"/" + operation
        try:
            self.__client.message_callback_remove(response_topic)
        except Exception:
            pass
        try:
            self.__client.unsubscribe(response_topic)
        except Exception:
            pass
    
    def last_metrics_state(self):
        return self.__metrics_state

    def last_error_code(self):
        return self.__code
    
    def last_error_msg(self):
        logger = getattr(self, "logger", LOGGER)
        if (self.__code == -1):
            logger.warn("Unknown error")
        elif (self.__code == 100):
            logger.warn("Timeout")
        elif (self.__code == 400):
            logger.warn("Request invalid or malformed")
        elif (self.__code == 500):
            logger.error("Internal error")
        elif (self.__code == 501):
            logger.warn("Not implemented")

    # ---- Minimal discovery compatible with callers passing attempts + wait_seconds ----
    def discover_devices(self, attempts: int = 4, wait_seconds: float = 2.5, target_device_id: str = None):
        """
        Broadcast 'dab/discovery' and collect responses on a unique response topic.
        When target_device_id is given, keep listening across shared-broker replies until
        that device responds (or attempts expire) instead of exiting on the first device.
        """
        resp_topic = f"dab/_response/discovery/{uuid.uuid4().hex}"
        found = {}

        def _on_disc(_c, _u, msg):
            try:
                d = json.loads(msg.payload.decode("utf-8"))
                dev = d.get("deviceId") or d.get("device_id")
                ip  = d.get("ip") or d.get("ipAddress")
                if dev and dev not in found:
                    found[dev] = {"deviceId": dev, "ip": ip}
                elif dev and ip and not found[dev].get("ip"):
                    found[dev]["ip"] = ip
            except:
                pass

        props = Properties(PacketTypes.PUBLISH)
        props.ResponseTopic = resp_topic
        payload = "{}"

        n = 4 if attempts is None else max(1, int(attempts))
        per_attempt = max(0.2, float(wait_seconds))
        for attempt_idx in range(n):
            self.ensure_connected()
            self.__client.message_callback_add(resp_topic, _on_disc)
            self.__client.subscribe(resp_topic)
            sleep(0.05)
            self.__client.publish("dab/discovery", payload, properties=props)
            waited = 0.0
            while waited < per_attempt:
                sleep(0.1)
                waited += 0.1
                if target_device_id and target_device_id in found:
                    sleep(0.05)
                    break
                if not target_device_id and found and attempt_idx > 0:
                    sleep(0.05)
                    break
            try:
                self.__client.message_callback_remove(resp_topic)
                self.__client.unsubscribe(resp_topic)
            except Exception:
                pass
            if (target_device_id and target_device_id in found) or (not target_device_id and found):
                break
            if attempt_idx + 1 < n:
                sleep(1.0)
        return list(found.values())
