from jsonschema import validate
import jsons
import re

# Non-empty identifier/parameter token with zero whitespace characters allowed.
NO_SPACE_STR = {"type": "string", "minLength": 1, "pattern": r"^\S+$"}
NO_SPACE_OPT_EMPTY_STR = {"type": "string", "pattern": r"^\S*$"}

# Fields allowed to contain human-readable display prose (spaces permitted).
HUMAN_PROSE_FIELDS = frozenset({
    "error",
    "message",
    "statusText",
    "friendlyName",
    "version",
    "manufacturer",
    "model",
    "chipset",
    "firmwareVersion",
    "firmwareBuild",
    "uptimeSince",
    "title",
    "requestText",
    "searchText",
})


def find_whitespace_violations(payload, path: str = "") -> list:
    """
    Recursively check a DAB JSON object/array so no parameter name or non-prose
    identifier/enum/code value (including 3P custom fields) contains whitespace.
    """
    issues = []
    if isinstance(payload, dict):
        for k, v in payload.items():
            key_str = str(k)
            cur_path = f"{path}.{key_str}" if path else key_str
            if any(ch.isspace() for ch in key_str):
                issues.append(f"parameter name {cur_path!r} contains whitespace")
            if key_str in HUMAN_PROSE_FIELDS or key_str == "details":
                continue
            issues.extend(find_whitespace_violations(v, cur_path))
    elif isinstance(payload, list):
        for idx, item in enumerate(payload):
            issues.extend(find_whitespace_violations(item, f"{path}[{idx}]"))
    elif isinstance(payload, str):
        # Empty string is only valid for cleared identifierForAdvertising; whitespace is never valid.
        if any(ch.isspace() for ch in payload):
            issues.append(f"parameter '{path}' contains whitespace: {payload!r}")
    return issues


# DabRequest
dab_request_schema = {
    "type": "object",
    "properties": {},
    "required": []
}

# DabResponse
dab_response_schema = {
    "type": "object",
    "properties": {
        "status": {"type": "integer"},
        "error": {"type": "string"}
    },
    "required": ["status"]
}

# Operation: operations/list
# OperationsListRequest
operations_list_request_schema = dab_request_schema

# ListSupportedOperationResponse
list_supported_operation_response_schema = {
    "type": "object",
    "properties": {
        "status": {"type": "integer"},
        "error": {"type": "string"},
        "operations": {
            "type": "array",
            "items": NO_SPACE_STR
        }
    },
    "required": ["status", "operations"]
}

# Operation: applications/list
# ApplicationListRequest
application_list_request_schema = dab_request_schema

# Application
application_schema = {
    "type": "object",
    "properties": {
        "appId": NO_SPACE_STR,
        "friendlyName": {"type": "string"},
        "version": {"type": "string"}
    },
    "required": ["appId"]
}

# ListApplicationsResponse
list_applications_response_schema = {
    "type": "object",
    "properties": {
        "status": {"type": "integer"},
        "error": {"type": "string"},
        "applications": {
            "type": "array",
            "items": application_schema
        }
    },
    "required": ["status", "applications"]
}

# Operation: applications/launch
# LaunchApplicationRequest
launch_application_request_schema = {
    "type": "object",
    "properties": {
        "appId": NO_SPACE_STR,
        "parameters": {
            "type": "array",
            "items": NO_SPACE_STR
        }
    },
    "required": ["appId"]
}

# LaunchApplicationResponse
launch_application_response_schema = dab_response_schema

# Operation: applications/launch_with_content
# LaunchApplicationWithContentRequest
launch_application_with_content_request_schema = {
    "type": "object",
    "properties": {
        "appId": NO_SPACE_STR,
        "contentId": NO_SPACE_STR,
        "parameters": {
            "type": "array",
            "items": NO_SPACE_STR
        }
    },
    "required": ["appId", "contentId"]
}

