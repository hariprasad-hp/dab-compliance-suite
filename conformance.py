import config
import dab.app_telemetry
import dab.device
import dab.health_check
import dab.input
import dab.operations
import dab.device_telemetry
import dab.voice
import dab.applications
import dab.system
import dab.output
import dab.version
from util.enforcement_manager import EnforcementManager

# Implement the test cases for conformance test.
CONFORMANCE_TEST_CASE = [
    ("operations/list",'{}', dab.operations.list, 200, "Conformance"),
    ("applications/list",'{}', dab.applications.list, 250, "Conformance"),
    ("applications/launch",f'{{"appId": "{config.apps["youtube"]}"}}', dab.applications.launch, 10000, "Conformance"),
    ("applications/launch",f'{{"appId": "{config.apps["youtube"]}", "parameters": ["v%3DSs75O8yllyc","enableEventConsole%3Dtrue","env_showConsole%3Dtrue"]}}', dab.applications.launch, 10000, "with parameters"),
    ("applications/launch-with-content",f'{{"appId": "{config.apps["youtube"]}", "contentId": "jfKfPfyJRdk"}}', dab.applications.launch_with_content, 10000, "Conformance"),
    ("applications/get-state",f'{{"appId": "{config.apps["youtube"]}"}}', dab.applications.get_state, 200, "Conformance"),
    ("applications/exit",f'{{"appId": "{config.apps["youtube"]}"}}', dab.applications.exit, 5000, "Conformance"),
    ("device/info",'{}', dab.device.info, 200, "Conformance"),
    ("system/settings/list",'{}', dab.system.list, 200, "Conformance"),
    ("system/settings/get",'{}', dab.system.get, 200, "Conformance"),
    ("system/settings/set",'{"language": "en-US"}', dab.system.set, 120000, "language"),
    ("system/settings/set",'{"outputResolution": {"width": 3840, "height": 2160, "frequency": 60} }', dab.system.set, 3000, "outputResolution"),
    ("system/settings/set",'{"memc": true}', dab.system.set, 3000, "memc"),
    ("system/settings/set",'{"cec": true}', dab.system.set, 3000, "cec"),
    ("system/settings/set",'{"lowLatencyMode": true}', dab.system.set, 3000, "lowLatencyMode"),
    ("system/settings/set",'{"matchContentFrameRate": "EnabledSeamlessOnly"}', dab.system.set, 3000, "matchContentFrameRate"),
    ("system/settings/set",'{"hdrOutputMode": "AlwaysHdr"}', dab.system.set, 3000, "hdrOutputMode"),
    ("system/settings/set",'{"pictureMode": "Standard"}', dab.system.set, 3000, "pictureMode"),
    ("system/settings/set",'{"audioOutputMode": "Auto"}', dab.system.set, 3000, "audioOutputMode"),
    ("system/settings/set",'{"audioOutputSource": "HDMI"}', dab.system.set, 3000, "audioOutputSource"),
    ("system/settings/set",'{"videoInputSource": "HDMI1"}', dab.system.set, 3000, "videoInputSource"),
    ("system/settings/set",'{"audioVolume": 20}', dab.system.set, 3000, "audioVolume"),
    ("system/settings/set",'{"mute": false}', dab.system.set, 3000, "mute"),
    ("system/settings/set",'{"textToSpeech": true}', dab.system.set, 3000, "textToSpeech"),
    ("input/key/list",'{}', dab.input.list, 200, "Conformance"),
    ("input/key-press",'{"keyCode": "KEY_HOME"}', dab.input.key_press, 1000, "KEY_HOME"),
    ("input/key-press",'{"keyCode": "KEY_VOLUME_UP"}', dab.input.key_press, 1000, "KEY_VOLUME_UP"),
    ("input/key-press",'{"keyCode": "KEY_VOLUME_DOWN"}', dab.input.key_press, 1000, "KEY_VOLUME_DOWN"),
    ("input/key-press",'{"keyCode": "KEY_MUTE"}', dab.input.key_press, 1000, "KEY_MUTE"),
    ("input/key-press",'{"keyCode": "KEY_CHANNEL_UP"}', dab.input.key_press, 1000, "KEY_CHANNEL_UP"),
    ("input/key-press",'{"keyCode": "KEY_CHANNEL_DOWN"}', dab.input.key_press, 1000, "KEY_CHANNEL_DOWN"),
    ("input/key-press",'{"keyCode": "KEY_MENU"}', dab.input.key_press, 1000, "KEY_MENU"),
    ("input/key-press",'{"keyCode": "KEY_EXIT"}', dab.input.key_press, 1000, "KEY_EXIT"),
    ("input/key-press",'{"keyCode": "KEY_INFO"}', dab.input.key_press, 1000, "KEY_INFO"),
    ("input/key-press",'{"keyCode": "KEY_GUIDE"}', dab.input.key_press, 1000, "KEY_GUIDE"),
    ("input/key-press",'{"keyCode": "KEY_CAPTIONS"}', dab.input.key_press, 1000, "KEY_CAPTIONS"),
    ("input/key-press",'{"keyCode": "KEY_UP"}', dab.input.key_press, 1000, "KEY_UP"),
    ("input/key-press",'{"keyCode": "KEY_PAGE_UP"}', dab.input.key_press, 1000, "KEY_PAGE_UP"),
    ("input/key-press",'{"keyCode": "KEY_PAGE_DOWN"}', dab.input.key_press, 1000, "KEY_PAGE_DOWN"),
    ("input/key-press",'{"keyCode": "KEY_RIGHT"}', dab.input.key_press, 1000, "KEY_RIGHT"),
    ("input/key-press",'{"keyCode": "KEY_DOWN"}', dab.input.key_press, 1000, "KEY_DOWN"),
    ("input/key-press",'{"keyCode": "KEY_LEFT"}', dab.input.key_press, 1000, "KEY_LEFT"),
    ("input/key-press",'{"keyCode": "KEY_ENTER"}', dab.input.key_press, 1000, "KEY_ENTER"),
    ("input/key-press",'{"keyCode": "KEY_BACK"}', dab.input.key_press, 1000, "KEY_BACK"),
    ("input/key-press",'{"keyCode": "KEY_PLAY"}', dab.input.key_press, 1000, "KEY_PLAY"),
    ("input/key-press",'{"keyCode": "KEY_PLAY_PAUSE"}', dab.input.key_press, 1000, "KEY_PLAY_PAUSE"),
    ("input/key-press",'{"keyCode": "KEY_PAUSE"}', dab.input.key_press, 1000, "KEY_PAUSE"),
    ("input/key-press",'{"keyCode": "KEY_STOP"}', dab.input.key_press, 1000, "KEY_STOP"),
    ("input/key-press",'{"keyCode": "KEY_REWIND"}', dab.input.key_press, 1000, "KEY_REWIND"),
    ("input/key-press",'{"keyCode": "KEY_FAST_FORWARD"}', dab.input.key_press, 1000, "KEY_FAST_FORWARD"),
    ("input/key-press",'{"keyCode": "KEY_SKIP_REWIND"}', dab.input.key_press, 1000, "KEY_SKIP_REWIND"),
    ("input/key-press",'{"keyCode": "KEY_SKIP_FAST_FORWARD"}', dab.input.key_press, 1000, "KEY_SKIP_FAST_FORWARD"),
    ("input/key-press",'{"keyCode": "KEY_0"}', dab.input.key_press, 1000, "KEY_0"),
    ("input/key-press",'{"keyCode": "KEY_1"}', dab.input.key_press, 1000, "KEY_1"),
    ("input/key-press",'{"keyCode": "KEY_2"}', dab.input.key_press, 1000, "KEY_2"),
    ("input/key-press",'{"keyCode": "KEY_3"}', dab.input.key_press, 1000, "KEY_3"),
    ("input/key-press",'{"keyCode": "KEY_4"}', dab.input.key_press, 1000, "KEY_4"),
    ("input/key-press",'{"keyCode": "KEY_5"}', dab.input.key_press, 1000, "KEY_5"),
    ("input/key-press",'{"keyCode": "KEY_6"}', dab.input.key_press, 1000, "KEY_6"),
    ("input/key-press",'{"keyCode": "KEY_7"}', dab.input.key_press, 1000, "KEY_7"),
    ("input/key-press",'{"keyCode": "KEY_8"}', dab.input.key_press, 1000, "KEY_8"),
    ("input/key-press",'{"keyCode": "KEY_9"}', dab.input.key_press, 1000, "KEY_9"),
    ("input/long-key-press",'{"keyCode": "KEY_HOME", "durationMs": 3000}', dab.input.long_key_press, 3200, "KEY_HOME"),
    ("input/long-key-press",'{"keyCode": "KEY_VOLUME_UP", "durationMs": 3000}', dab.input.long_key_press, 3200, "KEY_VOLUME_UP"),
    ("input/long-key-press",'{"keyCode": "KEY_VOLUME_DOWN", "durationMs": 3000}', dab.input.long_key_press, 3200, "KEY_VOLUME_DOWN"),
    ("input/long-key-press",'{"keyCode": "KEY_MUTE", "durationMs": 3000}', dab.input.long_key_press, 3200, "KEY_MUTE"),
    ("input/long-key-press",'{"keyCode": "KEY_CHANNEL_UP", "durationMs": 3000}', dab.input.long_key_press, 3200, "KEY_CHANNEL_UP"),
    ("input/long-key-press",'{"keyCode": "KEY_CHANNEL_DOWN", "durationMs": 3000}', dab.input.long_key_press, 3200, "KEY_CHANNEL_DOWN"),
    ("input/long-key-press",'{"keyCode": "KEY_MENU", "durationMs": 3000}', dab.input.long_key_press, 3200, "KEY_MENU"),
    ("input/long-key-press",'{"keyCode": "KEY_EXIT", "durationMs": 3000}', dab.input.long_key_press, 3200, "KEY_EXIT"),
    ("input/long-key-press",'{"keyCode": "KEY_INFO", "durationMs": 3000}', dab.input.long_key_press, 3200, "KEY_INFO"),
    ("input/long-key-press",'{"keyCode": "KEY_GUIDE", "durationMs": 3000}', dab.input.long_key_press, 3200, "KEY_GUIDE"),
    ("input/long-key-press",'{"keyCode": "KEY_CAPTIONS", "durationMs": 3000}', dab.input.long_key_press, 3200, "KEY_CAPTIONS"),
    ("input/long-key-press",'{"keyCode": "KEY_UP", "durationMs": 3000}', dab.input.long_key_press, 3200, "KEY_UP"),
    ("input/long-key-press",'{"keyCode": "KEY_PAGE_UP", "durationMs": 3000}', dab.input.long_key_press, 3200, "KEY_PAGE_UP"),
    ("input/long-key-press",'{"keyCode": "KEY_PAGE_DOWN", "durationMs": 3000}', dab.input.long_key_press, 3200, "KEY_PAGE_DOWN"),
    ("input/long-key-press",'{"keyCode": "KEY_RIGHT", "durationMs": 3000}', dab.input.long_key_press, 3200, "KEY_RIGHT"),
    ("input/long-key-press",'{"keyCode": "KEY_DOWN", "durationMs": 3000}', dab.input.long_key_press, 3200, "KEY_DOWN"),
    ("input/long-key-press",'{"keyCode": "KEY_LEFT", "durationMs": 3000}', dab.input.long_key_press, 3200, "KEY_LEFT"),
    ("input/long-key-press",'{"keyCode": "KEY_ENTER", "durationMs": 3000}', dab.input.long_key_press, 3200, "KEY_ENTER"),
    ("input/long-key-press",'{"keyCode": "KEY_BACK", "durationMs": 3000}', dab.input.long_key_press, 3200, "KEY_BACK"),
    ("input/long-key-press",'{"keyCode": "KEY_PLAY", "durationMs": 3000}', dab.input.long_key_press, 3200, "KEY_PLAY"),
    ("input/long-key-press",'{"keyCode": "KEY_PLAY_PAUSE", "durationMs": 3000}', dab.input.long_key_press, 3200, "KEY_PLAY_PAUSE"),
    ("input/long-key-press",'{"keyCode": "KEY_PAUSE", "durationMs": 3000}', dab.input.long_key_press, 3200, "KEY_PAUSE"),
    ("input/long-key-press",'{"keyCode": "KEY_STOP", "durationMs": 3000}', dab.input.long_key_press, 3200, "KEY_STOP"),
    ("input/long-key-press",'{"keyCode": "KEY_REWIND", "durationMs": 3000}', dab.input.long_key_press, 3200, "KEY_REWIND"),
    ("input/long-key-press",'{"keyCode": "KEY_FAST_FORWARD", "durationMs": 3000}', dab.input.long_key_press, 3200, "KEY_FAST_FORWARD"),
    ("input/long-key-press",'{"keyCode": "KEY_SKIP_REWIND", "durationMs": 3000}', dab.input.long_key_press, 3200, "KEY_SKIP_REWIND"),
    ("input/long-key-press",'{"keyCode": "KEY_SKIP_FAST_FORWARD", "durationMs": 3000}', dab.input.long_key_press, 3200, "KEY_SKIP_FAST_FORWARD"),
    ("input/long-key-press",'{"keyCode": "KEY_0", "durationMs": 3000}', dab.input.long_key_press, 3200, "KEY_0"),
    ("input/long-key-press",'{"keyCode": "KEY_1", "durationMs": 3000}', dab.input.long_key_press, 3200, "KEY_1"),
    ("input/long-key-press",'{"keyCode": "KEY_2", "durationMs": 3000}', dab.input.long_key_press, 3200, "KEY_2"),
    ("input/long-key-press",'{"keyCode": "KEY_3", "durationMs": 3000}', dab.input.long_key_press, 3200, "KEY_3"),
    ("input/long-key-press",'{"keyCode": "KEY_4", "durationMs": 3000}', dab.input.long_key_press, 3200, "KEY_4"),
    ("input/long-key-press",'{"keyCode": "KEY_5", "durationMs": 3000}', dab.input.long_key_press, 3200, "KEY_5"),
    ("input/long-key-press",'{"keyCode": "KEY_6", "durationMs": 3000}', dab.input.long_key_press, 3200, "KEY_6"),
    ("input/long-key-press",'{"keyCode": "KEY_7", "durationMs": 3000}', dab.input.long_key_press, 3200, "KEY_7"),
    ("input/long-key-press",'{"keyCode": "KEY_8", "durationMs": 3000}', dab.input.long_key_press, 3200, "KEY_8"),
    ("input/long-key-press",'{"keyCode": "KEY_9", "durationMs": 3000}', dab.input.long_key_press, 3200, "KEY_9"),
    ("output/image",'{}', dab.output.image, 2000, "Conformance"),
    ("device-telemetry/start",'{"duration": 1000}', dab.device_telemetry.start, 200, "Conformance"),
    ("device-telemetry/stop",'{}', dab.device_telemetry.stop, 200, "Conformance"),
    ("app-telemetry/start",f'{{"appId": "{config.apps["youtube"]}", "duration": 1000}}', dab.app_telemetry.start, 700, "Conformance"),
    ("app-telemetry/stop",f'{{"appId": "{config.apps["youtube"]}"}}', dab.app_telemetry.stop, 200, "Conformance"),
    ("health-check/get",'{}', dab.health_check.get, 2000, "Conformance"),
    ("voice/list",'{}', dab.voice.list, 200, "Conformance"),
    ("voice/set",f'{{"voiceSystem":{{"name":"{config.va}","enabled":true}}}}', dab.voice.set, 5000, "Conformance"),
    ("voice/send-audio",f'{{"fileLocation": "https://storage.googleapis.com/ytlr-cert.appspot.com/voice/ladygaga.wav", "voiceSystem": "{config.va}"}}',dab.voice.send_audio, 10000, "Conformance"),
    ("voice/send-text",f'{{"requestText" : "Play lady Gaga music on YouTube", "voiceSystem": "{config.va}"}}', dab.voice.send_text, 10000, "Conformance With VA"),
    ("version",' {}', dab.version.default, 200, "Conformance"),
    ("system/restart",' {}', dab.system.restart, 30000, "Conformance"),
]
