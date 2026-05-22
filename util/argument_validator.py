# util/argument_validator.py
import sys
import socket
from logger import LOGGER

def validate_broker(broker_val):
    """
    Validates the broker address parameter.
    Rejects:
      - Empty values
      - URLs containing protocol schemes (e.g., mqtt://, mqtts://)
      - Host with port (e.g., host:port, [ipv6]:port)
      - Slashes or URL paths
    """
    if not broker_val or not broker_val.strip():
        LOGGER.fatal("MQTT Broker argument validation failed:")
        LOGGER.fatal(f"  Invalid value: {repr(broker_val)}")
        LOGGER.fatal("  Mistake: The MQTT broker address cannot be empty.")
        LOGGER.fatal("  Correct command: python3 main.py -b <host/IP> -I <device-id>")
        LOGGER.fatal("  Note: The port 1883 is added internally.")
        sys.exit(2)

    broker_val_stripped = broker_val.strip()

    # Check if it contains any scheme (like mqtt://, mqtts://, http://, etc.)
    if "://" in broker_val_stripped:
        LOGGER.fatal("MQTT Broker argument validation failed:")
        LOGGER.fatal(f"  Invalid value: '{broker_val}'")
        LOGGER.fatal("  Mistake: Do not include the protocol scheme (e.g., 'mqtt://' or 'mqtts://').")
        LOGGER.fatal("  Correct command: python3 main.py -b <host/IP> -I <device-id>")
        LOGGER.fatal("  Note: The port 1883 is added internally.")
        sys.exit(2)

    # Check for URL paths or trailing slashes
    if "/" in broker_val_stripped:
        LOGGER.fatal("MQTT Broker argument validation failed:")
        LOGGER.fatal(f"  Invalid value: '{broker_val}'")
        LOGGER.fatal("  Mistake: Do not include URL paths or trailing slashes.")
        LOGGER.fatal("  Correct command: python3 main.py -b <host/IP> -I <device-id>")
        LOGGER.fatal("  Note: The port 1883 is added internally.")
        sys.exit(2)

    # Check for host:port combination (IP-v6 compliant)
    if ":" in broker_val_stripped:
        num_colons = broker_val_stripped.count(":")
        is_invalid_port = False
        
        if num_colons == 1:
            # Simple host:port or IPv4:port
            parts = broker_val_stripped.split(":")
            if parts[1].isdigit():
                is_invalid_port = True
        elif num_colons > 1 and "]" in broker_val_stripped:
            # Bracketed IPv6 with port, e.g., [::1]:1883
            parts = broker_val_stripped.rsplit(":", 1)
            if len(parts) == 2 and parts[1].isdigit():
                is_invalid_port = True

        if is_invalid_port:
            LOGGER.fatal("MQTT Broker argument validation failed:")
            LOGGER.fatal(f"  Invalid value: '{broker_val}'")
            LOGGER.fatal("  Mistake: Do not specify a port number (e.g., ':1883').")
            LOGGER.fatal("  Correct command: python3 main.py -b <host/IP> -I <device-id>")
            LOGGER.fatal("  Note: The port 1883 is added internally.")
            sys.exit(2)

def validate_arguments_and_warn(args):
    """
    Validates command line arguments and outputs helpful warnings/hints.
    """
    # Validate broker
    validate_broker(args.broker)

    # Warn if using default values that might be common mistakes
    if args.broker == "localhost":
        LOGGER.warn("[HINT] Using default broker host 'localhost'. If your device is on a different network/host, specify it via -b.")

    if args.ID == "localhost":
        LOGGER.warn("[HINT] Using default device ID 'localhost'. If your target device has a custom ID, specify it via -I.")

def handle_connection_error(broker_address, broker_port, exception):
    """
    Defensively handles connection-related errors.
    Logs clean, actionable FATAL messages and exits cleanly.
    """
    LOGGER.fatal("MQTT Connection failed:")
    LOGGER.fatal(f"  Broker address: {broker_address}:{broker_port}")
    LOGGER.fatal(f"  Error: {type(exception).__name__}: {exception}")
    LOGGER.fatal("  Please ensure that the MQTT broker is running, reachable, and the host/IP is correct.")
    sys.exit(2)