# LaunchApplicationWithContentResponse
launch_application_with_content_response_schema = dab_response_schema

# Operation: applications/get_state
# GetApplicationStateRequest
get_application_state_request_schema = {
    "type": "object",
    "properties": {
        "appId": NO_SPACE_STR
    },
    "required": ["appId"]
}

# GetApplicationStateResponse
get_application_state_response_schema = {
    "type": "object",
    "properties": {
        "status": {"type": "integer"},
        "error": {"type": "string"},
        "state": {"type": "string", "enum": ["STOPPED", "BACKGROUND", "FOREGROUND"]}
    },
    "required": ["status", "state"]
}

# Operation: applications/exit
# ExitApplicationRequest
exit_application_request_schema = {
    "type": "object",
    "properties": {
        "appId": NO_SPACE_STR,
        "background": {"type": "boolean"}
    },
    "required": ["appId"]
}

# ExitApplicationResponse
exit_application_response_schema = {
    "type": "object",
    "properties": {
        "status": {"type": "integer"},
        "error": {"type": "string"},
        "state": {"type": "string", "enum": ["STOPPED", "BACKGROUND", "FOREGROUND"]}
    },
    "required": ["status", "state"]
}
# InstallApplicationRequest
install_application_request_schema = {
    "type": "object",
    "properties": {
        "appId": NO_SPACE_STR,
        "force": {"type": "boolean"}
    },
    "required": ["appId"]
}
# InstallApplicationResponse
install_application_response_schema = {
    "type": "object",
    "properties": {
        "status": {"type": "integer"},
        "error": {"type": "string"},
        "message": {"type": "string"},
        "details": {"type": "object"},
    },
    "required": ["status"],
}

# UninstallApplicationRequest
uninstall_application_request_schema = {
    "type": "object",
    "properties": {
        "appId": NO_SPACE_STR,
        "force": {"type": "boolean"}
    },
    "required": ["appId"]
}
# UnnstallApplicationResponse
uninstall_application_response_schema = {
    "type": "object",
    "properties": {
        "status": {"type": "integer"},
        "error": {"type": "string"},
        "message": {"type": "string"},
        "details": {"type": "object"},
    },
    "required": ["status"],
}
# Clear_dataApplicationRequest
clear_data_application_request_schema = {
    "type": "object",
    "properties": {
        "appId": NO_SPACE_STR,
        "force": {"type": "boolean"}
    },
    "required": ["appId"]
}
# clear_dataApplicationResponse
clear_data_application_response_schema = {
    "type": "object",
    "properties": {
        "status": {"type": "integer"},
        "error": {"type": "string"},
        "message": {"type": "string"},
        "details": {"type": "object"},
    },
    "required": ["status"],
}
# InstallFromAppstoreApplicationRequest
install_from_appstore_application_request_schema = {
    "type": "object",
    "properties": {
        "appId": NO_SPACE_STR,
        "force": {"type": "boolean"}
    },
    "required": ["appId"]
}
# InstallFromAppstoreApplicationResponse
install_from_appstore_application_response_schema = {
    "type": "object",
    "properties": {
        "status": {"type": "integer"},
        "error": {"type": "string"},
        "message": {"type": "string"},
        "details": {"type": "object"},
    },
    "required": ["status"],
}

# Operation: device/info
# DeviceInfoRequest
device_info_request_schema = dab_request_schema

# NetworkInterfaceType and DisplayType
# These are enums and can be represented as strings in a JSON schema.

# NetworkInterface
network_interface_schema = {
    "type": "object",
    "properties": {
        "connected": {"type": "boolean"},
        "macAddress": NO_SPACE_STR,
        "ipAddress": {"type": ["string", "null"], "pattern": r"^\S+$"},
        "dns": {
            "type": ["array", "null"],
            "items": NO_SPACE_STR
        },
        "type": {"type": "string", "enum": ["Ethernet", "Wifi", "Bluetooth", "Coax", "Other"]}
    },
    "required": ["connected", "macAddress", "type"]
}

