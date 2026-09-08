from time import sleep
from threading import Event, Lock
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
        self.__client = mqtt.Client("mqtt5_client",protocol=mqtt.MQTTv5)
        self.__metrics_count = 0
        self.__response_chunks = []
        self.__response_dic = {}
        self.__code = -1
        self.__metrics_capture_lock = Lock()
        self.__metrics_capture_event = Event()
        self.__metrics_samples = []
        self.__metrics_capture_topic = None

    def __on_message(self, client, userdata, message):
        self.__response_dic = json.loads(message.payload)
        self.__response_chunks.append(self.__response_dic)
        if self.__lock.locked():
            self.__lock.release()
        try:
            self.__code = self.__response_dic['status']
        except:
            self.__code = -1

    def get_response_chunk(self):
        return self.__response_chunks.pop(0) if self.__response_chunks else None

    def __on_message_metrics(self, client, userdata, message):
        if not message.payload:
            return

        metrics_response = json.loads(message.payload)
        if self.__metrics_count < METRICS_TIMES:
            self.__metrics_count += 1
            logger = getattr(self, "logger", LOGGER)
            logger.info(f"{metrics_response}")
        else:
            self.__metrics_state = True
            self.__lock.release()

    def disconnect(self):
        self.__client.disconnect()

    def connect(self,broker_address,broker_port):
        try:
            self.__client.connect(broker_address, port=broker_port)
            self.__client.loop_start()
        except Exception as e:
            handle_connection_error(broker_address, broker_port, e)
    
    def request(self,device_id,operation,msg="{}"):
        # Send request and block until get the response or timeout
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
        properties=Properties(PacketTypes.PUBLISH)
        properties.ResponseTopic=response_topic
        self.__client.publish(topic,msg,properties=properties)
        if not (self.__lock.acquire(timeout = 90)):
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
        self.__metrics_state = False
        self.__metrics_count = 0
        response_topic = "dab/" + device_id+"/" + operation
        self.__client.subscribe(response_topic)
        self.__client.on_message = self.__on_message_metrics
        if not (self.__lock.acquire(timeout = 30)):
            self.__metrics_state = False

    def unsubscribe_metrics(self, device_id, operation):
        response_topic = "dab/" + device_id+"/" + operation
        self.__client.unsubscribe(response_topic)

    # These methods are deliberately separate from subscribe_metrics().  The
    # older method only answers "did any messages arrive?"; telemetry
    # conformance needs the actual MQTT payloads so their schema and values can
    # be checked.
    def begin_metrics_capture(self, device_id, operation):
        """Subscribe to one telemetry notification topic before issuing start.

        Returns the full MQTT topic.  Call wait_for_metrics_capture() after the
        start response, then end_metrics_capture() in a finally block.
        """
        topic = "dab/" + device_id + "/" + operation
        with self.__metrics_capture_lock:
            self.__metrics_samples = []
            self.__metrics_capture_event.clear()
            self.__metrics_capture_topic = topic

        def _on_metrics(_client, _userdata, message):
            try:
                payload = json.loads(message.payload.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                # Keep malformed payloads as evidence for the validator.
                payload = {"_invalidTelemetryPayload": message.payload.decode("utf-8", errors="replace")}
            with self.__metrics_capture_lock:
                self.__metrics_samples.append(payload)
                self.__metrics_capture_event.set()

        self.__client.message_callback_add(topic, _on_metrics)
        self.__client.subscribe(topic)
        return topic

    def wait_for_metrics_capture(self, minimum_messages=1, timeout=10):
        """Return up to the captured messages after waiting for the requested count."""
        deadline = __import__("time").monotonic() + timeout
        while True:
            with self.__metrics_capture_lock:
                samples = list(self.__metrics_samples)
            if len(samples) >= minimum_messages:
                return samples
            remaining = deadline - __import__("time").monotonic()
            if remaining <= 0:
                return samples
            self.__metrics_capture_event.wait(remaining)
            self.__metrics_capture_event.clear()

    def end_metrics_capture(self):
        """Remove the temporary telemetry callback and return all collected payloads."""
        with self.__metrics_capture_lock:
            topic = self.__metrics_capture_topic
            samples = list(self.__metrics_samples)
            self.__metrics_capture_topic = None
        if topic:
            try:
                self.__client.message_callback_remove(topic)
            except Exception:
                pass
            self.__client.unsubscribe(topic)
        return samples
    
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
    def discover_devices(self, attempts: int = 1, wait_seconds: float = 1.0):
        """
        Broadcasts to 'dab/discovery' and collects responses on a unique response topic.
        Compatible with callers that pass attempts + wait_seconds.
        Returns: [{"deviceId": "<id>", "ip": "<ip or None>"}]
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

        self.__client.message_callback_add(resp_topic, _on_disc)
        self.__client.subscribe(resp_topic)

        props = Properties(PacketTypes.PUBLISH)
        props.ResponseTopic = resp_topic
        payload = "{}"

        n = 1 if attempts is None else max(1, int(attempts))
        for _ in range(n):
            self.__client.publish("dab/discovery", payload, properties=props)
            sleep(max(0.2, float(wait_seconds)))

        try:
            self.__client.message_callback_remove(resp_topic)
        except:
            pass
        self.__client.unsubscribe(resp_topic)
        return list(found.values())