# DeviceInformation
device_information_schema = {
    "type": "object",
    "properties": {
        "status": {"type": "integer"},
        "error": {"type": ["string", "null"]},
        "manufacturer": {"type": "string"},
        "model": {"type": "string"},
        "serialNumber": NO_SPACE_STR,
        "chipset": {"type": "string"},
        "firmwareVersion": {"type": "string"},
        "firmwareBuild": {"type": "string"},
        "networkInterfaces": {
            "type": "array",
            "items": network_interface_schema
        },
        "displayType": {"type": "string", "enum": ["Native", "External"]},
        "screenWidthPixels": {"type": "integer"},
        "screenHeightPixels": {"type": "integer"},
        "uptimeSince": {"type": ["string", "integer"]},
        "deviceId": NO_SPACE_STR
    },
    "required": ["status", "manufacturer", "model", "serialNumber", "chipset", 
                 "firmwareVersion", "firmwareBuild", "networkInterfaces", "displayType", 
                 "uptimeSince", "deviceId"]
}

# Operation: system/restart
# RestartRequest and RestartResponse
restart_request_schema = dab_request_schema
restart_response_schema = dab_response_schema

# Operation: system/settings/list
# SettingsListRequest
settings_list_request_schema = dab_request_schema

# OutputResolution
output_resolution_schema = {
    "type": "object",
    "properties": {
        "width": {"type": "integer", "minimum": 1},
        "height": {"type": "integer", "minimum": 1},
        "frequency": {"type": "number", "exclusiveMinimum": 0}
    },
    "required": ["width", "height", "frequency"],
    "additionalProperties": False
}

MATCH_CONTENT_FRAME_RATE_ENUM = ["EnabledAlways", "EnabledSeamlessOnly", "Disabled"]
HDR_OUTPUT_MODE_ENUM = ["AlwaysHdr", "HdrOnPlayback", "DisableHdr"]
PICTURE_MODE_ENUM = ["Standard", "Dynamic", "Movie", "Sports", "FilmMaker", "Game", "Auto"]
AUDIO_OUTPUT_MODE_ENUM = ["Stereo", "MultichannelPcm", "PassThrough", "Auto"]
AUDIO_OUTPUT_SOURCE_ENUM_20 = ["NativeSpeaker", "Arc", "EArc", "Optical", "Aux", "Bluetooth", "Auto", "HDMI"]
AUDIO_OUTPUT_SOURCE_ENUM_21 = ["NativeSpeaker", "Arc", "EArc", "Optical", "Aux", "WirelessSpeakers", "Auto", "HDMI"]
VIDEO_INPUT_SOURCE_ENUM_20 = ["Tuner", "HDMI1", "HDMI2", "HDMI3", "HDMI4", "Composite", "Component", "Home", "Cast"]
VIDEO_INPUT_SOURCE_ENUM_21 = ["Tuner", "HDMI1", "HDMI2", "HDMI3", "HDMI4", "Composite", "Component", "USB", "Home", "Cast"]

numeric_range_schema = {
    "type": "object",
    "properties": {
        "min": {"type": "integer"},
        "max": {"type": "integer"}
    },
    "required": ["min", "max"],
    "additionalProperties": False
}

# ListSystemSettings (structural/type validation; partner enum names and extra keys allowed)
_non_empty_str_array = {"type": "array", "items": NO_SPACE_STR}

list_system_settings_schema = {
    "type": "object",
    "properties": {
        "status": {"type": "integer"},
        "error": {"type": ["string", "null"]},
        "language": {"type": "array", "items": {"type": "string", "minLength": 2, "pattern": r"^\S+$"}},
        "outputResolution": {"type": "array", "items": output_resolution_schema},
        "memc": {"type": "boolean"},
        "cec": {"type": "boolean"},
        "lowLatencyMode": {"type": "boolean"},
        "matchContentFrameRate": _non_empty_str_array,
        "hdrOutputMode": _non_empty_str_array,
        "pictureMode": _non_empty_str_array,
        "audioOutputMode": _non_empty_str_array,
        "audioOutputSource": _non_empty_str_array,
        "videoInputSource": _non_empty_str_array,
        "audioVolume": numeric_range_schema,
        "mute": {"type": "boolean"},
        "textToSpeech": {"type": "boolean"},
    },
}

list_system_settings_schema_20 = {
    "type": "object",
    "properties": list_system_settings_schema["properties"],
    "required": ["status"],
}

list_system_settings_schema_21 = {
    "type": "object",
    "properties": {
        **list_system_settings_schema["properties"],
        "brightness": numeric_range_schema,
        "contrast": numeric_range_schema,
        "timeZone": _non_empty_str_array,
        "screenSaver": {"type": "boolean"},
        "screenSaverMinTimeout": {"type": "integer", "minimum": 0, "maximum": 60},
        "personalizedAds": {"type": "boolean"},
        "highContrastText": {"type": "boolean"},
        "identifierForAdvertising": {"type": "boolean"},
    },
    "required": ["status"],
}

system_settings_schema = {
    "status": {"type": "integer"},
    "language": {"type": "string", "minLength": 2, "pattern": r"^\S+$"},
    "outputResolution": output_resolution_schema,
    "memc": {"type": "boolean"},
    "cec": {"type": "boolean"},
    "lowLatencyMode": {"type": "boolean"},
    "matchContentFrameRate": NO_SPACE_STR,
    "hdrOutputMode": NO_SPACE_STR,
    "pictureMode": NO_SPACE_STR,
    "audioOutputMode": NO_SPACE_STR,
    "audioOutputSource": NO_SPACE_STR,
    "videoInputSource": NO_SPACE_STR,
    "audioVolume": {"type": "integer"},
    "mute": {"type": "boolean"},
    "textToSpeech": {"type": "boolean"},
}

# Operation: system/settings/get
# GetSystemSettingsResponse
get_system_settings_response_schema = {
    "type": "object",
    "properties": {
        "status": {"type": "integer"}
    },
    "required": ["status"],

    "if": {
        "properties": {
            "status": { "const": 200 }
        }
    },
    "then": {
        "properties": system_settings_schema,
    },
    "else": {
        "properties": {
            "error": {"type": ["string", "null"]}
        },
        "required": ["error"]
    },
}

# SetSystemSettingsResponse
set_system_settings_response_schema = {
    "type": "object",
    "properties": {
        "status": {"type": "integer"}
    },
    "required": ["status"],

    "if": {
        "properties": {
            "status": { "const": 200 }
        }
    },
    "then": {
        "properties": system_settings_schema,
    },
    "else": {
        "properties": {
            "error": {"type": ["string", "null"]}
        },
        "required": ["error"]
    },
}

system_settings_schema_21 = {
    **system_settings_schema,
    "brightness": {"type": "integer"},
    "contrast": {"type": "integer"},
    "timeZone": NO_SPACE_STR,
    "screenSaver": {"type": "boolean"},
    "screenSaverTimeout": {"type": "integer", "minimum": 1},
    "personalizedAds": {"type": "boolean"},
    "highContrastText": {"type": "boolean"},
    "identifierForAdvertising": NO_SPACE_OPT_EMPTY_STR,
}

get_system_settings_response_schema_21 = {
    **get_system_settings_response_schema,
    "then": {
        "properties": system_settings_schema_21,
    },
}

set_system_settings_response_schema_21 = {
    **set_system_settings_response_schema,
    "then": {
        "properties": system_settings_schema_21,
    },
}

# Operation: input/key/list
# KeyList
key_list_schema = {
    "type": "object",
    "properties": {
        "status": {"type": "integer"},
        "error": {"type": ["string", "null"]},
        "keyCodes": {
            "type": "array",
            "items": NO_SPACE_STR
        },
    },
    "required": ["status", "keyCodes"]
}

# Operation: input/key_press
# KeyPressRequest and LongKeyPressRequest
key_press_request_schema = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "keyCode": NO_SPACE_STR,
    },
    "required": ["id", "keyCode"]
}

# Operation: input/long_key_press
# LongKeyPressRequest
long_key_press_request_schema = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "keyCode": NO_SPACE_STR,
        "durationMs": {"type": "integer"},
    },
    "required": ["id", "keyCode", "durationMs"]
}

# KeyPressResponse
key_press_response_schema = {
    "type": "object",
    "properties": {
        "status": {"type": "integer"},
        "error": {"type": ["string", "null"]},
    },
    "required": ["status"]
}

# Operation: output/image
# OutputImageRequest and OutputImageResponse
output_image_request_schema = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "outputLocation": NO_SPACE_STR,
    },
    "required": ["id", "outputLocation"]
}

output_image_response_schema = {
    "type": "object",
    "properties": {
        "status": {"type": "integer"},
        "error": {"type": ["string", "null"]},
        "outputImage": {"type": "string", "pattern": r"^data:image/png;base64,\S+$"},
    },
    "required": ["status", "outputImage"]
}

# Operation: device_telemetry/start
# StartDeviceTelemetryRequest and StartDeviceTelemetryResponse
start_device_telemetry_request_schema = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "duration": {"type": "number"},
    },
    "required": ["id", "duration"]
}

start_device_telemetry_response_schema = {
    "type": "object",
    "properties": {
        "status": {"type": "integer"},
        "error": {"type": ["string", "null"]},
        "duration": {"type": "number"},
    },
    "required": ["status", "duration"]
}

# Operation: device_telemetry/stop
# StopDeviceTelemetryRequest and StopDeviceTelemetryResponse
stop_device_telemetry_request_schema = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
    },
    "required": ["id"]
}

stop_device_telemetry_response_schema = {
    "type": "object",
    "properties": {
        "status": {"type": "integer"},
        "error": {"type": ["string", "null"]},
    },
    "required": ["status"]
}

# Operation: app_telemetry/start
# StartApplicationTelemetryRequest and StartApplicationTelemetryResponse
start_app_telemetry_request_schema = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "appId": NO_SPACE_STR,
        "duration": {"type": "number"},
    },
    "required": ["id", "appId", "duration"]
}

start_app_telemetry_response_schema = {
    "type": "object",
    "properties": {
        "status": {"type": "integer"},
        "error": {"type": ["string", "null"]},
        "duration": {"type": "number"},
    },
    "required": ["status", "duration"]
}

# Operation: app_telemetry/stop
# StopApplicationTelemetryRequest and StopApplicationTelemetryResponse
stop_app_telemetry_request_schema = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "appId": NO_SPACE_STR,
    },
    "required": ["id", "appId"]
}

stop_app_telemetry_response_schema = {
    "type": "object",
    "properties": {
        "status": {"type": "integer"},
        "error": {"type": ["string", "null"]},
    },
    "required": ["status"]
}

# Operation: health_check/get
# HealthCheckRequest and HealthCheckResponse
health_check_request_schema = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
    },
    "required": ["id"]
}

health_check_response_schema = {
    "type": "object",
    "properties": {
        "status": {"type": "integer"},
        "error": {"type": ["string", "null"]},
        "healthy": {"type": "boolean"},
        "message": {"type": ["string", "null"]},
    },
    "required": ["status", "healthy"]
}

# Operation: voice/list
# VoiceListRequest and ListVoiceResponse
voice_list_request_schema = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
    },
    "required": ["id"]
}

list_voice_response_schema = {
    "type": "object",
    "properties": {
        "status": {"type": "integer"},
        "error": {"type": ["string", "null"]},
        "voiceSystems": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": NO_SPACE_STR,
                    "enabled": {"type": "boolean"},
                },
                "required": ["name", "enabled"]
            }
        },
    },
    "required": ["status", "voiceSystems"]
}

# Operation: voice/set
# SetVoiceSystemRequest and SetVoiceSystemResponse
set_voice_system_request_schema = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "voiceSystem": {
            "type": "object",
            "properties": {
                "name": NO_SPACE_STR,
                "enabled": {"type": "boolean"},
            },
            "required": ["name", "enabled"]
        },
    },
    "required": ["id", "voiceSystem"]
}

set_voice_system_response_schema = {
    "type": "object",
    "properties": {
        "status": {"type": "integer"},
        "error": {"type": ["string", "null"]},
        "voiceSystem": {
            "type": "object",
            "properties": {
                "name": NO_SPACE_STR,
                "enabled": {"type": "boolean"},
            },
            "required": ["name", "enabled"]
        },
    },
    "required": ["status", "voiceSystem"]
}

# Operation: voice/send_audio
# SendAudioRequest and VoiceRequestResponse
send_audio_request_schema = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "fileLocation": NO_SPACE_STR,
        "voiceSystem": {"type": ["string", "null"], "pattern": r"^\S+$"},
    },
    "required": ["id", "fileLocation"]
}

voice_request_response_schema = {
    "type": "object",
    "properties": {
        "status": {"type": "integer"},
        "error": {"type": ["string", "null"]},
    },
    "required": ["status"]
}

# Operation: voice/send_text
# SendTextRequest and VoiceTextRequestResponse
send_text_request_schema = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "requestText": {"type": "string"},
        "voiceSystem": NO_SPACE_STR,
    },
    "required": ["id", "requestText", "voiceSystem"]
}

voice_text_request_response_schema = {
    "type": "object",
    "properties": {
        "status": {"type": "integer"},
        "error": {"type": ["string", "null"]},
    },
    "required": ["status"]
}

# Operation: discovery
# DiscoveryRequest and DiscoveryResponse
discovery_request_schema = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
    },
    "required": ["id"]
}

discovery_response_schema = {
    "type": "object",
    "properties": {
        "status": {"type": "integer"},
        "error": {"type": ["string", "null"]},
        "ip": NO_SPACE_STR,
        "deviceId": NO_SPACE_STR,
    },
    "required": ["status", "ip", "deviceId"]
}

# Operation: version
# VersionRequest and VersionResponse
version_request_schema = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
    },
    "required": ["id"]
}

version_response_schema = {
    "type": "object",
    "properties": {
        "status": {"type": "integer"},
        "error": {"type": ["string", "null"]},
        "versions": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "string",
                "pattern": "^[0-9]+\\.[0-9]+$"
            }
        },
    },
    "required": ["status", "versions"]
}

#StartLogCollectionRequest
start_log_collection_request_schema = dab_request_schema

#StartLogCollectionResponce
start_log_collection_response_schema = {
    "type": "object",
    "properties": {
        "status": {"type": "integer"},
        "error": {"type": "string"}
    },
    "required": ["status"]
}

#StopLogCollectionRequest
stop_log_collection_request_schema = dab_request_schema

#StopLogCollectionResponse
stop_log_collection_response_schema = {
    "type": "object",
    "properties": {
        "status": {"type": "integer"},
        "error": {"type": "string"},
        "logArchive": NO_SPACE_STR,
        "remainingChunks": {"type": "integer"}
    },
    "required": ["status", "logArchive", "remainingChunks"]
}

# Operation: system/power-mode/get
# GetPowerModeRequest
power_mode_get_request_schema = dab_request_schema

# GetPowerModeResponse
power_mode_get_response_schema = {
    "type": "object",
    "properties": {
        "status": {"type": "integer"},
        "error": {"type": "string"},
        "powerMode": {"type": "string", "enum": ["Active", "Standby", "DeepSleep"]}
    },
    "required": ["status", "powerMode"]
}

# Operation: system/power-mode/set
# SetPowerModeRequest
power_mode_set_request_schema = {
    "type": "object",
    "properties": {
        "powerMode": {"type": "string", "enum": ["Active", "Standby", "DeepSleep"]}
    },
    "required": ["powerMode"]
}

# SetPowerModeResponse
power_mode_set_response_schema = {
    "type": "object",
    "properties": {
        "status": {"type": "integer"},
        "error": {"type": "string"},
        "powerMode": {"type": "string", "enum": ["Active", "Standby", "DeepSleep"]}
    },
    "required": ["status", "powerMode"]
}

# Operation: content/open
# ContentOpenRequest
content_open_request_schema = {
    "type": "object",
    "properties": {
        "entryId": NO_SPACE_STR
    },
    "required": ["entryId"]
}

# ContentOpenResponse
content_open_response_schema = dab_response_schema

content_entries_schema = {
    "type": "object",
    "properties": {
        "status": {"type": "integer"},
        "error": {"type": ["string", "null"]},
        "entries": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "entryId": NO_SPACE_STR,
                    "title": {"type": "string"},
                    "appId": NO_SPACE_STR,
                    "poster": NO_SPACE_STR,
                    "categories": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["ContinueWatching", "Movies", "TvShows", "LiveEvents", "LinearTv", "Video", "Trending", "Others"]
                        }
                    }
                },
                "required": ["entryId", "title", "appId", "poster", "categories"]
            }
        },
    },
    "required": ["status", "entries"]
}

# Operation: content/recommendations
# ContentRecommendationsRequest
content_recommendations_request_schema = dab_request_schema
# ContentRecommendationsResponse
content_recommendations_response_schema = content_entries_schema

# Operation: content/search
# ContentSearchRequest
content_search_request_schema = {
    "type": "object",
    "properties": {
        "searchText": {"type": "string"}
    },
    "required": ["searchText"]
}
# ContentSearchResponse
content_search_response_schema = content_entries_schema

class dab_response_validator(object):
    def __init__(self):
        pass

    @staticmethod
    def validate_dab_response_schema(response):
        validate(instance=jsons.loads(response), schema=dab_response_schema)

    @staticmethod
    def validate_list_supported_operation_response_schema(response):
        validate(instance=jsons.loads(response), schema=list_supported_operation_response_schema)

    @staticmethod
    def validate_list_applications_response_schema(response):
        validate(instance=jsons.loads(response), schema=list_applications_response_schema)

    @staticmethod
    def validate_launch_application_response_schema(response):
        validate(instance=jsons.loads(response), schema=launch_application_response_schema)

    @staticmethod
    def validate_launch_application_with_content_response_schema(response):
        validate(instance=jsons.loads(response), schema=launch_application_with_content_response_schema)

    @staticmethod
    def validate_get_application_state_response_schema(response):
        validate(instance=jsons.loads(response), schema=get_application_state_response_schema)

    @staticmethod
    def validate_exit_application_response_schema(response):
        validate(instance=jsons.loads(response), schema=exit_application_response_schema)

    @staticmethod
    def validate_install_application_response_schema(response):
        validate(instance=jsons.loads(response), schema=install_application_response_schema)

    @staticmethod
    def validate_uninstall_application_response_schema(response):
        validate(instance=jsons.loads(response), schema=uninstall_application_response_schema)

    @staticmethod
    def validate_clear_data_application_response_schema(response):
        validate(instance=jsons.loads(response), schema=clear_data_application_response_schema)
    
    @staticmethod
    def validate_install_from_appstore_application_response_schema(response):
        validate(instance=jsons.loads(response), schema=install_from_appstore_application_response_schema)

    @staticmethod
    def validate_device_information_schema(response):
        validate(instance=jsons.loads(response), schema=device_information_schema)

    @staticmethod
    def validate_restart_response_schema(response):
        validate(instance=jsons.loads(response), schema=restart_response_schema)

    @staticmethod
    def validate_list_system_settings_schema(response):
        """Validate system/settings/list against DAB 2.0 (all 14 required) or 2.1 (optional omitted) schema."""
        import dab_tester
        dab_version = dab_tester.DAB_VERSION or "2.0"
        if dab_version == "2.0":
            validate(instance=jsons.loads(response), schema=list_system_settings_schema_20)
        else:
            validate(instance=jsons.loads(response), schema=list_system_settings_schema_21)

    @staticmethod
    def validate_get_system_settings_response_schema(response):
        """Validate system/settings/get against version-specific SystemSettings schema (excluding read-only keys)."""
        import dab_tester
        schema = get_system_settings_response_schema_21 if (dab_tester.DAB_VERSION or "2.0") >= "2.1" else get_system_settings_response_schema
        validate(instance=jsons.loads(response), schema=schema)

    @staticmethod
    def validate_set_system_settings_response_schema(response):
        """Validate system/settings/set response against version-specific SystemSettings schema."""
        import dab_tester
        schema = set_system_settings_response_schema_21 if (dab_tester.DAB_VERSION or "2.0") >= "2.1" else set_system_settings_response_schema
        validate(instance=jsons.loads(response), schema=schema)

    @staticmethod
    def validate_key_list_schema(response):
        validate(instance=jsons.loads(response), schema=key_list_schema)

    @staticmethod
    def validate_output_image_response_schema(response):
        validate(instance=jsons.loads(response), schema=output_image_response_schema)

    @staticmethod
    def validate_start_device_telemetry_response_schema(response):
        validate(instance=jsons.loads(response), schema=start_device_telemetry_response_schema)

    @staticmethod
    def validate_stop_device_telemetry_response_schema(response):
        validate(instance=jsons.loads(response), schema=stop_device_telemetry_response_schema)

    @staticmethod
    def validate_start_app_telemetry_response_schema(response):
        validate(instance=jsons.loads(response), schema=start_app_telemetry_response_schema)

    @staticmethod
    def validate_stop_app_telemetry_response_schema(response):
        validate(instance=jsons.loads(response), schema=stop_app_telemetry_response_schema)

    @staticmethod
    def validate_health_check_response_schema(response):
        validate(instance=jsons.loads(response), schema=health_check_response_schema)

    @staticmethod
    def validate_list_voice_response_schema(response):
        validate(instance=jsons.loads(response), schema=list_voice_response_schema)

    @staticmethod
    def validate_set_voice_system_response_schema(response):
        validate(instance=jsons.loads(response), schema=set_voice_system_response_schema)

    @staticmethod
    def validate_discovery_response_schema(response):
        validate(instance=jsons.loads(response), schema=discovery_response_schema)

    @staticmethod
    def validate_version_response_schema(response):
        validate(instance=jsons.loads(response), schema=version_response_schema)

    @staticmethod
    def validate_stop_log_collection_response_schema(response):
        validate(instance=jsons.loads(response), schema=stop_log_collection_response_schema)

    @staticmethod
    def validate_start_log_collection_response_schema(response):
        validate(instance=jsons.loads(response), schema=start_log_collection_response_schema)

    @staticmethod
    def validate_power_mode_set_response_schema(response):
        validate(instance=jsons.loads(response), schema=power_mode_set_response_schema)

    @staticmethod
    def validate_power_mode_get_response_schema(response):
        validate(instance=jsons.loads(response), schema=power_mode_get_response_schema)

    @staticmethod
    def validate_content_recommendations_response_schema(response):
        validate(instance=jsons.loads(response), schema=content_recommendations_response_schema)

    @staticmethod
    def validate_content_search_response_schema(response):
        validate(instance=jsons.loads(response), schema=content_search_response_schema)

    @staticmethod
    def validate_content_open_response_schema(response):
        validate(instance=jsons.loads(response), schema=content_open_response_schema)
